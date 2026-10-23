"""Shared UMG theme for BoatlRacing menus: dark glass panels, gold accents (matches Content/Boats/UI_REF.png).

Theme textures come from SourceAssets/UI/Theme/make_theme.ps1. Scripts import this module with
    sys.path.insert(0, str(Path(unreal.Paths.project_dir()) / "Tools")); import ui_theme
because Tools/run_editor_script.py sends script text, not a file path.
"""
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

ROOT = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()))
LOG = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())) / "BoatlRacing.log"
THEME_SOURCE = ROOT / "SourceAssets/UI/Theme/Textures"
THEME_PATH = "/Game/UI/Theme"
THAI_FONT = "/Game/UI/Prototype/Fonts/NotoSansThai_Font"

GOLD = unreal.LinearColor(1, 0.62, 0.08, 1)
WHITE = unreal.LinearColor(1, 1, 1, 1)
MUTED = unreal.LinearColor(0.68, 0.72, 0.78, 1)
DIM = unreal.LinearColor(0, 0, 0, 0.62)


def import_textures(files, destination):
    """Import PNGs as UI textures (no mips, UI group, never streamed). Returns {stem: texture}."""
    tasks = []
    for file in files:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(file))
        task.set_editor_property("destination_path", destination)
        task.set_editor_property("replace_existing", True)
        task.set_editor_property("automated", True)
        task.set_editor_property("save", False)
        tasks.append(task)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    result = {}
    for file in files:
        texture = unreal.load_asset(f"{destination}/{file.stem}")
        assert texture, file.stem
        texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
        texture.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
        texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
        texture.set_editor_property("never_stream", True)
        unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)
        result[file.stem] = texture
    return result


def theme_textures():
    files = sorted(THEME_SOURCE.glob("*.png"))
    assert files, "Run SourceAssets/UI/Theme/make_theme.ps1 first"
    return import_textures(files, THEME_PATH)


def image_brush(texture, size):
    brush = unreal.SlateBrush()
    brush.set_editor_property("resource_object", texture)
    image_size = unreal.DeprecateSlateVector2D()
    image_size.set_editor_property("x", size[0])
    image_size.set_editor_property("y", size[1])
    brush.set_editor_property("image_size", image_size)
    brush.set_editor_property("draw_as", unreal.SlateBrushDrawType.IMAGE)
    return brush


def box_brush(texture, margin=0.25):
    """9-slice brush so one small texture stretches to any panel or button size."""
    brush = image_brush(texture, (texture.blueprint_get_size_x(), texture.blueprint_get_size_y()))
    brush.set_editor_property("draw_as", unreal.SlateBrushDrawType.BOX)
    brush.set_editor_property("margin", unreal.Margin(margin, margin, margin, margin))
    return brush


class Builder:
    """Creates themed widgets inside one WidgetBlueprint's widget tree."""

    def __init__(self, widget_bp, textures):
        self.widget_bp = widget_bp
        self.tree = None
        self.textures = textures
        self.font = unreal.load_asset(THAI_FONT)
        self.variables = []

    def root_canvas(self, asset_path):
        name = asset_path.rsplit("/", 1)[1]
        canvas = unreal.load_object(None, f"{asset_path}.{name}:WidgetTree.RootCanvas")
        assert canvas, asset_path + " has no RootCanvas"
        canvas.clear_children()
        self.tree = canvas.get_outer()
        return canvas

    def make(self, widget_class, name):
        # Reusing a name with a different widget class is a fatal engine error, so move stale objects aside.
        stale = unreal.find_object(self.tree, name)
        if stale and stale.get_class() != widget_class.static_class():
            stale.rename(name + "_Stale" + str(abs(hash(stale.get_path_name())) % 100000))
        return unreal.new_object(widget_class, outer=self.tree, name=name)

    def variable(self, widget):
        """TextBlocks, Borders and Images are not Blueprint variables by default."""
        self.variables.append(widget.get_name())
        return widget

    def expose_variables(self):
        umg = unreal.get_default_object(unreal.UMGToolSet)
        for name in self.variables:
            umg.call_method("ToggleWidgetAsVariable", (self.widget_bp, unreal.find_object(self.tree, name), True))

    def text(self, name, label, size, color=WHITE, center=False, wrap=True):
        block = self.make(unreal.TextBlock, name)
        block.set_text(label)
        info = block.get_editor_property("font")
        info.set_editor_property("font_object", self.font)
        info.set_editor_property("size", size)
        block.set_editor_property("font", info)
        block.set_color_and_opacity(unreal.SlateColor(specified_color=color))
        block.set_auto_wrap_text(wrap)
        if center:
            block.set_editor_property("justification", unreal.TextJustify.CENTER)
        return block

    def image(self, name, texture, size):
        widget = self.make(unreal.Image, name)
        widget.set_brush(image_brush(texture, size))
        return widget

    def panel(self, name, padding=(28, 22, 28, 24)):
        border = self.make(unreal.Border, name)
        border.set_editor_property("background", box_brush(self.textures["T_UI_Panel"], 0.2))
        border.set_padding(unreal.Margin(*padding))
        return border

    def button(self, name, label, width=0, height=46, size=18):
        """SizeBox > Button (idle dark / hover gold / pressed orange) > centred caption."""
        box = self.make(unreal.SizeBox, name + "Size")
        box.set_height_override(height)
        if width:
            box.set_width_override(width)
        button = self.make(unreal.Button, name)
        style = button.get_editor_property("widget_style")
        for key, texture in (("normal", "T_UI_Button_Idle"), ("hovered", "T_UI_Button_Hover"), ("pressed", "T_UI_Button_Pressed")):
            style.set_editor_property(key, box_brush(self.textures[texture], 0.3))
        for key in ("normal_padding", "pressed_padding"):
            style.set_editor_property(key, unreal.Margin(10, 0, 10, 0))
        button.set_style(style)
        caption = self.text("Txt" + name[3:], label, size, center=True, wrap=False)
        button.add_child(caption)
        caption.slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
        caption.slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
        box.add_child(button)
        return box

    def tag(self, name, label):
        """Slanted gold header strip like the reference's SEASONAL EVENT label."""
        holder = self.make(unreal.SizeBox, name)
        holder.set_height_override(30)
        overlay = self.make(unreal.Overlay, name + "Overlay")
        strip = self.make(unreal.Image, name + "Strip")
        strip.set_brush(box_brush(self.textures["T_UI_Tag"], 0.1))
        overlay.add_child_to_overlay(strip)
        caption = self.text(name + "Text", label, 15, unreal.LinearColor(0.05, 0.04, 0.02, 1), wrap=False)
        slot = overlay.add_child_to_overlay(caption)
        slot.set_padding(unreal.Margin(12, 0, 24, 0))
        slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
        holder.add_child(overlay)
        return holder

    def bar(self, name, percent=0.5, height=10):
        box = self.make(unreal.SizeBox, name + "Size")
        box.set_height_override(height)
        progress = self.make(unreal.ProgressBar, name)
        style = progress.get_editor_property("widget_style")
        style.set_editor_property("background_image", box_brush(self.textures["T_UI_BarTrack"], 0.2))
        style.set_editor_property("fill_image", box_brush(self.textures["T_UI_BarFill"], 0.2))
        progress.set_editor_property("widget_style", style)
        progress.set_fill_color_and_opacity(WHITE)
        progress.set_percent(percent)
        box.add_child(progress)
        return box

    def divider(self, name):
        return self.image(name, self.textures["T_UI_Divider"], (256, 2))


def add(box, child, top=4, bottom=4, fill=False):
    """Append to a VerticalBox or HorizontalBox with padding."""
    if isinstance(box, unreal.VerticalBox):
        slot = box.add_child_to_vertical_box(child)
        slot.set_padding(unreal.Margin(0, top, 0, bottom))
    else:
        slot = box.add_child_to_horizontal_box(child)
        slot.set_padding(unreal.Margin(top, 0, bottom, 0))
        slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
    if fill:
        slot.set_size(unreal.SlateChildSize(value=1.0, size_rule=unreal.SlateSizeRule.FILL))
    return slot


# ---------------------------------------------------------------- Blueprint graph helpers
def write(graph, source, *expected):
    """Write DSL and fail loudly: the toolset only logs DSL errors as LogScript warnings."""
    unreal.SystemLibrary.execute_console_command(None, "FlushLog")
    start = LOG.stat().st_size
    Blueprint.write_graph_dsl(graph, source)
    unreal.SystemLibrary.execute_console_command(None, "FlushLog")
    with LOG.open("rb") as handle:
        handle.seek(start)
        fresh = handle.read().decode("utf-8", "replace")
    assert "LogScript: Warning" not in fresh, fresh[fresh.find("LogScript: Warning"):][:800]
    readback = Blueprint.read_graph_dsl(graph)
    for text in expected:
        assert text in readback, (graph.get_name(), text, readback[:600])


def function(bp, name, inputs=(), object_inputs=()):
    if name in [graph.get_name() for graph in Blueprint.list_graphs(bp)]:
        return Blueprint.get_graph(bp, name)
    graph = Blueprint.add_function_graph(bp, name)
    for param, kind in inputs:
        Blueprint.add_function_param(graph, param, kind, True)
    for param, cls in object_inputs:
        Blueprint.add_object_function_param(graph, param, cls, True)
    return graph


def node(graph, query):
    matches = [str(m) for m in Blueprint.find_node_types(graph, query)]
    exact = sorted(set(m for m in matches if m.endswith(query)))
    assert len(exact) == 1, (query, matches[:20])
    return exact[0]


def clear_event_graph(bp):
    """write_graph_dsl keeps existing bound events; drop everything but the default events first."""
    for old in Blueprint.find_nodes(Blueprint.get_graph(bp, "EventGraph")):
        if not (isinstance(old, unreal.K2Node_Event) and not isinstance(old, unreal.K2Node_ComponentBoundEvent)):
            Blueprint.delete_node(old)


def bind_clicks(bp, names):
    umg = unreal.get_default_object(unreal.UMGToolSet)
    for name in names:
        assert umg.call_method("BindToEventProperty", (bp, "OnClicked", name, unreal.Button.static_class())), name


HOST = "/Game/UI/Prototype/BP_TestNavigationHost"
MENU_WIDGET = "/Game/UI/MainMenu/WBP_MainMenu.WBP_MainMenu_C"
DRIVE_WIDGET = "/Game/UI/MainMenu/WBP_DriveHUD.WBP_DriveHUD_C"
OLD_DRIVE_WIDGET = "/Game/UI/Prototype/WBP_TestDriveNavigation.WBP_TestDriveNavigation_C"


def write_host():
    """BP_TestNavigationHost: menu maps show WBP_MainMenu, driving maps show WBP_DriveHUD (or the old test
    navigation until the HUD exists). Written from scratch: the host graph does not survive a DSL round trip."""
    drive = DRIVE_WIDGET if unreal.EditorAssetLibrary.does_asset_exist(DRIVE_WIDGET.split(".")[0]) else OLD_DRIVE_WIDGET
    host = unreal.load_asset(HOST)
    write(Blueprint.get_graph(host, "EventGraph"), f"""(event EventBeginPlay
  (Utilities|FlowControl|Delay :Duration 0.2)
  (bind controller (Game|GetPlayerController :PlayerIndex 0))
  (Class|PlayerController|SetShowMouseCursor :self controller :bShowMouseCursor true)
  (if (Variables|Default|GetDriving)
    (bind screen (UserInterface|CreateWidget :Class "{drive}" :OwningPlayer controller))
    (UserInterface|Viewport|AddtoViewport :self screen :ZOrder 100)
    (Input|SetInputModeGameAndUI :PlayerController controller :InMouseLockMode "DoNotLock" :bHideCursorDuringCapture false :bFlushInput true)
    (else
      (bind menu (UserInterface|CreateWidget :Class "{MENU_WIDGET}" :OwningPlayer controller))
      (UserInterface|Viewport|AddtoViewport :self menu :ZOrder 100)
      (Input|SetInputModeUIOnly :PlayerController controller :InWidgetToFocus menu :InMouseLockMode "DoNotLock" :bFlushInput true))))

(event Collision|EventActorBeginOverlap (OtherActor))

(event EventTick (DeltaSeconds))""", MENU_WIDGET.split(".")[1], drive.split(".")[1])
    Blueprint.compile_blueprint(host, warnings_as_errors=True)
    unreal.EditorAssetLibrary.save_loaded_asset(host, only_if_is_dirty=False)
    return drive

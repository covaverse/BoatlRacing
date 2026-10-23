"""Showroom step 3: WBP_Showroom layout and the BP_ShowroomStage turntable components.

Layout follows the garage screens of Forza Horizon / Need for Speed: category tabs and a horizontal row
of part cards along the bottom, a stats panel with +/- against stock on the right, and the camera moving
to whatever category is open (see BP_ShowroomStage.SetFocus in showroom_build_graphs.py).
Uses the shared menu theme (Tools/ui_theme.py), art cut from the main-menu reference (logo, account bar)
and card thumbnails captured in the showroom (SourceAssets/UI/Showroom/Textures/T_SR_Thumb_*.png).
Run Tools/mainmenu_build.py first, then from a live editor (PIE stopped):
  python Tools/run_editor_script.py Tools/showroom_build_ui.py
The widget layout is rebuilt from scratch on every run.
"""
import importlib
import sys
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

sys.path.insert(0, str(Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / "Tools"))
import ui_theme
importlib.reload(ui_theme)
from ui_theme import GOLD, MUTED, WHITE, add

BASE = "/Game/Showroom"
WIDGET = BASE + "/WBP_Showroom"
TEMPLATE = "/Game/UI/Prototype/WBP_TestMenu"
STAGE = BASE + "/BP_ShowroomStage"
MENU_TEXTURES = "/Game/UI/MainMenu/Textures"
THUMBS = ui_theme.ROOT / "SourceAssets/UI/Showroom/Textures"
BOAT_COUNT = 2
ENGINE_COUNT = 4
TABS = [("BtnTabBoat", "เรือ"), ("BtnTabEngine", "เครื่องยนต์"), ("BtnTabProp", "ใบพัด"), ("BtnTabLivery", "ลายเรือ")]
CARD = (232, 130)  # thumbnail size on screen

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"
textures = ui_theme.theme_textures()
for name in ("T_MM_CropLogo", "T_MM_CropTopBar"):
    textures[name] = unreal.load_asset(f"{MENU_TEXTURES}/{name}")
    assert textures[name], name + " missing: run Tools/mainmenu_build.py first"
thumbs = sorted(THUMBS.glob("T_SR_Thumb_*.png"))
assert len(thumbs) == BOAT_COUNT + ENGINE_COUNT, "capture the card thumbnails first"
textures.update(ui_theme.import_textures(thumbs, BASE + "/Textures"))

# ---------------------------------------------------------------- widget layout
if not unreal.EditorAssetLibrary.does_asset_exist(WIDGET):
    assert unreal.EditorAssetLibrary.duplicate_asset(TEMPLATE, WIDGET), "Could not copy the menu widget"
widget_bp = unreal.load_asset(WIDGET)
ui = ui_theme.Builder(widget_bp, textures)
canvas = ui.root_canvas(WIDGET)


def anchored(child, anchor, alignment, position, size=None):
    slot = canvas.add_child_to_canvas(child)
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
    slot.set_alignment(unreal.Vector2D(*alignment))
    slot.set_position(unreal.Vector2D(*position))
    if size:
        slot.set_size(unreal.Vector2D(*size))
    else:
        slot.set_auto_size(True)
    return slot


def marker(name):
    """Gold frame drawn over the chosen tab or card; Refresh toggles it."""
    image = ui.variable(ui.make(unreal.Image, name))
    image.set_brush(ui_theme.box_brush(textures["T_UI_Selected"], 0.3))
    image.set_visibility(unreal.SlateVisibility.HIDDEN)
    return image


def stacked(name, base, overlay_widget):
    holder = ui.make(unreal.Overlay, name)
    for child in (base, overlay_widget):
        slot = holder.add_child_to_overlay(child)
        slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
        slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
    return holder


def card(button_name, label_name, thumb, label):
    """Part card: thumbnail over a name strip, themed idle/hover/pressed, gold frame when selected."""
    button = ui.make(unreal.Button, button_name)
    style = button.get_editor_property("widget_style")
    for key, texture in (("normal", "T_UI_Button_Idle"), ("hovered", "T_UI_Button_Hover"), ("pressed", "T_UI_Button_Pressed")):
        style.set_editor_property(key, ui_theme.box_brush(textures[texture], 0.3))
    for key in ("normal_padding", "pressed_padding"):
        style.set_editor_property(key, unreal.Margin(6, 6, 6, 6))
    button.set_style(style)
    column = ui.make(unreal.VerticalBox, button_name + "Column")
    size = ui.make(unreal.SizeBox, button_name + "Thumb")
    size.set_width_override(CARD[0])
    size.set_height_override(CARD[1])
    size.add_child(ui.image(button_name + "Image", textures[thumb], CARD))
    add(column, size, 0, 4)
    add(column, ui.variable(ui.text(label_name, label, 17, WHITE, center=True, wrap=False)), 0, 2)
    button.add_child(column)
    return stacked(button_name + "Card", button, marker("Sel" + button_name[3:]))


# Top-left: logo, section tag and breadcrumb.
brand = ui.make(unreal.HorizontalBox, "Brand")
logo = ui.make(unreal.SizeBox, "LogoSize")
logo.set_width_override(240)
logo.set_height_override(81)
logo.add_child(ui.image("Logo", textures["T_MM_CropLogo"], (240, 81)))
add(brand, logo, 0, 14)
crumbs = ui.make(unreal.VerticalBox, "Crumbs")
tag_row = ui.make(unreal.HorizontalBox, "TagRow")
add(tag_row, ui.tag("TagShowroom", "SHOWROOM  ·  โชว์รูมเรือ"), 0, 0)
add(crumbs, tag_row, 6, 6)
add(crumbs, ui.variable(ui.text("TxtCrumb", "-", 20, WHITE, wrap=False)), 0, 0)
add(brand, crumbs, 0, 0)
anchored(brand, (0, 0), (0, 0), (32, 24))

# Top-right: account bar (same art as the main menu).
account = ui.make(unreal.SizeBox, "AccountSize")
account.add_child(ui.image("Account", textures["T_MM_CropTopBar"], (584, 60)))
anchored(account, (1, 0), (1, 0), (-28, 22), (438, 45))

# Right: details and stats against stock.
details = ui.make(unreal.SizeBox, "DetailsWidth")
details.set_width_override(380)
panel = ui.panel("Details", (26, 18, 26, 22))
column = ui.make(unreal.VerticalBox, "DetailsColumn")
add(column, ui.variable(ui.text("TxtPanelTag", "-", 14, GOLD, wrap=False)), 0, 2)
add(column, ui.variable(ui.text("TxtItemName", "-", 30, WHITE)), 0, 4)
add(column, ui.variable(ui.text("TxtItemDesc", "-", 15, MUTED)), 0, 6)
add(column, ui.divider("DetailsLine"), 6, 10)
for key, label in (("Power", "แรงขับ"), ("Speed", "ความเร็วปลาย")):
    stat = ui.make(unreal.HorizontalBox, f"{key}Row")
    add(stat, ui.text(f"Txt{key}Label", label, 15, MUTED, wrap=False), 0, 0, fill=True)
    add(stat, ui.variable(ui.text(f"Txt{key}", "-", 19, WHITE, wrap=False)), 8, 0)
    add(stat, ui.variable(ui.text(f"Txt{key}Delta", "-", 15, GOLD, wrap=False)), 10, 0)
    add(column, stat, 2, 2)
    add(column, ui.bar(f"{key}Bar", 0.5, 9), 2, 10)
add(column, ui.text("TxtStockNote", "เทียบกับหางยาวมาตรฐาน + เครื่องเดิม V4", 13, MUTED), 0, 0)
panel.add_child(column)
details.add_child(panel)
anchored(details, (1, 0.5), (1, 0.5), (-32, -40))

# Bottom centre: category tabs, then the card row for the open category.
dock = ui.make(unreal.VerticalBox, "Dock")
tabs = ui.make(unreal.HorizontalBox, "Tabs")
for index, (name, label) in enumerate(TABS):
    tab = stacked(name + "Tab", ui.button(name, label, width=170, height=42, size=18), marker("Sel" + name[3:]))
    add(tabs, tab, 0 if index == 0 else 8, 0)
slot = add(dock, tabs, 0, 10)
slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
switcher = ui.variable(ui.make(unreal.WidgetSwitcher, "CardSwitcher"))
for prefix, count, thumb in (("Boat", BOAT_COUNT, "T_SR_Thumb_Boat"), ("Engine", ENGINE_COUNT, "T_SR_Thumb_Engine")):
    cards = ui.make(unreal.HorizontalBox, prefix + "Cards")
    for index in range(count):
        add(cards, card(f"Btn{prefix}{index}", f"Txt{prefix}Card{index}", f"{thumb}{index}", "-"), 0 if index == 0 else 12, 0)
    switcher.add_child(cards).set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
add(dock, switcher, 0, 8)
notice = ui.variable(ui.text("TxtNotice", "คลิกการ์ดเพื่อติดตั้ง  ·  ค่าที่เลือกบันทึกให้ทันที", 14, MUTED, center=True))
add(dock, notice, 0, 0)
anchored(dock, (0.5, 1), (0.5, 1), (0, -24))

# Bottom right: drive (primary, gold at rest) and back to menu.
actions = ui.make(unreal.VerticalBox, "Actions")
add(actions, ui.button("BtnDrive", "ไปขับในคลอง", height=58, size=22), 0, 6)
add(actions, ui.button("BtnHome", "กลับเมนูหลัก", height=44, size=17), 0, 0)
anchored(actions, (1, 1), (1, 1), (-32, -28), (300, 116))
drive = unreal.find_object(ui.tree, "BtnDrive")
style = drive.get_editor_property("widget_style")
style.set_editor_property("normal", ui_theme.box_brush(textures["T_UI_Button_Hover"], 0.3))
style.set_editor_property("hovered", ui_theme.box_brush(textures["T_UI_Button_Pressed"], 0.3))
drive.set_style(style)
unreal.find_object(ui.tree, "TxtDrive").set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(0.04, 0.03, 0.02, 1)))

ui.expose_variables()
Blueprint.compile_blueprint(widget_bp)
assert unreal.EditorAssetLibrary.save_loaded_asset(widget_bp, only_if_is_dirty=False)
print("SHOWROOM_WIDGET_LAYOUT_READY")

# ---------------------------------------------------------------- stage components
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
stage = unreal.load_asset(STAGE)


def handles(bp):
    return {str(library.get_variable_name(library.get_data(h))): h for h in subobjects.k2_gather_subobject_data_for_blueprint(bp)}


def component(bp, parent, component_class, name):
    existing = handles(bp)
    if name in existing:
        handle = existing[name]
    else:
        handle, failure = subobjects.add_new_subobject(unreal.AddNewSubobjectParams(parent_handle=existing[parent], new_class=component_class, blueprint_context=bp))
        assert not str(failure), failure
        subobjects.rename_subobject(handle, unreal.Text(name))
    return library.get_object(library.get_data(handle))


turntable = component(stage, "DefaultSceneRoot", unreal.SceneComponent, "Turntable")
slot_component = component(stage, "Turntable", unreal.ChildActorComponent, "BoatSlot")
# The visual's pivot is mid-hull; its bounds centre (tail included) is 123 cm aft.
slot_component.set_editor_property("relative_location", unreal.Vector(-123, 0, 0))
# No default child class: a class on this template creates a child-actor template that leaked into M_Garage
# as a second, always-visible stock boat. RefreshBoat sets the class at BeginPlay instead.
slot_component.set_editor_property("child_actor_class", None)
camera = component(stage, "DefaultSceneRoot", unreal.CameraComponent, "Camera")
camera_location = unreal.Vector(-560, -1080, 210)
# Low three-quarter view, aimed a little above and left of the boat so the LED wall stays in frame and
# the boat sits right of the left-hand panel.
target = unreal.Vector(110, -70, 165)
camera.set_editor_property("relative_location", camera_location)
camera.set_editor_property("relative_rotation", unreal.MathLibrary.find_look_at_rotation(camera_location, target))
camera.set_editor_property("field_of_view", 50.0)
camera.set_editor_property("constrain_aspect_ratio", False)
Blueprint.compile_blueprint(stage)
unreal.EditorAssetLibrary.save_loaded_asset(stage, only_if_is_dirty=False)
print("SHOWROOM_STAGE_COMPONENTS_READY")

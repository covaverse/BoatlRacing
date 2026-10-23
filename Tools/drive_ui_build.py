"""In-drive HUD (WBP_DriveHUD) in the shared menu theme.

Top-left: loadout, menu/showroom buttons and controls. Bottom-right: speed, RPM and throttle read from
BP_LongtailPhysicsPawn every tick. BP_TestNavigationHost shows it on driving maps.
Run after Tools/mainmenu_build.py from a live editor (PIE stopped):
  python Tools/run_editor_script.py Tools/drive_ui_build.py
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

WIDGET = "/Game/UI/MainMenu/WBP_DriveHUD"
TEMPLATE = "/Game/UI/Prototype/WBP_TestMenu"
MENU_MAP = "/Game/Maps/M_MainMenu"
GARAGE_MAP = "/Game/Maps/M_Garage"
MAX_RPM = 6500.0  # matches the pawn's free-revving limit
MAX_KMH = 130.0

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"
textures = ui_theme.theme_textures()
textures["T_MM_CropLogo"] = unreal.load_asset("/Game/UI/MainMenu/Textures/T_MM_CropLogo")
assert textures["T_MM_CropLogo"], "run Tools/mainmenu_build.py first"

if not unreal.EditorAssetLibrary.does_asset_exist(WIDGET):
    assert unreal.EditorAssetLibrary.duplicate_asset(TEMPLATE, WIDGET)
widget_bp = unreal.load_asset(WIDGET)
ui = ui_theme.Builder(widget_bp, textures)
canvas = ui.root_canvas(WIDGET)


def anchored(child, anchor, alignment, position, size):
    slot = canvas.add_child_to_canvas(child)
    slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(*anchor), maximum=unreal.Vector2D(*anchor)))
    slot.set_alignment(unreal.Vector2D(*alignment))
    slot.set_position(unreal.Vector2D(*position))
    slot.set_size(unreal.Vector2D(*size))
    # Panels grow with their content (wrapped Thai lines vary), so size comes from the widgets inside.
    slot.set_auto_size(True)
    return slot


# ---------------------------------------------------------------- top-left: loadout and navigation
info = ui.panel("InfoPanel", (20, 14, 20, 16))
column = ui.make(unreal.VerticalBox, "InfoColumn")
logo = ui.make(unreal.SizeBox, "LogoSize")
logo.set_width_override(210)
logo.set_height_override(71)
logo.add_child(ui.image("Logo", textures["T_MM_CropLogo"], (210, 71)))
add(column, logo, 0, 4)
tags = ui.make(unreal.HorizontalBox, "TagRow")
add(tags, ui.tag("TagDrive", "FREE DRIVE  ·  ขับอิสระ"), 0, 0)
add(column, tags, 0, 6)
add(column, ui.variable(ui.text("TxtLoadout", "-", 17, WHITE, wrap=False)), 0, 8)
row = ui.make(unreal.HorizontalBox, "NavRow")
add(row, ui.button("BtnMenu", "เมนูหลัก", height=40, size=16), 0, 0, fill=True)
add(row, ui.button("BtnShowroom", "โชว์รูม", height=40, size=16), 8, 0, fill=True)
add(column, row, 0, 8)
add(column, ui.divider("InfoLine"), 0, 6)
add(column, ui.text("TxtControls", "W/S เร่ง / ถอย   A/D เลี้ยว\nQ/E กด / ยกหาง   SPACE คลัตช์   C กล้อง", 13, MUTED), 0, 0)
info.add_child(column)
anchored(info, (0, 0), (0, 0), (24, 24), (300, 268))

# ---------------------------------------------------------------- bottom-right: gauges
gauge = ui.panel("GaugePanel", (24, 14, 24, 18))
column = ui.make(unreal.VerticalBox, "GaugeColumn")
speed_row = ui.make(unreal.HorizontalBox, "SpeedRow")
add(speed_row, ui.variable(ui.text("TxtSpeed", "0", 64, WHITE, wrap=False)), 0, 0)
unit = ui.text("TxtUnit", "กม./ชม.", 18, GOLD, wrap=False)
slot = add(speed_row, unit, 10, 0)
slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_BOTTOM)
slot.set_padding(unreal.Margin(10, 0, 0, 14))
add(column, speed_row, 0, 2)
for key, label in (("Rpm", "รอบเครื่อง"), ("Throttle", "คันเร่ง")):
    stat = ui.make(unreal.HorizontalBox, f"{key}Row")
    add(stat, ui.text(f"Txt{key}Label", label, 14, MUTED, wrap=False), 0, 0, fill=True)
    add(stat, ui.variable(ui.text(f"Txt{key}", "-", 15, WHITE, wrap=False)), 8, 0)
    add(column, stat, 4, 2)
    add(column, ui.bar(f"{key}Bar", 0.0, 9), 2, 2)
gauge.add_child(column)
anchored(gauge, (1, 1), (1, 1), (-28, -28), (320, 212))

ui.expose_variables()
Blueprint.compile_blueprint(widget_bp)
unreal.EditorAssetLibrary.save_loaded_asset(widget_bp, only_if_is_dirty=False)
print("DRIVE_HUD_LAYOUT_READY")

# ---------------------------------------------------------------- graph
ui_theme.clear_event_graph(widget_bp)
for stale in [graph.get_name() for graph in Blueprint.list_graphs(widget_bp)]:
    if stale != "EventGraph":
        Blueprint.remove_function_graph(widget_bp, stale)
Blueprint.compile_blueprint(widget_bp)
var = lambda name: f"(Variables|WBP_DriveHUD|Get{name})"

loadout = ui_theme.function(widget_bp, "ShowLoadout")
gi = {key: ui_theme.node(loadout, "BPBoatGameInstance|" + key) for key in ("GetSelectedBoat", "GetSelectedEngine", "GetBoatInfo", "GetEngineInfo")}
text_to_string = ui_theme.node(loadout, "Utilities|String|ToString(Text)")
ui_theme.write(loadout, f"""(fn ShowLoadout ()
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      (bind (boatName boatText boatPower) ({gi['GetBoatInfo']} :self gi :Index ({gi['GetSelectedBoat']} :self gi)))
      (bind (engineName engineText enginePower engineTop) ({gi['GetEngineInfo']} :self gi :Index ({gi['GetSelectedEngine']} :self gi)))
      (bind line (Utilities|String|Append (Utilities|String|Append ({text_to_string} boatName) "  ·  ") ({text_to_string} engineName)))
      (Widget|SetText(Text) :self {var("TxtLoadout")} :InText (Utilities|Text|ToText(String) line)))
    (:CastFailed)))""", "TxtLoadout")

gauges = ui_theme.function(widget_bp, "UpdateGauges")
pawn = {key: ui_theme.node(gauges, "BPLongtailPhysicsPawn|" + key) for key in ("GetForwardSpeedKmh", "GetEngineRPM", "GetThrottle")}


def number(value, suffix=""):
    text = f"(Utilities|String|ToString(Integer) (Math|Float|Round {value}))"
    if suffix:
        text = f'(Utilities|String|Append {text} "{suffix}")'
    return f"(Utilities|Text|ToText(String) {text})"


ui_theme.write(gauges, f"""(fn UpdateGauges ()
  (bind boat (Utilities|Casting|CastToBP_LongtailPhysicsPawn (Game|GetPlayerPawn :PlayerIndex 0))
    (:then
      (bind speed ({pawn['GetForwardSpeedKmh']} :self boat))
      (bind rpm ({pawn['GetEngineRPM']} :self boat))
      (bind throttle ({pawn['GetThrottle']} :self boat))
      (Widget|SetText(Text) :self {var("TxtSpeed")} :InText {number("speed")})
      (Widget|SetText(Text) :self {var("TxtRpm")} :InText {number("rpm", " rpm")})
      (Progress|SetPercent :self {var("RpmBar")} :InPercent (/ rpm {MAX_RPM}))
      (bind throttlePercent (* (select (< throttle 0.0) (- throttle) throttle) 100.0))
      (Widget|SetText(Text) :self {var("TxtThrottle")} :InText {number("throttlePercent", " %")})
      (Progress|SetPercent :self {var("ThrottleBar")} :InPercent (/ throttlePercent 100.0)))
    (:CastFailed)))""", "GetEngineRPM", "ThrottleBar")

ui_theme.write(ui_theme.function(widget_bp, "Travel", [("Map", "string")]), """(fn Travel (Map)
  (Widget|RemoveFromParent self)
  (Game|OpenLevel(byName) :LevelName Map))""", "OpenLevel")
bodies = {"BtnMenu": f'(CallFunction|Travel :Map "{MENU_MAP}")', "BtnShowroom": f'(CallFunction|Travel :Map "{GARAGE_MAP}")'}
ui_theme.bind_clicks(widget_bp, bodies)
events = "\n\n".join(f"(event OnClicked({name})\n  {body})" for name, body in bodies.items())
ui_theme.write(Blueprint.get_graph(widget_bp, "EventGraph"), f"""(event UserInterface|EventConstruct
  (CallFunction|ShowLoadout))

(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (CallFunction|UpdateGauges))

{events}""", "UpdateGauges", "OnClicked(BtnShowroom)")
Blueprint.compile_blueprint(widget_bp, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(widget_bp, only_if_is_dirty=False)
print("DRIVE_HUD_GRAPH_READY")

# ---------------------------------------------------------------- host
print("DRIVE_HUD_HOST_READY", ui_theme.write_host())

"""Showroom step 4: graphs for BP_ShowroomStage and WBP_Showroom.

Stage: RefreshBoat (apply the saved boat/engine), SetFocus (camera target per category) and a Tick that
eases the camera to that target; the turntable spins on the boat overview and settles to a fixed pose
when the camera is on the engine bay.
Widget: category tabs, part cards, stats with +/- against stock, drive / back.
Run after showroom_build_ui.py from a live editor (PIE stopped):
  python Tools/run_editor_script.py Tools/showroom_build_graphs.py
"""
import importlib
import sys
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

sys.path.insert(0, str(Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / "Tools"))
import ui_theme
importlib.reload(ui_theme)
from ui_theme import function, node, write

BASE = "/Game/Showroom"
STAGE_CLASS = BASE + "/BP_ShowroomStage.BP_ShowroomStage_C"
WIDGET_CLASS = BASE + "/WBP_Showroom.WBP_Showroom_C"
DRIVE_MAP = "/Game/Maps/M_CanalBlockout"
MENU_MAP = "/Game/Maps/M_MainMenu"
BOAT_COUNT = 2
ENGINE_COUNT = 4
BASE_TOP_KMH = 110.0
# Camera shots in stage space (turntable at yaw 0: the boat's engine bay sits at about (117, 0, 90)).
SHOTS = {
    0: (unreal.Vector(-560, -1080, 210), unreal.Vector(110, -70, 165)),   # whole boat, turntable spinning
    1: (unreal.Vector(-230, -420, 300), unreal.Vector(70, 30, 70)),        # engine bay close-up
}
CAMERA_SPEED = 3.0
SPIN_DEG_PER_SEC = 8.0

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"


def vector(v):
    return f"(Math|Vector|MakeVector :X {v.x} :Y {v.y} :Z {v.z})"


def rotator(r):
    return f"(Math|Rotator|MakeRotator :Roll 0.0 :Pitch {r.pitch:.3f} :Yaw {r.yaw:.3f})"


# ---------------------------------------------------------------- stage
stage = unreal.load_asset(BASE + "/BP_ShowroomStage")
existing = [str(v) for v in Blueprint.list_variables(stage)]
for name, kind in (("FocusMode", "int"), ("CamTargetLoc", "Vector"), ("CamTargetRot", "Rotator")):
    if name not in existing:
        Blueprint.add_variable(stage, name, kind)
Blueprint.compile_blueprint(stage)
overview_loc, overview_aim = SHOTS[0]
defaults = unreal.get_default_object(stage.generated_class())
defaults.set_editor_property("CamTargetLoc", overview_loc)
defaults.set_editor_property("CamTargetRot", unreal.MathLibrary.find_look_at_rotation(overview_loc, overview_aim))

refresh_boat = function(stage, "RefreshBoat")
apply_class = node(refresh_boat, "BPBoatGameInstance|ApplyBoatClass")
apply_visual = node(refresh_boat, "BPThaiLongtailBoat|ApplyLoadoutVisual")
# Setting the same boat class again does not respawn the child, so re-apply the engine explicitly.
write(refresh_boat, f"""(fn RefreshBoat ()
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      ({apply_class} :self gi :Slot (Variables|Default|GetBoatSlot))
      (bind boat (Utilities|Casting|CastToBP_ThaiLongtailBoat (Class|ChildActorComponent|GetChildActor (Variables|Default|GetBoatSlot)))
        (:then
          ({apply_visual} :self boat))
        (:CastFailed)))
    (:CastFailed)))""", "ApplyBoatClass", "ApplyLoadoutVisual")

loc1, aim1 = SHOTS[1]
write(function(stage, "SetFocus", [("Mode", "int")]), f"""(fn SetFocus (Mode)
  (Variables|Default|SetFocusMode Mode)
  (if (== Mode 1)
    (Variables|Default|SetCamTargetLoc {vector(loc1)})
    (Variables|Default|SetCamTargetRot {rotator(unreal.MathLibrary.find_look_at_rotation(loc1, aim1))})
    (else
      (Variables|Default|SetCamTargetLoc {vector(overview_loc)})
      (Variables|Default|SetCamTargetRot {rotator(unreal.MathLibrary.find_look_at_rotation(overview_loc, overview_aim))}))))""",
      "SetCamTargetRot")

# The short delay lets possession and the level's auto-activate camera settle before the stage takes the view.
write(Blueprint.get_graph(stage, "EventGraph"), f"""(event EventBeginPlay
  (Utilities|FlowControl|Delay 0.2)
  (bind pc (Game|GetPlayerController 0))
  (Game|Player|SetViewTargetwithBlend :self pc :NewViewTarget self)
  (Class|PlayerController|SetShowMouseCursor :self pc :bShowMouseCursor true)
  ; The GameMode's DefaultPawn (a grey sphere) spawns at the PlayerStart under the platform.
  (Rendering|SetActorHiddenInGame :self (Game|GetPlayerPawn :PlayerIndex 0) :bNewHidden true)
  (CallFunction|RefreshBoat)
  (bind screen (UserInterface|CreateWidget :Class "{WIDGET_CLASS}" :OwningPlayer pc))
  (UserInterface|Viewport|AddtoViewport :self screen :ZOrder 100)
  (Input|SetInputModeUIOnly :PlayerController pc :InWidgetToFocus screen :InMouseLockMode "DoNotLock" :bFlushInput true))

(event Collision|EventActorBeginOverlap (OtherActor))

(event EventTick (DeltaSeconds)
  (bind cam (Variables|Default|GetCamera))
  (bind table (Variables|Default|GetTurntable))
  (Transformation|SetRelativeLocation :self cam :NewLocation (Math|Interpolation|VInterpTo :Current (Class|SceneComponent|GetRelativeLocation :self cam) :Target (Variables|Default|GetCamTargetLoc) :DeltaTime DeltaSeconds :InterpSpeed {CAMERA_SPEED}))
  (Transformation|SetRelativeRotation :self cam :NewRotation (Math|Interpolation|RInterpTo :Current (Class|SceneComponent|GetRelativeRotation :self cam) :Target (Variables|Default|GetCamTargetRot) :DeltaTime DeltaSeconds :InterpSpeed {CAMERA_SPEED}))
  (if (== (Variables|Default|GetFocusMode) 0)
    (Transformation|AddRelativeRotation :self table :DeltaRotation (Math|Rotator|MakeRotator :Yaw (* DeltaSeconds {SPIN_DEG_PER_SEC})))
    (else
      (Transformation|SetRelativeRotation :self table :NewRotation (Math|Interpolation|RInterpTo :Current (Class|SceneComponent|GetRelativeRotation :self table) :Target (Math|Rotator|MakeRotator :Yaw 0.0) :DeltaTime DeltaSeconds :InterpSpeed {CAMERA_SPEED})))))""",
      "CreateWidget", "VInterpTo", "RInterpTo")
Blueprint.compile_blueprint(stage, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(stage, only_if_is_dirty=False)
print("SHOWROOM_STAGE_GRAPH_READY")

# ---------------------------------------------------------------- widget
widget = unreal.load_asset(BASE + "/WBP_Showroom")
ui_theme.clear_event_graph(widget)
# Function graphs hold typed getters of the rebuilt layout; recreate all of them so types always match.
for stale in [graph.get_name() for graph in Blueprint.list_graphs(widget)]:
    if stale != "EventGraph":
        Blueprint.remove_function_graph(widget, stale)
if "Category" not in [str(v) for v in Blueprint.list_variables(widget)]:
    Blueprint.add_variable(widget, "Category", "int")
Blueprint.compile_blueprint(widget)
var = lambda name: f"(Variables|WBP_Showroom|Get{name})"


def text(widget_name, value):
    return f"(Widget|SetText(Text) :self {var(widget_name)} :InText {value})"


def show_if(widget_name, condition):
    return f"""(if {condition}
        (Widget|SetVisibility :self {var(widget_name)} :InVisibility "HitTestInvisible")
        (else (Widget|SetVisibility :self {var(widget_name)} :InVisibility "Hidden")))"""


def as_text(string_expr):
    return f"(Utilities|Text|ToText(String) {string_expr})"


def signed(int_expr, suffix):
    return f'(Utilities|String|Append (Utilities|String|Append (select (>= {int_expr} 0) "+" "") (Utilities|String|ToString(Integer) {int_expr})) "{suffix}")'


refresh = function(widget, "Refresh")
gi = {key: node(refresh, "BPBoatGameInstance|" + key) for key in
      ("GetSelectedBoat", "GetSelectedEngine", "GetBoatInfo", "GetEngineInfo", "SetSelectedBoat", "SaveSelection", "SelectEngine")}
to_string = node(refresh, "Utilities|String|ToString(Text)")
boat_cards = "\n".join(f"""      (bind (cardBoat{i} cardBoatText{i} cardBoatPower{i}) ({gi['GetBoatInfo']} :self gi :Index {i}))
      {text(f"TxtBoatCard{i}", f"cardBoat{i}")}
      {show_if(f"SelBoat{i}", f"(== boat {i})")}""" for i in range(BOAT_COUNT))
engine_cards = "\n".join(f"""      (bind (cardEngine{i} cardEngineText{i} cardEnginePower{i} cardEngineTop{i}) ({gi['GetEngineInfo']} :self gi :Index {i}))
      {text(f"TxtEngineCard{i}", f"cardEngine{i}")}
      {show_if(f"SelEngine{i}", f"(== engine {i})")}""" for i in range(ENGINE_COUNT))
write(refresh, f"""(fn Refresh ()
  (bind category (Variables|Default|GetCategory))
  {show_if("SelTabBoat", "(== category 0)")}
  {show_if("SelTabEngine", "(== category 1)")}
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      (bind boat ({gi['GetSelectedBoat']} :self gi))
      (bind engine ({gi['GetSelectedEngine']} :self gi))
{boat_cards}
{engine_cards}
      (bind (boatName boatText boatPower) ({gi['GetBoatInfo']} :self gi :Index boat))
      (bind (engineName engineText enginePower engineTop) ({gi['GetEngineInfo']} :self gi :Index engine))
      (if (== category 0)
        {text("TxtPanelTag", '"BOAT  ·  ตัวเรือ"')}
        {text("TxtItemName", "boatName")}
        {text("TxtItemDesc", "boatText")}
        {text("TxtCrumb", as_text(f'(Utilities|String|Append "เรือ  ›  " ({to_string} boatName))'))}
        (else
          {text("TxtPanelTag", '"ENGINE  ·  เครื่องยนต์"')}
          {text("TxtItemName", "engineName")}
          {text("TxtItemDesc", "engineText")}
          {text("TxtCrumb", as_text(f'(Utilities|String|Append "เครื่องยนต์  ›  " ({to_string} engineName))'))}))
      (bind power (Math|Float|Round (* (* boatPower enginePower) 100.0)))
      (bind speed (Math|Float|Round (* engineTop {BASE_TOP_KMH})))
      {text("TxtPower", as_text('(Utilities|String|Append (Utilities|String|ToString(Integer) power) " %")'))}
      {text("TxtPowerDelta", as_text(signed("(- power 100)", "")))}
      (Progress|SetPercent :self {var("PowerBar")} :InPercent (/ (* (* boatPower enginePower) 100.0) 125.0))
      {text("TxtSpeed", as_text('(Utilities|String|Append (Utilities|String|ToString(Integer) speed) " กม./ชม.")'))}
      {text("TxtSpeedDelta", as_text(signed(f"(- speed {int(BASE_TOP_KMH)})", "")))}
      (Progress|SetPercent :self {var("SpeedBar")} :InPercent (/ engineTop 1.2)))
    (:CastFailed)))""", "SelEngine3", "TxtSpeedDelta")

stage_focus = node(refresh, "BPShowroomStage|SetFocus")
stage_refresh = node(refresh, "BPShowroomStage|RefreshBoat")
write(function(widget, "UpdateStage"), f"""(fn UpdateStage ()
  (bind stage (Actor|GetActorOfClass :ActorClass "{STAGE_CLASS}"))
  (Utilities|IsValid stage
    (:"Is Valid"
      ({stage_refresh} :self stage)
      ({stage_focus} :self stage :Mode (Variables|Default|GetCategory)))
    (:"Is Not Valid")))""", "SetFocus")
write(function(widget, "SetCategory", [("Index", "int")]), f"""(fn SetCategory (Index)
  (Variables|Default|SetCategory Index)
  (Switcher|SetActiveWidgetIndex :self {var("CardSwitcher")} :Index Index)
  (CallFunction|UpdateStage)
  (CallFunction|Refresh))""", "UpdateStage")
write(function(widget, "PickBoat", [("Index", "int")]), f"""(fn PickBoat (Index)
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      ({gi['SetSelectedBoat']} :self gi :SelectedBoat Index)
      ({gi['SaveSelection']} :self gi)
      (CallFunction|UpdateStage)
      (CallFunction|Refresh))
    (:CastFailed)))""", "SaveSelection")
write(function(widget, "PickEngine", [("Index", "int")]), f"""(fn PickEngine (Index)
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      ({gi['SelectEngine']} :self gi :Index Index)
      (CallFunction|UpdateStage)
      (CallFunction|Refresh))
    (:CastFailed)))""", "SelectEngine")
write(function(widget, "Notice", [("Message", "string")]), f"""(fn Notice (Message)
  {text("TxtNotice", as_text("Message"))})""", "TxtNotice")
write(function(widget, "Travel", [("Map", "string")]), """(fn Travel (Map)
  (Widget|RemoveFromParent self)
  (Game|OpenLevel(byName) :LevelName Map))""", "OpenLevel")

clicks = {"BtnTabBoat": "(CallFunction|SetCategory :Index 0)", "BtnTabEngine": "(CallFunction|SetCategory :Index 1)",
          "BtnTabProp": '(CallFunction|Notice :Message "ใบพัด  ·  เร็ว ๆ นี้")', "BtnTabLivery": '(CallFunction|Notice :Message "ลายเรือ  ·  เร็ว ๆ นี้")',
          "BtnDrive": f'(CallFunction|Travel :Map "{DRIVE_MAP}")', "BtnHome": f'(CallFunction|Travel :Map "{MENU_MAP}")'}
clicks.update({f"BtnBoat{i}": f"(CallFunction|PickBoat :Index {i})" for i in range(BOAT_COUNT)})
clicks.update({f"BtnEngine{i}": f"(CallFunction|PickEngine :Index {i})" for i in range(ENGINE_COUNT)})
ui_theme.bind_clicks(widget, clicks)
events = "\n\n".join(f"(event OnClicked({name})\n  {body})" for name, body in clicks.items())
write(Blueprint.get_graph(widget, "EventGraph"), f"""(event UserInterface|EventConstruct
  (CallFunction|SetCategory :Index 0))

{events}""", "OnClicked(BtnEngine3)", "OnClicked(BtnTabEngine)", "SetCategory")
Blueprint.compile_blueprint(widget, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(widget, only_if_is_dirty=False)
print("SHOWROOM_WIDGET_GRAPH_READY")

"""Showroom step 2: graphs for the game instance, boat visual and physics pawn.

Run after showroom_build_assets.py from a live editor (PIE stopped):
  python Tools/run_editor_script.py Tools/showroom_build_logic.py
"""
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

BASE = "/Game/Showroom"
GI = BASE + "/BP_BoatGameInstance"
SAVE_CLASS = BASE + "/BP_ShowroomSave.BP_ShowroomSave_C"
VISUAL = "/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat"
VISUAL_CLASS = VISUAL + ".BP_ThaiLongtailBoat_C"
R3_CLASS = BASE + "/Boats/BP_Boat_R3.BP_Boat_R3_C"
PAWN = "/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn"
ENGINE_CLASSES = [BASE + f"/Engines/{name}.{name}_C" for name in ("BP_Engine_Racing150", "BP_Engine_Thai150", "BP_Engine_River125")]

# Catalogue. Power scales DriveForce; top-speed scales the governor (stock target is 110 km/h).
BOATS = [
    ("หางยาวมาตรฐาน", "เรือหางยาวแข่งลำเดิม ตัวเรือไม้สักกว้าง นิ่งในคลื่น", 1.0),
    ("R3 สปีดเรเซอร์", "ตัวเรือ Refine03 ลายกราฟิกแข่ง ทรงเพรียว พุ่งออกตัวดีกว่า", 1.06),
]
ENGINES = [
    ("เครื่องเดิม V4", "เครื่องรถยนต์ดัดแปลงแบบดั้งเดิม แรงบิดหนัก นิ่งทุกรอบ", 1.0, 1.0),
    ("Racing 150cc", "เครื่องแข่งสูบเดียว ฝาไทเทเนียม รอบจัด ปลายไหลแรงที่สุด", 1.12, 1.12),
    ("Thai 150cc", "เครื่องไทยแต่งซิ่ง ท่อสูตร ตอบสนองคันเร่งไว", 1.05, 1.04),
    ("River Racer 125cc", "เครื่องเล็กน้ำหนักเบา หม้อน้ำระบายความร้อน ขับง่าย", 0.9, 0.95),
]

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"


def quote(text):
    return '"' + text.replace('"', "'") + '"'


def function(bp, name, inputs=(), outputs=(), object_inputs=()):
    """Create (or reuse) a function graph with typed parameters."""
    if name in [graph.get_name() for graph in Blueprint.list_graphs(bp)]:
        return Blueprint.get_graph(bp, name)
    graph = Blueprint.add_function_graph(bp, name)
    for param, kind in inputs:
        Blueprint.add_function_param(graph, param, kind, True)
    for param, cls in object_inputs:
        Blueprint.add_object_function_param(graph, param, cls, True)
    for param, kind in outputs:
        Blueprint.add_function_param(graph, param, kind, False)
    return graph


def node(graph, query):
    matches = [str(m) for m in Blueprint.find_node_types(graph, query)]
    exact = [m for m in matches if m.endswith(query)]
    assert len(exact) == 1, (query, matches[:20])
    return exact[0]


LOG = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_log_dir())) / "BoatlRacing.log"


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


def chain(variable, values):
    """(if (== v 1) a (elif (== v 2) b (else default))) built from {index: statement}; index 0 is the default."""
    branches = sorted(i for i in values if i)
    source = f"(else {values[0]})"
    for index in reversed(branches):
        source = f"(elif (== {variable} {index}) {values[index]} {source})"
    return "(if" + source[len("(elif"):]


# ---------------------------------------------------------------- game instance
gi = unreal.load_asset(GI)
info = function(gi, "GetBoatInfo", [("Index", "int")], [("Name", "text"), ("Description", "text"), ("PowerScale", "float")])
write(info, "(fn GetBoatInfo (Index)\n  " + chain("Index", {i: f"(return {quote(n)} {quote(d)} {p})" for i, (n, d, p) in enumerate(BOATS)}) + ")", "1.06")

info = function(gi, "GetEngineInfo", [("Index", "int")], [("Name", "text"), ("Description", "text"), ("PowerScale", "float"), ("TopSpeedScale", "float")])
write(info, "(fn GetEngineInfo (Index)\n  " + chain("Index", {i: f"(return {quote(n)} {quote(d)} {p} {t})" for i, (n, d, p, t) in enumerate(ENGINES)}) + ")", "1.12", "0.95")

scales = function(gi, "GetLoadoutScales", outputs=[("Power", "float"), ("TopSpeed", "float")])
write(scales, """(fn GetLoadoutScales ()
  (bind (boatName boatText boatPower) (CallFunction|GetBoatInfo :Index (Variables|Default|GetSelectedBoat)))
  (bind (engineName engineText enginePower engineTop) (CallFunction|GetEngineInfo :Index (Variables|Default|GetSelectedEngine)))
  (return (* boatPower enginePower) engineTop))""", "GetEngineInfo")

apply_boat = function(gi, "ApplyBoatClass", object_inputs=[("Slot", unreal.ChildActorComponent.static_class())])
write(apply_boat, f"""(fn ApplyBoatClass (Slot)
  (if (== (Variables|Default|GetSelectedBoat) 1)
    (ChildActorComponent|SetChildActorClass :self Slot :InClass "{R3_CLASS}")
    (else (ChildActorComponent|SetChildActorClass :self Slot :InClass "{VISUAL_CLASS}"))))""", "BP_Boat_R3")

save = function(gi, "SaveSelection")
graph_probe = Blueprint.get_graph(gi, "SaveSelection")
set_boat = node(graph_probe, "SetBoat")
set_engine = node(graph_probe, "SetEngine")
write(save, f"""(fn SaveSelection ()
  (bind created (SaveGame|CreateSaveGameObject "{SAVE_CLASS}"))
  (bind record (Utilities|Casting|CastToBP_ShowroomSave created)
    (:then
      ({set_boat} :self record :Boat (Variables|Default|GetSelectedBoat))
      ({set_engine} :self record :Engine (Variables|Default|GetSelectedEngine))
      (SaveGame|SaveGametoSlot record "BoatShowroom" 0))
    (:CastFailed)))""", "SaveGameToSlot")

pick_boat = function(gi, "CycleBoat", [("Delta", "int")])
write(pick_boat, f"""(fn CycleBoat (Delta)
  (bind next (+ (Variables|Default|GetSelectedBoat) Delta))
  (Variables|Default|SetSelectedBoat (select (> next {len(BOATS) - 1}) 0 (select (< next 0) {len(BOATS) - 1} next)))
  (CallFunction|SaveSelection))""", "SaveSelection")

pick_engine = function(gi, "SelectEngine", [("Index", "int")])
write(pick_engine, f"""(fn SelectEngine (Index)
  (Variables|Default|SetSelectedEngine (Math|Integer|Clamp(Integer) Index 0 {len(ENGINES) - 1}))
  (CallFunction|SaveSelection))""", "SaveSelection")

events = Blueprint.get_graph(gi, "EventGraph")
get_boat = node(events, "GetBoat")
get_engine = node(events, "GetEngine")
write(events, f"""(event EventInit
  (if (SaveGame|DoesSaveGameExist "BoatShowroom" 0)
    (bind loaded (SaveGame|LoadGamefromSlot "BoatShowroom" 0))
    (bind record (Utilities|Casting|CastToBP_ShowroomSave loaded)
      (:then
        (Variables|Default|SetSelectedBoat (Math|Integer|Clamp(Integer) ({get_boat} :self record) 0 {len(BOATS) - 1}))
        (Variables|Default|SetSelectedEngine (Math|Integer|Clamp(Integer) ({get_engine} :self record) 0 {len(ENGINES) - 1})))
      (:CastFailed))))""", "SetSelectedEngine")
Blueprint.compile_blueprint(gi, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(gi, only_if_is_dirty=False)
print("SHOWROOM_GI_READY")

# ---------------------------------------------------------------- boat visual
# Each visual applies the saved engine on BeginPlay, so the showroom, menu preview and driving pawn all match.
# ApplyLoadoutVisual can run again on a live boat (showroom engine change), so it first removes any
# engine it spawned earlier and shows the stock engine parts again.
visual = unreal.load_asset(VISUAL)
remove_engine = function(visual, "RemoveSwappedEngine")
write(remove_engine, """(fn RemoveSwappedEngine ()
  (for part (Components|GetChildrenComponents :self (Variables|Default|GetEngineAssembly) :bIncludeAllDescendants true)
    (Rendering|SetVisibility :self part :bNewVisibility true))
  (bind mounted (Variables|Default|GetEngineActor))
  (Utilities|IsValid mounted
    (:"Is Valid"
      (Actor|DestroyActor :self mounted))
    (:"Is Not Valid")))""", "DestroyActor", "SetVisibility")
apply_visual = function(visual, "ApplyLoadoutVisual")
selected_engine = node(apply_visual, "BPBoatGameInstance|GetSelectedEngine")
alt_hull = node(apply_visual, "GetAltHull")
hide = """(for part (Components|GetChildrenComponents :self (Variables|Default|Get{0}) :bIncludeAllDescendants true)
      (Rendering|SetVisibility :self part :bNewVisibility false))"""
spawn = {i + 1: f"""(Variables|Default|SetEngineActor (Game|SpawnActorfromClass :Class "{path}" :SpawnTransform (Math|Transform|MakeTransform) :CollisionHandlingOverride "AlwaysSpawn"))"""
         for i, path in enumerate(ENGINE_CLASSES)}
spawn[0] = "(Variables|Default|SetEngineActor (Variables|Default|GetEngineActor))"
# Always set the stock hull's visibility both ways: when the showroom swaps R3 back to the stock class,
# the ChildActorComponent carries the old child's hidden component state over to the new child.
stock_hull = """(for part (Components|GetChildrenComponents :self (Variables|Default|Get{0}) :bIncludeAllDescendants true)
    (Rendering|SetVisibility :self part :bNewVisibility stockHull))"""
write(apply_visual, f"""(fn ApplyLoadoutVisual ()
  (CallFunction|RemoveSwappedEngine)
  (bind stockHull (not ({alt_hull})))
  {stock_hull.format("HullAssembly")}
  {stock_hull.format("InteriorAssembly")}
  {stock_hull.format("DetailsAssembly")}
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      (bind engine ({selected_engine} :self gi))
      (if (!= engine 0)
        {hide.format("EngineAssembly")}
        {chain("engine", spawn)}
        (bind mounted (Variables|Default|GetEngineActor))
        (Utilities|IsValid mounted
          (:"Is Valid"
            (Transformation|AttachActorToComponent :self mounted :Parent (Variables|Default|GetEngineAssembly))
            (Transformation|SetActorRelativeLocation :self mounted :NewRelativeLocation (Variables|Default|GetEngineMountOffset)))
          (:"Is Not Valid"
            (Development|PrintString "WARNING engine spawn failed; loadout not applied")))))
    (:CastFailed)))""", "BP_Engine_River125", "AttachActorToComponent", "DetailsAssembly")

events = Blueprint.get_graph(visual, "EventGraph")
# A child actor's BeginPlay runs while its parent is still being constructed, where SpawnActor is refused
# ("running a ConstructionScript"); wait one frame before spawning the engine.
write(events, """(event EventBeginPlay
  (Utilities|FlowControl|Delay :Duration 0.0)
  (CallFunction|ApplyLoadoutVisual))

(event Collision|EventActorBeginOverlap (OtherActor))

(event EventTick (DeltaSeconds))

(event EventEndPlay (EndPlayReason)
  (CallFunction|RemoveSwappedEngine))""", "ApplyLoadoutVisual", "RemoveSwappedEngine")
Blueprint.compile_blueprint(visual, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(visual, only_if_is_dirty=False)
print("SHOWROOM_VISUAL_READY")

# ---------------------------------------------------------------- physics pawn
# ApplyLoadout swaps the visual hull and scales thrust/governor after the handling profile is cached.
pawn = unreal.load_asset(PAWN)
loadout = function(pawn, "ApplyLoadout")
apply_class = node(loadout, "BPBoatGameInstance|ApplyBoatClass")
scales_node = node(loadout, "BPBoatGameInstance|GetLoadoutScales")
write(loadout, f"""(fn ApplyLoadout ()
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      ({apply_class} :self gi :Slot (Variables|Default|GetBoatVisual))
      (Collision|SetActorEnableCollision :self (Class|ChildActorComponent|GetChildActor (Variables|Default|GetBoatVisual)) :bNewActorEnableCollision false)
      (bind (power top) ({scales_node} :self gi))
      (Variables|Default|SetDriveForce (* (Variables|Default|GetDriveForce) power))
      (Variables|Default|SetGovernorStartKmh (* (Variables|Default|GetGovernorStartKmh) top))
      (Variables|Default|SetTargetForwardSpeedKmh (* (Variables|Default|GetTargetForwardSpeedKmh) top)))
    (:CastFailed)))""", "ApplyBoatClass", "SetTargetForwardSpeedKmh")

# LoadHandlingProfile does not survive a DSL round trip (getters on the profile object read back ambiguously),
# so hook the call onto the end of its valid branch with a single node instead of rewriting the graph.
profile = Blueprint.get_graph(pawn, "LoadHandlingProfile")
infos = Blueprint.get_node_infos(Blueprint.find_nodes(profile))
if not any("ApplyLoadout" in str(info.type_id) for info in infos):
    last = [info for info in infos if str(info.type_id).endswith("SetVibrationStartKmh")]
    assert len(last) == 1, "LoadHandlingProfile changed; inspect before inserting ApplyLoadout"
    then = [pin for pin in last[0].output_pins if str(pin.name) == "then"][0]
    assert not then.connected_pins, "SetVibrationStartKmh is no longer the end of the valid branch"
    call = Blueprint.create_node(profile, "CallFunction|ApplyLoadout", unreal.IntPoint(last[0].position.x + 300, last[0].position.y))
    execute = [pin for pin in Blueprint.get_node_infos([call])[0].input_pins if str(pin.name) == "execute"][0]
    Blueprint.connect_pins(then.pin_id, execute.pin_id)
Blueprint.compile_blueprint(pawn, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(pawn, only_if_is_dirty=False)
print("SHOWROOM_PAWN_READY")

"""Showroom step 1: Blueprint assets for boat and engine choices.

Run from a live editor (PIE stopped):
  python Tools/run_editor_script.py Tools/showroom_build_assets.py
Creates /Game/Showroom (GameInstance, SaveGame, stage, engine and boat variants)
and adds loadout variables to BP_ThaiLongtailBoat. Safe to rerun.
"""
import datetime
import math
import shutil
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

ROOT = Path(unreal.Paths.project_dir())
BASE = "/Game/Showroom"
VISUAL = "/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat"
PAWN = "/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn"
R3 = "/Game/Boats/Modular/ThaiLongtailRefine03/VH_ThaiLongtailBoat_LOD0/StaticMeshes"
# Engine meshes share one origin at the engine base. Yaw turns the output side toward the stern (+X);
# scale makes the small motorcycle engines read clearly in the stock engine bay.
ENGINES = {
    "BP_Engine_Racing150": ("/Game/Engines/Racing150cc", 90.0, 1.6),
    "BP_Engine_Thai150": ("/Game/Engines/Thai150cc", 0.0, 1.5),
    "BP_Engine_River125": ("/Game/Engines/River125cc", 0.0, 1.35),
}
# Refine03 hull is 400 cm long along -Y (stern). Fit it to the stock 621 x 114 x 73 cm hull, stern toward +X.
R3_ROTATION = unreal.Rotator(0, 0, 90)
R3_SCALE = unreal.Vector(1.15, 1.55, 1.22)

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world(), "Stop PIE first"
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary


def backup():
    folder = ROOT / "Saved" / "Backups" / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-showroom")
    folder.mkdir(parents=True, exist_ok=True)
    for path in (VISUAL, PAWN):
        source = ROOT / ("Content" + path[len("/Game"):] + ".uasset")
        shutil.copy2(source, folder / source.name)
    for name in ("DefaultEngine.ini",):
        shutil.copy2(ROOT / "Config" / name, folder / name)
    return folder


def ensure_blueprint(name, parent, folder=BASE):
    existing = unreal.load_asset(folder + "/" + name)
    return existing if existing else Blueprint.create(folder, name, parent)


def ensure_var(bp, name, kind):
    if name not in [str(v) for v in Blueprint.list_variables(bp)]:
        Blueprint.add_variable(bp, name, kind)


def handles(bp):
    result = {}
    for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
        data = library.get_data(handle)
        result[str(library.get_variable_name(data))] = handle
    return result


def add_component(bp, parent_handle, component_class, name):
    existing = handles(bp)
    if name in existing:
        handle = existing[name]
    else:
        params = unreal.AddNewSubobjectParams(parent_handle=parent_handle, new_class=component_class, blueprint_context=bp)
        handle, failure = subobjects.add_new_subobject(params)
        assert not str(failure), failure
        subobjects.rename_subobject(handle, unreal.Text(name))
    return handle, library.get_object(library.get_data(handle))


def meshes_in(folder):
    found = []
    for path in unreal.EditorAssetLibrary.list_assets(folder, recursive=True):
        asset = unreal.load_asset(str(path))
        if isinstance(asset, unreal.StaticMesh):
            found.append(asset)
    assert found, folder
    return found


def fitted_offset(meshes, yaw, scale):
    """Location that centres the rotated, scaled engine on X/Y and puts its base at Z=0."""
    low = [1e9] * 3
    high = [-1e9] * 3
    cos, sin = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    for mesh in meshes:
        box = mesh.get_bounding_box()
        for x in (box.min.x, box.max.x):
            for y in (box.min.y, box.max.y):
                for z in (box.min.z, box.max.z):
                    point = ((x * cos - y * sin) * scale, (x * sin + y * cos) * scale, z * scale)
                    for axis, value in enumerate(point):
                        low[axis] = min(low[axis], value)
                        high[axis] = max(high[axis], value)
    return unreal.Vector(-(low[0] + high[0]) / 2, -(low[1] + high[1]) / 2, -low[2]), [h - l for h, l in zip(high, low)]


saved = backup()
report = []

visual = unreal.load_asset(VISUAL)
for name, kind in (("EngineMountOffset", "Vector"), ("bAltHull", "bool")):
    ensure_var(visual, name, kind)
if "EngineActor" not in [str(v) for v in Blueprint.list_variables(visual)]:
    Blueprint.add_object_variable(visual, "EngineActor", unreal.Actor.static_class())
Blueprint.compile_blueprint(visual)
defaults = unreal.get_default_object(visual.generated_class())
defaults.set_editor_property("EngineMountOffset", unreal.Vector(240, 0, 50))
unreal.EditorAssetLibrary.save_loaded_asset(visual, only_if_is_dirty=False)

for name, (folder, yaw, scale) in ENGINES.items():
    bp = ensure_blueprint(name, unreal.Actor.static_class(), BASE + "/Engines")
    root = handles(bp)["DefaultSceneRoot"]
    meshes = meshes_in(folder)
    offset, size = fitted_offset(meshes, yaw, scale)
    fit_handle, fit = add_component(bp, root, unreal.SceneComponent, "Fit")
    fit.set_editor_property("relative_location", offset)
    fit.set_editor_property("relative_rotation", unreal.Rotator(0, 0, yaw))
    fit.set_editor_property("relative_scale3d", unreal.Vector(scale, scale, scale))
    for mesh in meshes:
        _, component = add_component(bp, fit_handle, unreal.StaticMeshComponent, mesh.get_name())
        component.set_editor_property("static_mesh", mesh)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
        component.set_editor_property("generate_overlap_events", False)
    Blueprint.compile_blueprint(bp)
    unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)
    report.append(f"{name} meshes={len(meshes)} size_cm={[round(v) for v in size]}")

boat = ensure_blueprint("BP_Boat_R3", visual.generated_class(), BASE + "/Boats")
boat_handles = handles(boat)
hull_handle, hull = add_component(boat, boat_handles["BoatRoot"], unreal.SceneComponent, "R3Hull")
hull.set_editor_property("relative_rotation", R3_ROTATION)
hull.set_editor_property("relative_scale3d", R3_SCALE)
for mesh in meshes_in(R3):
    _, component = add_component(boat, hull_handle, unreal.StaticMeshComponent, mesh.get_name().replace("VH_ThaiLongtailBoat_", "R3_").replace("_LOD0", ""))
    component.set_editor_property("static_mesh", mesh)
    component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    component.set_editor_property("generate_overlap_events", False)
Blueprint.compile_blueprint(boat)
boat_defaults = unreal.get_default_object(boat.generated_class())
boat_defaults.set_editor_property("bAltHull", True)
unreal.EditorAssetLibrary.save_loaded_asset(boat, only_if_is_dirty=False)

print("SHOWROOM_ASSETS_READY backup=" + str(saved) + " | " + " | ".join(report))

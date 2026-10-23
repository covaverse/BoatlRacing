import datetime
import re
import shutil
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint


ROOT = Path(unreal.Paths.project_dir())
CATALOG = "/Game/UI/Catalog"
PAWN = "/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn"
VISUAL = "/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat"
HANDLING = "/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling"
FIELDS = {
    "UIIdleRPM": 900.0,
    "UILoadedMaxRPM": 5600.0,
    "UIFreeMaxRPM": 6500.0,
    "UIShaftRatio": 0.25,
    "UIShaftFullRPM": 1400.0,
}


def create_data(name, asset_class):
    existing = unreal.load_asset(f"{CATALOG}/{name}")
    if existing:
        return existing
    factory = unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class", asset_class)
    asset = unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, CATALOG, asset_class, factory)
    assert asset, name
    return asset


def install():
    editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
    assert not editor.get_game_world(), "Stop PIE before installing the frontend"
    assert hasattr(unreal, "BoatDefinition"), "Build and load the updated BoatlRacingPhysics plugin first"
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    backup = ROOT / "Saved" / "Backups" / (datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + "-frontend")
    backup.mkdir(parents=True, exist_ok=True)
    for relative in (
        "Content/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn.uasset",
        "Config/DefaultEngine.ini",
        "Config/DefaultGame.ini",
    ):
        source = ROOT / relative
        shutil.copy2(source, backup / source.name)

    pawn = unreal.load_asset(PAWN)
    assert pawn
    variables = [str(variable) for variable in Blueprint.list_variables(pawn)]
    for name in FIELDS:
        if name not in variables:
            Blueprint.add_variable(pawn, name, "float")
            Blueprint.set_variable_category(pawn, name, "Default")
    Blueprint.compile_blueprint(pawn, warnings_as_errors=True)
    defaults = unreal.get_default_object(pawn.generated_class())
    for name, value in FIELDS.items():
        defaults.set_editor_property(name, value)

    drive = Blueprint.get_graph(pawn, "UpdateDriveState_0")
    shaft = Blueprint.get_graph(pawn, "UpdateShaftState")
    for graph, label in ((drive, "drive"), (shaft, "shaft")):
        original = Blueprint.read_graph_dsl(graph)
        (backup / f"{label}.dsl").write_text(original, encoding="utf-8")
        source = original
        if label == "drive" and "GetUIIdleRPM" not in source:
            replacements = {
                "900.0": "(Variables|Default|GetUIIdleRPM)",
                "5600.0": "(- (Variables|Default|GetUIFreeMaxRPM) (Variables|Default|GetUIIdleRPM))",
                "4700.0": "(- (Variables|Default|GetUILoadedMaxRPM) (Variables|Default|GetUIIdleRPM))",
            }
        elif label == "shaft" and "GetUIShaftRatio" not in source:
            replacements = {
                "0.25": "(Variables|Default|GetUIShaftRatio)",
                "1400.0": "(Variables|Default|GetUIShaftFullRPM)",
            }
        else:
            replacements = {}
        for number, expression in replacements.items():
            source, count = re.subn(r"(?<![\w.])" + re.escape(number) + r"(?![\w.])", lambda match: expression, source)
            assert count > 0, f"Expected RPM constant {number} in {label}; restore backup and inspect graph"
        if source != original:
            Blueprint.write_graph_dsl(graph, source)
    Blueprint.compile_blueprint(pawn, warnings_as_errors=True)
    assert "GetUIIdleRPM" in Blueprint.read_graph_dsl(drive)
    assert "GetUIShaftRatio" in Blueprint.read_graph_dsl(shaft)
    unreal.EditorAssetLibrary.save_loaded_asset(pawn, only_if_is_dirty=False)

    engine = create_data("DA_StockEngine", unreal.BoatEngineDefinition)
    engine.set_editor_property("id", "stock_longtail")
    engine.set_editor_property("display_name", "Longtail / เครื่องเดิม")
    for name, value in {"idle_rpm": 900.0, "loaded_max_rpm": 5600.0, "free_max_rpm": 6500.0,
                        "shaft_ratio": 0.25, "shaft_full_rpm": 1400.0, "engine_mass_kg": 0.0, "drive_force": 0.0}.items():
        engine.set_editor_property(name, value)
    unreal.EditorAssetLibrary.save_loaded_asset(engine)

    boat = create_data("DA_ThaiLongtail", unreal.BoatDefinition)
    boat.set_editor_property("id", "thai_longtail")
    boat.set_editor_property("display_name", "Thai Longtail / เรือหางยาว")
    boat.set_editor_property("pawn_class", pawn.generated_class())
    boat.set_editor_property("handling_profile", unreal.load_asset(HANDLING))
    boat.set_editor_property("compatible_engines", ["stock_longtail"])
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    source_actor = actors.spawn_actor_from_class(unreal.load_asset(VISUAL).generated_class(), unreal.Vector())
    assert source_actor
    parts = []
    for component in source_actor.get_components_by_class(unreal.MeshComponent):
        if not component.get_editor_property("visible"):
            continue
        part = unreal.BoatPreviewPart()
        if isinstance(component, unreal.StaticMeshComponent):
            mesh = component.get_editor_property("static_mesh")
            if not mesh:
                continue
            part.set_editor_property("static_mesh", mesh)
        elif isinstance(component, unreal.SkeletalMeshComponent):
            mesh = component.get_skeletal_mesh_asset()
            if not mesh:
                continue
            part.set_editor_property("skeletal_mesh", mesh)
        else:
            continue
        part.set_editor_property("transform", unreal.MathLibrary.make_relative_transform(component.get_world_transform(), source_actor.get_actor_transform()))
        part.set_editor_property("materials", [component.get_material(index) for index in range(component.get_num_materials())])
        parts.append(part)
    actors.destroy_actor(source_actor)
    assert parts, "The boat preview has no meshes"
    boat.set_editor_property("preview_parts", parts)
    image_file = ROOT / "Docs/images/hero.png"
    if image_file.exists() and not unreal.EditorAssetLibrary.does_asset_exist(CATALOG + "/T_LongtailPreview"):
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(image_file))
        task.set_editor_property("destination_path", CATALOG)
        task.set_editor_property("destination_name", "T_LongtailPreview")
        task.set_editor_property("automated", True)
        task.set_editor_property("save", True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    image = unreal.load_asset(CATALOG + "/T_LongtailPreview")
    if image:
        boat.set_editor_property("thumbnail", image)
    unreal.EditorAssetLibrary.save_loaded_asset(boat)

    if not unreal.EditorAssetLibrary.does_asset_exist(CATALOG + "/SMX_BoatMaster"):
        factory = unreal.SoundMixFactory()
        mix = unreal.AssetToolsHelpers.get_asset_tools().create_asset("SMX_BoatMaster", CATALOG, unreal.SoundMix, factory)
        assert mix
        unreal.EditorAssetLibrary.save_loaded_asset(mix)

    levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    for name in ("M_MainMenu", "M_Garage"):
        path = "/Game/Maps/" + name
        if unreal.EditorAssetLibrary.does_asset_exist(path):
            continue
        assert levels.new_level(path)
        light = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 900), unreal.Rotator(-40, -35, 0))
        light.set_actor_label("Garage_KeyLight")
        light.light_component.set_editor_property("intensity", 5.0)
        sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 600))
        sky.light_component.set_editor_property("intensity", 1.5)
        sky.light_component.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
        cubemap = unreal.load_asset("/Engine/EngineResources/DefaultTextureCube")
        if cubemap:
            sky.light_component.set_editor_property("cubemap", cubemap)
        floor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(0, 0, -140))
        floor.static_mesh_component.set_static_mesh(unreal.load_asset("/Engine/BasicShapes/Cube"))
        floor.set_actor_scale3d(unreal.Vector(50, 50, 0.1))
        floor.set_actor_label("Garage_DisplayFloor")
        actors.spawn_actor_from_class(unreal.PlayerStart, unreal.Vector(0, -1000, 500))
        assert levels.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    print("BOAT_FRONTEND_INSTALLED", str(backup), "preview_parts", len(parts))


install()

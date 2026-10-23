from pathlib import Path

import unreal


editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
assert not editor.get_game_world(), "Stop PIE before creating frontend scenes"
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
root = Path(unreal.Paths.project_dir())
assert root.name.lower() == "boatl racing".replace(" ", "")
cube = unreal.load_asset("/Engine/BasicShapes/Cube")
wood = unreal.load_asset("/Game/Blockout/Materials/MI_Blockout_HouseWood")
metal = unreal.load_asset("/Game/Blockout/Materials/MI_Blockout_Roof")
signal = unreal.load_asset("/Game/Blockout/Materials/MI_Blockout_Signal")
boat_class = unreal.load_asset("/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat").generated_class()


def box(name, position, scale, material=None):
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(*position))
    actor.set_actor_label(name)
    actor.set_folder_path("Frontend/Set")
    actor.static_mesh_component.set_static_mesh(cube)
    actor.set_actor_scale3d(unreal.Vector(*scale))
    if material:
        actor.static_mesh_component.set_material(0, material)
    return actor


def build(path, garage):
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        assert levels.load_level(path)
    else:
        assert levels.new_level(path)
    for actor in actors.get_all_level_actors():
        if str(actor.get_folder_path()).startswith("Frontend") or actor.get_name() in (
            "StaticMeshActor_0", "Floor_0", "DirectionalLight_0", "SkyLight_0"
        ):
            actors.destroy_actor(actor)
    box("Frontend_Floor", (0, 0, -10), (45, 45, 0.2), metal)
    box("Frontend_DisplayPlatform", (80, 0, 75), (13, 5, 0.4), wood)
    for offset in (-230, 230):
        box("Frontend_HullCradle", (offset, 0, 115), (0.8, 1.2, 0.4), metal)
    if garage:
        box("Frontend_BackWall", (0, 850, 450), (40, 0.3, 9), metal)
        box("Frontend_Workbench", (900, 600, 100), (6, 2, 1.8), wood)
        for offset in (-1400, -700, 0, 700, 1400):
            box("Frontend_WallRib", (offset, 820, 450), (0.25, 0.35, 9), signal)
    else:
        for offset in (-900, 900):
            box("Frontend_DockPillar", (offset, 500, 350), (0.5, 0.5, 7), wood)
        box("Frontend_DockCanopy", (0, 500, 740), (28, 9, 0.25), wood)
        box("Frontend_CanalBackdrop", (0, 2600, -35), (80, 35, 0.1), metal)
    boat = actors.spawn_actor_from_class(boat_class, unreal.Vector(80, 0, 155), unreal.Rotator(0, 18, 0))
    boat.set_actor_label("Frontend_PreviewBoat")
    boat.set_folder_path("Frontend/Preview")
    boat.set_editor_property("tags", ["FrontendPreview"])
    boat.set_actor_tick_enabled(False)
    for component in boat.get_components_by_class(unreal.PrimitiveComponent):
        component.set_simulate_physics(False)
        component.set_collision_enabled(unreal.CollisionEnabled.NO_COLLISION)
    key = actors.spawn_actor_from_class(unreal.DirectionalLight, unreal.Vector(0, 0, 1500), unreal.Rotator(-35, -55, 0))
    key.set_folder_path("Frontend/Lighting")
    key.light_component.set_editor_property("intensity", 6.0)
    key.light_component.set_editor_property("light_color", unreal.Color(255, 223, 190, 255))
    fill = actors.spawn_actor_from_class(unreal.PointLight, unreal.Vector(-450, -350, 700))
    fill.set_folder_path("Frontend/Lighting")
    fill.light_component.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    fill.light_component.set_editor_property("intensity", 3500.0)
    fill.light_component.set_editor_property("attenuation_radius", 3000.0)
    sky = actors.spawn_actor_from_class(unreal.SkyLight, unreal.Vector(0, 0, 1000))
    sky.set_folder_path("Frontend/Lighting")
    sky.light_component.set_editor_property("intensity", 1.0)
    sky.light_component.set_editor_property("source_type", unreal.SkyLightSourceType.SLS_SPECIFIED_CUBEMAP)
    cubemap = unreal.load_asset("/Engine/EngineResources/DefaultTextureCube")
    if cubemap:
        sky.light_component.set_editor_property("cubemap", cubemap)
    camera = actors.spawn_actor_from_class(unreal.CameraActor, unreal.Vector(-1050, -1350, 600), unreal.Rotator(-14, 53, 0))
    camera.set_actor_label("Frontend_ShowcaseCamera")
    camera.set_folder_path("Frontend/Camera")
    camera.set_editor_property("auto_activate_for_player", unreal.AutoReceiveInput.PLAYER0)
    camera.camera_component.set_editor_property("field_of_view", 45.0)
    camera.camera_component.set_editor_property("constrain_aspect_ratio", False)
    camera.set_is_temporarily_hidden_in_editor(True)
    assert levels.save_current_level()
    print("FRONTEND_SCENE_SAVED", path)


build("/Game/Maps/M_MainMenu", False)
assert levels.load_level("/Game/Maps/M_Garage")
for actor in actors.get_all_level_actors():
    if actor.get_actor_label().startswith(("Frontend_", "Garage_")):
        actor.set_folder_path("Frontend/Legacy")
build("/Game/Maps/M_Garage", True)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(unreal.Vector(-1050, -1350, 600), unreal.Rotator(-14, 53, 0))
print("FRONTEND_SCENES_READY")

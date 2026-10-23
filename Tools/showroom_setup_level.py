"""Showroom step 5: put the turntable stage into M_Garage and point menus at it.

Run after showroom_build_graphs.py from a live editor (PIE stopped):
  python Tools/run_editor_script.py Tools/showroom_setup_level.py
Config/DefaultEngine.ini must name BP_BoatGameInstance as GameInstanceClass; this script
sets the same value on the loaded settings so the running editor uses it without a restart.
"""
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

GAME_INSTANCE = "/Game/Showroom/BP_BoatGameInstance.BP_BoatGameInstance_C"
STAGE = "/Game/Showroom/BP_ShowroomStage"
GARAGE = "/Game/Maps/M_Garage"
# Old garage pieces replaced by the stage: the menu UI host, the two overlapping static preview boats,
# and the hull cradles the rotating boat would pass through.
REMOVE = ("UI_TestNavigationHost", "Frontend_PreviewBoat", "Frontend_HullCradle")
MENU_LABELS = {"/Game/UI/Prototype/WBP_TestMenu": "โชว์รูมเรือ", "/Game/UI/Prototype/WBP_TestDriveNavigation": "โชว์รูมเรือ"}

editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world(), "Stop PIE first"
settings = unreal.get_default_object(unreal.GameMapsSettings)
settings.set_editor_property("game_instance_class", unreal.SoftClassPath(GAME_INSTANCE))

for path, label in MENU_LABELS.items():
    name = path.rsplit("/", 1)[1]
    caption = unreal.load_object(None, f"{path}.{name}:WidgetTree.BtnGarageText")
    if caption:
        caption.set_text(label)
        menu = unreal.load_asset(path)
        Blueprint.compile_blueprint(menu, warnings_as_errors=True)
        unreal.EditorAssetLibrary.save_loaded_asset(menu, only_if_is_dirty=False)

actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
assert levels.load_level(GARAGE)
stage_class = unreal.load_asset(STAGE).generated_class()
platform = None
removed = []
for actor in actors.get_all_level_actors():
    label = actor.get_actor_label()
    if label in REMOVE or actor.get_class() == stage_class:
        removed.append(label)
        actors.destroy_actor(actor)
    elif label == "Frontend_DisplayPlatform" and str(actor.get_folder_path()) == "Frontend/Set":
        platform = actor
assert platform, "Frontend/Set/Frontend_DisplayPlatform not found"
# A child-actor template ("*_CAT_*") once leaked into this level as a real, always-visible stock boat.
# It is not returned by get_all_level_actors, so find it by outer.
level = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_path_name().split(".")[0]
boat_class = unreal.load_asset("/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat").generated_class()
for leaked in [a for a in unreal.ObjectIterator(boat_class) if "_CAT_" in a.get_name() and a.get_path_name().startswith(level + ".")]:
    removed.append(leaked.get_name())
    if not actors.destroy_actor(leaked):
        leaked.rename(None, unreal.get_transient_package())
origin, extent = platform.get_actor_bounds(False)
stage = actors.spawn_actor_from_class(stage_class, unreal.Vector(origin.x, origin.y, origin.z + extent.z + 1))
stage.set_actor_label("Showroom_Stage")
stage.set_folder_path("Showroom")
assert levels.save_current_level()
print("SHOWROOM_LEVEL_READY removed=" + ",".join(removed) + f" stage_z={origin.z + extent.z + 1:.0f}")

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint


assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"
BASE = "/Game/UI/Prototype"
MAPS = {
    "BtnHome": "/Game/Maps/M_MainMenu",
    "BtnGarage": "/Game/Maps/M_Garage",
    "BtnStart": "/Game/Maps/M_CanalBlockout",
    "BtnCanal": "/Game/Maps/M_CanalBlockout",
    "BtnCalm": "/Game/Maps/M_WaterPhysicsTest",
    "BtnSmall": "/Game/Maps/M_WaterSmallWavesTest",
    "BtnHigh": "/Game/Maps/M_WaterHighWavesTest",
}


def exact(graph, query):
    matches = Blueprint.find_node_types(graph, query)
    assert len(matches) == 1, (query, matches)
    Blueprint.get_node_type_pins(graph, matches[0])
    return matches[0]


for name in ("WBP_TestMenu", "WBP_TestDriveNavigation"):
    widget = unreal.load_asset(BASE + "/" + name)
    graph = Blueprint.get_graph(widget, "EventGraph")
    source = Blueprint.read_graph_dsl(graph)
    remove = exact(graph, "Widget|RemovefromParent")
    Blueprint.get_node_type_pins(graph, "Game|OpenLevel(byName)")
    for button, level in MAPS.items():
        marker = f"(event OnClicked({button}))"
        if marker in source:
            source = source.replace(marker, f'''(event OnClicked({button})
  ({remove} :self self)
  (Game|OpenLevel(byName) :LevelName "{level}"))''')
    if name == "WBP_TestMenu":
        switcher = exact(graph, "GetPageSwitcher")
        Blueprint.get_node_type_pins(graph, "Switcher|SetActiveWidgetIndex")
        for button, index in (("BtnMaps", 1), ("BtnSettings", 2), ("BtnBack", 0)):
            marker = f"(event OnClicked({button}))"
            source = source.replace(marker, f'''(event OnClicked({button})
  (Switcher|SetActiveWidgetIndex :self ({switcher}) :Index {index}))''')
    Blueprint.write_graph_dsl(graph, source)
    Blueprint.compile_blueprint(widget, warnings_as_errors=True)
    assert unreal.EditorAssetLibrary.save_loaded_asset(widget, only_if_is_dirty=False)
    print("NAV_WIDGET_WIRED", name)

host = unreal.load_asset(BASE + "/BP_TestNavigationHost")
if not host:
    host = Blueprint.create(BASE, "BP_TestNavigationHost", unreal.Actor.static_class())
if "Driving" not in [str(name) for name in Blueprint.list_variables(host)]:
    Blueprint.add_variable(host, "Driving", "bool")
    Blueprint.set_variable_instance_editable(host, "Driving", True)
Blueprint.compile_blueprint(host)
graph = Blueprint.get_graph(host, "EventGraph")
driving = exact(graph, "GetDriving")
for node in ("UserInterface|CreateWidget", "UserInterface|Viewport|AddtoViewport", "Game|GetPlayerController", "Class|PlayerController|SetShowMouseCursor", "Input|SetInputModeGameAndUI", "Input|SetInputModeUIOnly"):
    Blueprint.get_node_type_pins(graph, node)
source = f'''(event EventBeginPlay
  (Utilities|FlowControl|Delay :Duration 0.2)
  (bind controller (Game|GetPlayerController :PlayerIndex 0))
  (Class|PlayerController|SetShowMouseCursor :self controller :bShowMouseCursor true)
  (if ({driving})
    (bind screen (UserInterface|CreateWidget :Class "{BASE}/WBP_TestDriveNavigation.WBP_TestDriveNavigation_C" :OwningPlayer controller))
    (UserInterface|Viewport|AddtoViewport :self screen :ZOrder 100)
    (Input|SetInputModeGameAndUI :PlayerController controller :InMouseLockMode "DoNotLock" :bHideCursorDuringCapture false :bFlushInput true)
    (else
      (bind camera (Actor|GetActorOfClass :ActorClass "/Script/Engine.CameraActor"))
      (Game|Player|SetViewTargetwithBlend :self controller :NewViewTarget camera :BlendTime 0.0)
      (bind screen (UserInterface|CreateWidget :Class "{BASE}/WBP_TestMenu.WBP_TestMenu_C" :OwningPlayer controller))
      (UserInterface|Viewport|AddtoViewport :self screen :ZOrder 100)
      (Input|SetInputModeUIOnly :PlayerController controller :InWidgetToFocus screen :InMouseLockMode "DoNotLock" :bFlushInput true))))
'''
Blueprint.write_graph_dsl(graph, source)
Blueprint.compile_blueprint(host, warnings_as_errors=True)
assert unreal.EditorAssetLibrary.save_loaded_asset(host, only_if_is_dirty=False)
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
for path in ("/Game/Maps/M_MainMenu", "/Game/Maps/M_Garage", "/Game/Maps/M_CanalBlockout", "/Game/Maps/M_WaterPhysicsTest", "/Game/Maps/M_WaterSmallWavesTest", "/Game/Maps/M_WaterHighWavesTest"):
    assert levels.load_level(path)
    for actor in actors.get_all_level_actors():
        if actor.get_class() == host.generated_class():
            actors.destroy_actor(actor)
    actor = actors.spawn_actor_from_class(host.generated_class(), unreal.Vector(0, 0, 1000))
    actor.set_actor_label("UI_TestNavigationHost")
    actor.set_folder_path("UI")
    actor.set_editor_property("Driving", path not in ("/Game/Maps/M_MainMenu", "/Game/Maps/M_Garage"))
    assert levels.save_current_level()
    print("NAV_HOST_SAVED", path)
assert levels.load_level("/Game/Maps/M_MainMenu")
print("NAVIGATION_READY")

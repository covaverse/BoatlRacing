import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

print("UMG_CLASSES", [name for name in dir(unreal) if "UMGTool" in name])
widget = unreal.load_asset("/Game/UI/Prototype/WBP_TestMenu")
graph = Blueprint.get_graph(widget, "EventGraph")
for query in ("OpenLevel", "SetActiveWidgetIndex", "SetVisibility", "CreateWidget", "AddtoViewport", "SetInputMode", "ShowMouseCursor", "GetCurrentLevelName", "GetPlayerController", "SetKeyboardFocus"):
    print("NAV_NODE", query, Blueprint.find_node_types(graph, query))
for node in ("Game|OpenLevel(byName)", "Switcher|SetActiveWidgetIndex", "UserInterface|CreateWidget", "UserInterface|Viewport|AddtoViewport", "Input|SetInputModeGameAndUI", "Input|SetInputModeUIOnly", "Class|PlayerController|SetShowMouseCursor", "Game|GetCurrentLevelName", "Game|GetPlayerController"):
    info = Blueprint.get_node_type_pins(graph, node)
    print("NAV_PINS", node, [str(pin.name) for pin in info.input_pins])
print("UMG_METHODS", [name for name in dir(unreal.UMGToolSet) if any(word in name for word in ("add_widget", "bind_to", "toggle_widget"))])
print("BOUND_GRAPH", Blueprint.read_graph_dsl(graph))
print("BOUND_EVENTS", [(info.type_id, info.node.get_name()) for info in Blueprint.get_node_infos(Blueprint.find_nodes(graph, "OnClicked", None, False))])
print("SWITCHER_GET", Blueprint.find_node_types(graph, "GetPageSwitcher"))
for query in ("GetActorOfClass", "SetViewTarget", "FlowControl|Delay"):
    for node in Blueprint.find_node_types(graph, query):
        info = Blueprint.get_node_type_pins(graph, node)
        print("CAMERA_PINS", node, [str(pin.name) for pin in info.input_pins])
print("FONT_FACTORIES", [name for name in dir(unreal) if "Font" in name and "Factory" in name])

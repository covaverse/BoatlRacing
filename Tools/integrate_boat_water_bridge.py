import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools


ROOT = Path(unreal.Paths.project_dir())
BP_PATH = "/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn"
blueprint = unreal.load_asset(BP_PATH)
assert blueprint is not None
apply_changes = "-BoatApplyWaterBridge" in unreal.SystemLibrary.get_command_line()
# Blueprint-local actions are absent from this engine's commandlet action database.
assert "-run=pythonscript" not in unreal.SystemLibrary.get_command_line().lower(), (
    "Run this integration inside Unreal Editor after loading BlueprintBasicsSkill; "
    "commandlet graph inspection is read-only, not an editing path."
)

if "PropWaterVelocity" not in BlueprintTools.list_variables(blueprint):
    BlueprintTools.add_variable(blueprint, "PropWaterVelocity", "Vector")
    BlueprintTools.compile_blueprint(blueprint, True)

for graph_name in ("UpdateWaterPropState", "ApplyTailWaterSteering", "ConfigureBoatMass"):
    graph = BlueprintTools.get_graph(blueprint, graph_name)
    source = (ROOT / "Tools/BlueprintDSL/WaterBridge" / (graph_name + ".dsl")).read_text()
    for function in ("ApplyLaunchPitch", "LoadHandlingProfile"):
        placeholder = "CallFunction|" + function
        if placeholder not in source:
            continue
        types = list(BlueprintTools.find_node_types(graph, "", []))
        matches = [node for node in types if node.split("|")[-1].replace(" ", "") == function]
        print("BOAT_BRIDGE_FUNCTION_TYPES", function, json.dumps(matches))
        if not matches:
            original = BlueprintTools.read_graph_dsl(graph)
            existing_type = "|" + function
            assert "(" + existing_type in original, (function, original)
            print("BOAT_BRIDGE_EXISTING_FUNCTION_PINS",
                  BlueprintTools.get_node_type_pins(graph, existing_type))
            matches = [existing_type]
        assert len(matches) == 1, (function, matches)
        source = source.replace(placeholder, matches[0])
    BlueprintTools.write_graph_dsl(graph, source)
    BlueprintTools.compile_blueprint(blueprint, True)
    readback = BlueprintTools.read_graph_dsl(graph)
    print("BOAT_BRIDGE_GRAPH", graph_name, readback)
    required = {
        "UpdateWaterPropState": "SampleWaveSurface",
        "ApplyTailWaterSteering": "CalculateTailWaterForce",
        "ConfigureBoatMass": "SetHullPontoonRadii",
    }[graph_name]
    assert required in readback, (graph_name, readback)
    assert "GetSternWaveHeight" not in readback

if apply_changes:
    assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint)
    print("BOAT_BRIDGE_SAVED", blueprint.get_path_name())
else:
    print("BOAT_BRIDGE_DRY_RUN_NO_ASSET_WRITES")

print("BOAT_BRIDGE_COMPILE_SUCCESS", json.dumps({"apply": apply_changes}))

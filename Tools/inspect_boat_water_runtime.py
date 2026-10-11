import json
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.material import MaterialTools


BP_PATH = "/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn"
blueprint = unreal.load_asset(BP_PATH)
assert blueprint is not None
graph = BlueprintTools.get_graph(blueprint, "UpdateWaterPropState")
for name in ("SampleWaveSurface", "SetHullPontoonRadii", "CalculateTailWaterForce"):
    print("BOAT_NATIVE_NODE", name,
          BlueprintTools.find_node_types(graph, name, []))
    print("BOAT_NATIVE_PINS", name,
          BlueprintTools.get_node_type_pins(graph, "Boat|Water|" + name))

for graph_name in ("UpdateWaterPropState", "ApplyTailWaterSteering",
                   "ConfigureBoatMass", "LoadHandlingProfile", "UpdateDriveState_0"):
    print("BOAT_GRAPH_BEGIN", graph_name)
    print(BlueprintTools.read_graph_dsl(BlueprintTools.get_graph(blueprint, graph_name)))
    print("BOAT_GRAPH_END", graph_name)

material = unreal.load_asset("/Water/Materials/WaterSurface/Water_Material_Ocean")
while isinstance(material, unreal.MaterialInstance):
    material = material.get_editor_property("parent")
print("BOAT_BASE_WATER_MATERIAL", material.get_path_name())
print("BOAT_BASE_WATER_PROPERTIES", unreal.ToolsetLibrary.get_object_properties(
    material, ["BlendMode", "ShadingModel", "OpacityMaskClipValue"]))
for expression in MaterialTools.get_expressions(material):
    fields = ["ParameterName"] if "Parameter" in expression.get_class().get_name() else []
    if isinstance(expression, unreal.MaterialExpressionMaterialFunctionCall):
        fields.append("MaterialFunction")
    print("BOAT_WATER_EXPRESSION", expression.get_class().get_name(),
          unreal.ToolsetLibrary.get_object_properties(expression, fields) if fields else "")

print("BOAT_NATIVE_API", unreal.BoatlRacingWaterLibrary.sample_wave_surface.__doc__)
print("BOAT_NATIVE_FORCE_API", unreal.BoatlRacingWaterLibrary.calculate_tail_water_force.__doc__)

for map_name in ("M_WaterPhysicsTest", "M_WaterSmallWavesTest", "M_WaterHighWavesTest"):
    world = unreal.EditorLoadingAndSavingUtils.load_map("/Game/Maps/" + map_name)
    assert world is not None
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    for actor in actors:
        if actor.get_class().get_name() == "BP_LongtailPhysicsPawn_C":
            fields = ["bUseTestInput", "TestThrottle", "TestSteeringDegrees",
                      "TestTrimDegrees", "TestCoastAfterSeconds", "HandlingProfile"]
            print("BOAT_SAVED_INPUT", map_name,
                  unreal.ToolsetLibrary.get_object_properties(actor, fields))
            buoyancy = actor.get_component_by_class(unreal.BuoyancyComponent)
            print("BOAT_SAVED_PONTOONS", map_name,
                  unreal.ToolsetLibrary.get_object_properties(buoyancy, ["BuoyancyData"]))
        if isinstance(actor, unreal.WaterBodyOcean):
            body = actor.get_editor_property("water_body_component")
            for field in ("water_material", "underwater_post_process_material"):
                try:
                    material = body.get_editor_property(field)
                    print("BOAT_WATER_MATERIAL", map_name, field,
                          material.get_path_name() if material else None)
                    if isinstance(material, unreal.MaterialInstance):
                        parent = material.get_editor_property("parent")
                        print("BOAT_WATER_MATERIAL_PARENT", parent.get_path_name())
                except Exception as error:
                    print("BOAT_WATER_MATERIAL_ERROR", field, str(error))

print("BOAT_INSPECTION_COMPLETE_NO_ASSET_WRITES")

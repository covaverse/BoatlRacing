"""Read-only commandlet check: saved maps remain intact and draft tuning persisted."""
import json
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools

handling = unreal.load_asset('/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling')
values = json.loads(unreal.ToolsetLibrary.get_object_properties(
    handling, ['FrontPontoonRadiusCm', 'RearPontoonRadiusCm']))
assert values == {'FrontPontoonRadiusCm': 60, 'RearPontoonRadiusCm': 55}, values
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
fx = BlueprintTools.read_graph_dsl(BlueprintTools.get_graph(bp, 'UpdateFXState_0'))
assert '80.0' in fx and '130.0' in fx, fx
for name in ('M_WaterPhysicsTest', 'M_WaterSmallWavesTest', 'M_WaterHighWavesTest'):
    assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/' + name)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    names = [a.get_class().get_name() for a in actors]
    assert names.count('BP_LongtailPhysicsPawn_C') == 1, (name, names)
    assert names.count('WaterBodyOcean') == names.count('WaterZone') == 1, (name, names)
    assert names.count('BP_FluidSim_01_C') == 1, (name, names)
    assert all(c in names for c in ('DirectionalLight', 'SkyLight', 'SkyAtmosphere',
                                  'ExponentialHeightFog', 'PlayerStart')), (name, names)
    print('BOAT_SAVED_MAP_INTACT', name, len(actors))
print('BOAT_SAVED_DRAFT_PASS')

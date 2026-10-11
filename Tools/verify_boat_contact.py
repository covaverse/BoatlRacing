"""Read-only saved-asset check; run with Unreal's PythonScript commandlet."""
import json
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.material import MaterialTools


def properties(obj, names):
    return json.loads(unreal.ToolsetLibrary.get_object_properties(obj, names))


bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
bow_template = unreal.load_object(None, bp.get_path_name() + '_C:BowSplashFX_GEN_VARIABLE')
assert bow_template.get_asset().get_name() == 'NS_LongtailBowSplash'
fx = BlueprintTools.read_graph_dsl(BlueprintTools.get_graph(bp, 'UpdateFXState_0'))
assert fx.count('SampleWaveSurface') >= 2, fx
assert 'GetBowSplashFX' in fx and 'GetWaterSurfaceZ' in fx
assert 'GetComponentVelocity' in fx
startup = BlueprintTools.read_graph_dsl(BlueprintTools.get_graph(bp, 'ConfigureBoatMass'))
assert 'SetRenderInMainPass' in startup and 'SetHiddenInGame' in startup
mesh = unreal.load_asset('/Game/Boats/ThaiLongtail/Physics/SM_BoatPhysicsHull')
assert properties(mesh, ['bGenerateMeshDistanceField'])['bGenerateMeshDistanceField']
handling = unreal.load_asset('/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling')
assert properties(handling, ['FrontPontoonRadiusCm', 'RearPontoonRadiusCm']) == {
    'FrontPontoonRadiusCm': 60, 'RearPontoonRadiusCm': 55}

folder = '/Game/Water/Materials/BoatContact/'
material = unreal.load_asset(folder + 'M_WaterBoatContact')
assert properties(material, ['BlendMode', 'bUseMaterialAttributes', 'ShadingModel']) == {
    'BlendMode': 'BLEND_Masked', 'bUseMaterialAttributes': True,
    'ShadingModel': 'MSM_SingleLayerWater'}
expressions = MaterialTools.get_expressions(material)
mask = next(e for e in expressions if e.get_editor_property('desc') == 'BoatMeasuredCavity')
assert isinstance(mask, unreal.MaterialExpressionCustom)
mask_inputs = MaterialTools.get_expression_inputs(material, mask)
assert len(mask_inputs) == 6 and all(i.expression for i in mask_inputs)
assert fx.count('SetVectorParameterValue') == 4
profile = unreal.load_asset(folder + 'T_BoatDryProfile')
assert profile and not profile.get_editor_property('srgb')
assert len(unreal.load_asset(folder + 'MPC_BoatContactFrame').get_editor_property('vector_parameters')) == 4
for name, parent in [('MI_WaterBoatOcean', 'MI_WaterBoatBase'),
                     ('MI_WaterBoatBase', 'M_WaterBoatContact')]:
    asset = unreal.load_asset(folder + name)
    assert asset.get_editor_property('parent').get_path_name() == folder + parent + '.' + parent

for name in ('M_WaterPhysicsTest', 'M_WaterSmallWavesTest', 'M_WaterHighWavesTest'):
    assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/' + name)
    actors = unreal.EditorLevelLibrary.get_all_level_actors()
    boats = [a for a in actors if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C']
    assert len(boats) == 1, name
    assert properties(boats[0], ['bUseTestInput', 'TestThrottle']) == {
        'bUseTestInput': False, 'TestThrottle': 0}, name
    bow = boats[0].get_editor_property('BowSplashFX')
    prop = boats[0].get_editor_property('PropSprayFX')
    assert bow.get_asset().get_name() == 'NS_LongtailBowSplash', name
    assert prop.get_asset().get_name() == 'NS_LongtailPropSpray', name
    assert bow.get_asset() != prop.get_asset(), name
    oceans = [a for a in actors if isinstance(a, unreal.WaterBodyOcean)]
    assert len(oceans) == 1, name
    sims = [a for a in actors if a.get_class().get_name() == 'BP_FluidSim_01_C']
    assert len(sims) == 1, name
    sim = properties(sims[0], ['Resolution', 'Simulation World Size',
                              'Frames until Simulation Idle', 'Travel Speed', 'Damping'])
    assert sim['Resolution'] == 1024 and sim['Simulation World Size'] == 4096, (name, sim)
    assert not properties(sims[0], ['Simulate Wave Foam'])['Simulate Wave Foam']
    zones = [a for a in actors if isinstance(a, unreal.WaterZone)]
    assert zones and all(z.get_component_by_class(unreal.WaterMeshComponent).get_editor_property(
        'tessellation_factor') == 9 for z in zones), name
    assert sim['Frames until Simulation Idle'] == 600, (name, sim)
    assert abs(sim['Travel Speed'] - .35) < .001 and abs(sim['Damping'] - .005) < .0001
    body = oceans[0].get_editor_property('water_body_component')
    assert body.get_editor_property('water_material').get_path_name() == (
        folder + 'MI_WaterBoatOcean.MI_WaterBoatOcean'), name
    spline = oceans[0].get_component_by_class(unreal.WaterSplineComponent)
    for i in range(spline.get_number_of_spline_points()):
        assert spline.get_location_at_spline_point(i, unreal.SplineCoordinateSpace.WORLD).x > 50000, name
    print('BOAT_CONTACT_MAP_PASS', name)

# Execute the actual Blueprint at zero hull velocity: wash is driven by the prop.
assert 'GetPropWashFX' in fx and 'GetShaftRPM' in fx and 'GetPropImmersion' in fx
assert 'NS_LongtailPropWash' in startup
assert fx.count('ApplyFluidForceImpulse') == 3 and '0.033333' in fx
assert startup.count('Deactivate') == 2
assert 'NS_LongtailBowSplash' in startup and 'Activate' in startup
assert 'SpraySpeed' in fx and 'SpraySpread' in fx and '-280.0' in fx
defaults = unreal.get_default_object(bp.generated_class())
actor_tools = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
for rpm, immersion, expected in [(0, 1, 0), (700, 0, 0), (700, .01, 0),
                                 (700, .5, 8), (700, 1, 16), (1400, 1, 28),
                                 (2800, 1, 28)]:
    defaults.set_editor_property('ShaftRPM', rpm)
    defaults.set_editor_property('PropImmersion', immersion)
    probe = actor_tools.spawn_actor_from_class(bp.generated_class(), unreal.Vector(0, 0, 1000))
    probe.call_method('UpdateFXState_0')
    wash = probe.get_editor_property('PropWashFX')
    rate, valid = wash.get_variable_float('SpawnRate')
    assert valid and abs(rate - expected) < .001, (rpm, immersion, rate, expected)
    jet = probe.get_editor_property('PropSprayFX')
    jet_rate, jet_valid = jet.get_variable_float('SpawnRate')
    jet_speed, speed_valid = jet.get_variable_float('JetSpeed')
    assert jet_valid and abs(jet_rate - expected * 7) < .001, (rpm, immersion, jet_rate)
    assert speed_valid and abs(jet_speed - (120 + min(abs(rpm) / 1400, 1) * 500)) < .001
    actor_tools.destroy_actor(probe)
print('BOAT_PROP_WASH_BRANCHES_PASS')
print('BOAT_REAR_JET_BRANCHES_PASS')
foam = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionCustom)
            and e.get_editor_property('desc') == 'BoatRippleFoam')
assert 'FluidDelta.z' in foam.get_editor_property('code')
foam_inputs = MaterialTools.get_expression_inputs(material, foam)
assert all(i.expression for i in foam_inputs) and len(foam_inputs) == 3
foam_texture = next(i.expression for i in foam_inputs if i.input_name == 'FoamTexture')
assert isinstance(foam_texture, unreal.MaterialExpressionTextureObjectParameter)
assert foam_texture.get_editor_property('texture').get_name() == 'T_WaterFlow_03_Foam_Tiled'
assert 'Texture2DSample' in foam.get_editor_property('code')
delta = next(i.expression for i in foam_inputs if i.input_name == 'FluidDelta')
assert isinstance(delta, unreal.MaterialExpressionSubtract)
assert len(MaterialTools.get_expression_inputs(material, delta)) == 2
final_attributes = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionMakeMaterialAttributes))
final_inputs = {i.input_name: i.expression for i in MaterialTools.get_expression_inputs(material, final_attributes)}
assert isinstance(final_inputs['BaseColor'], unreal.MaterialExpressionLinearInterpolate)
assert isinstance(final_inputs['Roughness'], unreal.MaterialExpressionLinearInterpolate)
assert final_inputs['OpacityMask'] == mask
assert isinstance(final_inputs['Opacity'], unreal.MaterialExpressionLinearInterpolate)
assert abs(final_inputs['Opacity'].get_editor_property('const_b') - .95) < .001
assert isinstance(final_inputs['WorldPositionOffset'], unreal.MaterialExpressionBreakMaterialAttributes)
print('BOAT_FLUID_FOAM_CONNECTIONS_PASS')
from pathlib import Path
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
before = json.loads((folder/'ripple-released_before.json').read_text())
after = json.loads((folder/'ripple-released_after.json').read_text())
assert not before['source_tick_enabled'] and not after['source_tick_enabled']
assert after['passes'] > before['passes'] and before['hash'] != after['hash']
assert after['outside_source_pixels'] > before['outside_source_pixels'] > 0
assert max(abs(before['min_height']), abs(before['max_height']),
           abs(after['min_height']), abs(after['max_height'])) < 40
print('BOAT_RIPPLE_PROPAGATION_EVIDENCE_PASS')
detail = json.loads((folder / 'ripple-detail1024.json').read_text())
assert detail['pixels'] == 1024 ** 2 and detail['outside_source_pixels'] > 0
assert max(abs(detail['min_height']), abs(detail['max_height'])) < 40
textured = json.loads((folder / 'ripple-textured-wake-steady.json').read_text())
assert textured['pixels'] == 1024 ** 2 and textured['outside_source_pixels'] > 0
assert max(abs(textured['min_height']), abs(textured['max_height'])) < 40
print('BOAT_TEXTURED_WAKE_EVIDENCE_PASS')
branches = json.loads((folder / 'bow-branches.json').read_text())
assert len(branches) == 8
assert branches[0]['rate_per_side'] == branches[1]['rate_per_side'] == branches[-1]['rate_per_side'] == 0
assert branches[2]['rate_per_side'] == 0
assert 0 < branches[3]['rate_per_side'] < branches[4]['rate_per_side'] < branches[5]['rate_per_side']
assert branches[5]['rate_per_side'] == branches[6]['rate_per_side']
print('BOAT_BOW_AND_DETAIL_EVIDENCE_PASS')
print('BOAT_CONTACT_SAVED_ASSETS_PASS')

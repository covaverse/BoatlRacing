"""Editor Python: feed a hull-shaped pressure source into the native ripple solver."""
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

root = Path(unreal.Paths.project_dir())
assets = unreal.EditorAssetLibrary
path = '/Game/Water/Materials/BoatContact/M_BoatHullFluidForce'
if not assets.does_asset_exist(path):
    assets.duplicate_asset('/Water/FluidSimulation/Materials/Forces/M_Fluid_Sim_Force_Impulse', path)
material = unreal.load_asset(path)
expressions = MaterialTools.get_expressions(material)
force = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionScalarParameter)
             and str(e.get_editor_property('parameter_name')) == 'F')
uv = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionTextureCoordinate))
shape = next((e for e in expressions if e.get_editor_property('desc') == 'MeasuredHullPressure'), None)
if not shape:
    shape = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionCustom, 800, 0)
    shape.set_editor_property('desc', 'MeasuredHullPressure')
    inputs = []
    for name in ('UV', 'Force', 'Origin', 'AxisX', 'AxisY', 'AxisZ', 'Profile'):
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    shape.set_editor_property('inputs', inputs)
    shape.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT3)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(uv, '', shape, 'UV')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(force, '', shape, 'Force')
    collection = unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
    for i, name in enumerate(('Origin', 'AxisX', 'AxisY', 'AxisZ')):
        node = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionCollectionParameter, 200, 200 + i * 150)
        node.set_editor_property('collection', collection)
        node.set_editor_property('parameter_name', name)
        assert unreal.MaterialEditingLibrary.connect_material_expressions(node, '', shape, name)
    profile = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureObjectParameter, 200, 850)
    profile.set_editor_property('parameter_name', 'Hull Profile')
    profile.set_editor_property('texture', unreal.load_asset('/Game/Water/Materials/BoatContact/T_BoatDryProfile'))
    profile.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(profile, '', shape, 'Profile')
shape.set_editor_property('code', '''
// ponytail: prescribed pressure on a height field; this is not a solid-boundary CFD solver.
// Native canvas stamp has radius 360 cm. AxisZ.a carries sampled water height.
float3 d = float3((UV - 0.5) * 720.0, AxisZ.a - Origin.z);
float3 p = float3(dot(d, AxisX.rgb), dot(d, AxisY.rgb), dot(d, AxisZ.rgb));
float u = saturate((p.x + 230.5) / 532.0);
float2 limits = Texture2DSampleLevel(Profile, ProfileSampler, float2(u, 0.0625), 0).gb * 64.0;
float v = (saturate((p.z - limits.x) / max(limits.y - limits.x, 0.01)) * 7.0 + 0.5) / 8.0;
float width = Texture2DSampleLevel(Profile, ProfileSampler, float2(u, v), 0).r * 64.0 + 2.0;
float edge = abs(p.y) - width;
float core = 1.0 - smoothstep(-8.0, 8.0, edge);
float bank = smoothstep(-4.0, 8.0, edge) * (1.0 - smoothstep(8.0, 32.0, edge));
float lengthMask = smoothstep(-245.0, -225.0, p.x) * (1.0 - smoothstep(285.0, 315.0, p.x));
// Collision hull keel is at local Z=-25 cm; the liner floor is above the wetted hull.
float wet = smoothstep(-25.0, -15.0, p.z);
return float3(Force * 3.0 * lengthMask * wet * (core - bank * width / 22.0), 0.0, 0.0);
''')
assert unreal.MaterialEditingLibrary.connect_material_property(shape, '', unreal.MaterialProperty.MP_EMISSIVE_COLOR)
unreal.MaterialEditingLibrary.recompile_material(material)
assert assets.save_loaded_asset(material, only_if_is_dirty=False)

bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
graph = BlueprintTools.get_graph(bp, 'UpdateFXState_0')
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-foam-blend/fx-before-hull-pressure.dsl'
if not backup.exists():
    backup.write_text(BlueprintTools.read_graph_dsl(graph), encoding='utf-8')
BlueprintTools.write_graph_dsl(graph, (root / 'Tools/BlueprintDSL/UpdateFXState.dsl').read_text())
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
readback = BlueprintTools.read_graph_dsl(graph)
assert readback.count("ApplyFluidForceImpulse") == 2 and "M_BoatHullFluidForce" in readback
assert "SetFollowPlayer" in readback and "SetActorLocation" in readback
assert "GetForceParentandMIDMap" in readback
assert assets.save_loaded_asset(bp, only_if_is_dirty=False)
print('BOAT_HULL_PRESSURE_AND_GRID_FOLLOW_SAVED')

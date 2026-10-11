"""Editor Python: a measured cavity mask for the single boat in each test map."""
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

folder = '/Game/Water/Materials/BoatContact'
assets = unreal.EditorAssetLibrary
mpc_path = folder + '/MPC_BoatContactFrame'
mpc = unreal.load_asset(mpc_path)
if not mpc:
    mpc = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
        'MPC_BoatContactFrame', folder, unreal.MaterialParameterCollection,
        unreal.MaterialParameterCollectionFactoryNew())
    values = []
    for name, value in [('Origin', unreal.LinearColor(0, 0, 0, -100000)),
                        ('AxisX', unreal.LinearColor(1, 0, 0, 0)),
                        ('AxisY', unreal.LinearColor(0, 1, 0, 0)),
                        ('AxisZ', unreal.LinearColor(0, 0, 1, 0))]:
        parameter = unreal.CollectionVectorParameter()
        parameter.set_editor_property('parameter_name', name)
        parameter.set_editor_property('default_value', value)
        values.append(parameter)
    mpc.set_editor_property('vector_parameters', values)
    mpc.modify()
    assert assets.save_asset(mpc_path, only_if_is_dirty=False)
texture_path = folder + '/T_BoatDryProfile'
if not assets.does_asset_exist(texture_path):
    task = unreal.AssetImportTask()
    task.set_editor_property('filename', str(Path(unreal.Paths.project_dir()) / 'SourceAssets/Physics/T_BoatDryProfile.tga'))
    task.set_editor_property('destination_path', folder)
    task.set_editor_property('destination_name', 'T_BoatDryProfile')
    task.set_editor_property('automated', True)
    task.set_editor_property('save', True)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = unreal.load_asset(texture_path)
assert texture
texture.set_editor_property('srgb', False)
texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
texture.modify()
assert assets.save_asset(texture_path, only_if_is_dirty=False)
material = unreal.load_asset(folder + '/M_WaterBoatContact')
expressions = MaterialTools.get_expressions(material)
mask = next((e for e in expressions if e.get_editor_property('desc') == 'BoatMeasuredCavity'), None)
if not mask:
    mask = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionCustom, 2750, 1700)
    mask.set_editor_property('desc', 'BoatMeasuredCavity')
    inputs = []
    for name in ('World', 'Origin', 'AxisX', 'AxisY', 'AxisZ', 'Profile'):
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
    mask.set_editor_property('inputs', inputs)
    mask.set_editor_property('output_type', unreal.CustomMaterialOutputType.CMOT_FLOAT1)
    world = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionWorldPosition))
    assert unreal.MaterialEditingLibrary.connect_material_expressions(world, '', mask, 'World')
    for i, name in enumerate(('Origin', 'AxisX', 'AxisY', 'AxisZ')):
        parameter = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionCollectionParameter, 2200, 1750 + i * 150)
        parameter.set_editor_property('collection', mpc)
        parameter.set_editor_property('parameter_name', name)
        assert unreal.MaterialEditingLibrary.connect_material_expressions(parameter, '', mask, name)
    profile = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionTextureObjectParameter, 2200, 2350)
    profile.set_editor_property('parameter_name', 'Boat Dry Profile')
    profile.set_editor_property('texture', texture)
    profile.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(profile, '', mask, 'Profile')
mask.set_editor_property('code', '''
// ponytail: one unit-scale boat per world; add ownership slots for multiplayer.
// The existing actor FX tick publishes this frame; use a post-physics publisher if lag becomes visible.
float3 d = World - Origin.rgb;
float3 p = float3(dot(d, AxisX.rgb), dot(d, AxisY.rgb), dot(d, AxisZ.rgb));
float u = saturate((p.x + 230.5) / 532.0);
float2 limits = Texture2DSampleLevel(Profile, ProfileSampler, float2(u, 0.0625), 0).gb * 64.0;
float v = (saturate((p.z - limits.x) / max(limits.y - limits.x, 0.01)) * 7.0 + 0.5) / 8.0;
float width = Texture2DSampleLevel(Profile, ProfileSampler, float2(u, v), 0).r * 64.0;
float inside = step(-230.0, p.x) * step(p.x, 301.0) * step(limits.x, p.z) * step(p.z, limits.y) * (1.0 - step(width - 0.2, abs(p.y)));
// ponytail: fixed one-boat test worlds; clear Origin on EndPlay before supporting actor deletion.
float active = step(0.0, Origin.a);
return 1.0 - inside * active;
''')
final = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionMakeMaterialAttributes))
assert unreal.MaterialEditingLibrary.connect_material_expressions(mask, '', final, 'OpacityMask')
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)
assert assets.save_loaded_asset(material, only_if_is_dirty=False)
bp_path = '/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn'
bp = unreal.load_asset(bp_path)
graph = BlueprintTools.get_graph(bp, 'UpdateFXState_0')
BlueprintTools.write_graph_dsl(graph, (Path(unreal.Paths.project_dir()) / 'Tools/BlueprintDSL/UpdateFXState.dsl').read_text())
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
assert BlueprintTools.read_graph_dsl(graph).count('SetVectorParameterValue') == 4
assert assets.save_asset(bp_path, only_if_is_dirty=False)
print('BOAT_MEASURED_PROFILE_MASK_SAVED')

"""Editor Python: attach foam to the exterior hull and transport the existing trail."""
import datetime
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

root = Path(unreal.Paths.project_dir())
folder = '/Game/Water/Materials/BoatContact'
assets = unreal.EditorAssetLibrary
material = unreal.load_asset(folder + '/M_BoatFoamComposite')
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before changing assets'
backup = root / 'Saved/Backups' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-hull-contact')
backup.mkdir(parents=True)
for asset in (material, bp):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False)
    package = asset.get_path_name().split('.')[0].replace('/Game/', 'Content/') + '.uasset'
    shutil.copy2(root / package, backup / Path(package).name)

task = unreal.AssetImportTask()
task.filename = str(root / 'SourceAssets/Physics/T_BoatOuterProfile.tga')
task.destination_path = folder
task.destination_name = 'T_BoatOuterProfile'
task.automated = True
task.replace_existing = True
task.save = False
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
texture = unreal.load_asset(folder + '/T_BoatOuterProfile')
assert texture
texture.set_editor_property('srgb', False)
texture.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_VECTOR_DISPLACEMENTMAP)
texture.set_editor_property('mip_gen_settings', unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
texture.set_editor_property('address_x', unreal.TextureAddress.TA_CLAMP)
texture.set_editor_property('address_y', unreal.TextureAddress.TA_CLAMP)
texture.modify()

expressions = MaterialTools.get_expressions(material)
custom = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionCustom))
old_code = custom.get_editor_property('code')
(backup / 'foam-before.hlsl').write_text(old_code)
profile = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionTextureObjectParameter)
               and str(e.get_editor_property('parameter_name')) == 'HullProfile')
profile.set_editor_property('texture', texture)
# Flow is world-space cm/s, so turns do not rotate the wind with the hull.
flow = next((e for e in expressions if isinstance(e, unreal.MaterialExpressionVectorParameter)
             and str(e.get_editor_property('parameter_name')) == 'SurfaceFlowCmPerSec'), None)
if not flow:
    flow = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -700, 1500)
    flow.set_editor_property('parameter_name', 'SurfaceFlowCmPerSec')
    flow.set_editor_property('default_value', unreal.LinearColor(12, 0, 0, 0))
inputs = list(custom.get_editor_property('inputs'))
if not any(str(i.get_editor_property('input_name')) == 'SurfaceFlow' for i in inputs):
    item = unreal.CustomInput()
    item.set_editor_property('input_name', 'SurfaceFlow')
    inputs.append(item)
    custom.set_editor_property('inputs', inputs)
assert unreal.MaterialEditingLibrary.connect_material_expressions(flow, '', custom, 'SurfaceFlow')
code = '''// ponytail: one symmetric boat in the existing foam RT; use per-boat fields for multiplayer.
float2 uv = UV;
float2 world = FoamOrigin + uv * FoamSize;
float3 dd = float3(world - Origin.rg, AxisZ.a - Origin.b);
float3 p = float3(dot(dd, AxisX.rgb), dot(dd, AxisY.rgb), dot(dd, AxisZ.rgb));
// Measured OUTER shell, 1 cm texels: X [-320,320], Z [-16,112].
float2 profileUV = (p.xz + float2(320.0, 16.0)) / float2(640.0, 128.0);
float2 profile = Texture2DSampleLevel(Profile, ProfileSampler, saturate(profileUV), 0).rg;
float valid = profile.g * step(0.0, profileUV.x) * step(profileUV.x, 1.0)
                         * step(0.0, profileUV.y) * step(profileUV.y, 1.0);
float width = profile.r * 64.0;
float rim = (1.0 - smoothstep(0.0, max(Range, 1.0), abs(abs(p.y) - width))) * valid;
float dt = clamp(AxisY.a, 0.0, 0.1);
float moving = smoothstep(0.05, 0.5, AxisX.a);
// Birth only at the real waterline. History supplies the curved wake, including turns.
float added = rim * rim * Birth * moving * dt;
float downstream = max(p.x + 240.0, 0.0);
float spread = lerp(12.0, 42.0, 1.0 - exp(-downstream / 420.0));
float wakeArea = smoothstep(-300.0, -180.0, p.x) * exp(-downstream / 1400.0)
               * (1.0 - smoothstep(180.0, 420.0, abs(p.y)));
float2 drift = SurfaceFlow.rg + AxisY.rg * tanh(p.y / 18.0) * spread * wakeArea * moving;
// World-anchored eddies advect history in seconds, without redrawing straight V arms.
float2 n = float2(Texture2DSample(Noise, NoiseSampler, world / 600.0 + Time * 0.013).r,
                  Texture2DSample(Noise, NoiseSampler, world / 600.0 + 0.41 - Time * 0.009).r);
drift += (n - 0.5) * NoiseAmount * FoamSize;
float2 prevUV = uv + Shift - drift * dt / max(FoamSize, 1.0);
'''
tail = old_code[old_code.index('// 9-tap blur'):]
custom.set_editor_property('code', code + tail)
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)

# Only rewire the four published frame queries; physics velocity/water sampling stay intact.
graph = BlueprintTools.get_graph(bp, 'UpdateFXState_0')
nodes = BlueprintTools.find_nodes(graph, '')
infos = BlueprintTools.get_node_infos(nodes)
visual_info = next((i for i in infos if i.type_id == 'Variables|Default|GetBoatVisual'), None)
if visual_info is None:
    visual = BlueprintTools.create_node(graph, 'Variables|Default|GetBoatVisual', unreal.IntPoint(-600, -500))
    visual_info = BlueprintTools.get_node_infos([visual])[0]
source = visual_info.output_pins[0].pin_id
for info in infos:
    if info.type_id in ('Transformation|GetWorldLocation', 'Transformation|GetForwardVector',
                         'Transformation|GetRightVector', 'Transformation|GetUpVector'):
        pin = next(p for p in info.input_pins if p.name == 'self')
        BlueprintTools.connect_pins(source, pin.pin_id)
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
for asset in (texture, material, bp):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False)
print('HULL_CONTACT_FOAM_SAVED', str(backup))

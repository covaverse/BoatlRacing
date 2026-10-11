"""Editor Python: replace coarse procedural foam grain with the installed water foam texture."""
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools

path = '/Game/Water/Materials/BoatContact/M_WaterBoatContact'
material = unreal.load_asset(path)
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-water-contact/M_WaterBoatContact-before-textured-foam.uasset'
if not backup.exists():
    shutil.copy2(Path(unreal.Paths.project_content_dir()) / 'Water/Materials/BoatContact/M_WaterBoatContact.uasset', backup)
expressions = MaterialTools.get_expressions(material)
foam = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionCustom)
            and e.get_editor_property('desc') == 'BoatRippleFoam')
texture = next((e for e in expressions if isinstance(e, unreal.MaterialExpressionTextureObjectParameter)
                and str(e.get_editor_property('parameter_name')) == 'Boat Foam Texture'), None)
if not texture:
    texture = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionTextureObjectParameter, 2150, 1450)
    texture.set_editor_property('parameter_name', 'Boat Foam Texture')
    texture.set_editor_property('texture', unreal.load_asset('/Water/Textures/Foam/T_WaterFlow_03_Foam_Tiled'))
inputs = list(foam.get_editor_property('inputs'))
if not any(str(i.get_editor_property('input_name')) == 'FoamTexture' for i in inputs):
    item = unreal.CustomInput()
    item.set_editor_property('input_name', 'FoamTexture')
    inputs.append(item)
    foam.set_editor_property('inputs', inputs)
assert unreal.MaterialEditingLibrary.connect_material_expressions(texture, '', foam, 'FoamTexture')
foam.set_editor_property('code', '''
// ponytail: texture follows fluid amplitude; use transported foam RT for independent persistence.
float disturbance = smoothstep(0.12, 1.8, abs(FluidDelta.z));
float2 uv = World.xy / 160.0 + float2(View.GameTime * 0.015, View.GameTime * 0.006);
float large = Texture2DSample(FoamTexture, FoamTextureSampler, uv).r;
float fine = Texture2DSample(FoamTexture, FoamTextureSampler, uv * 2.31 + float2(0.37, 0.13)).r;
return disturbance * smoothstep(0.22, 0.82, large) * (0.55 + 0.45 * fine);
''')
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
print('BOAT_TEXTURED_FLUID_FOAM_SAVED')

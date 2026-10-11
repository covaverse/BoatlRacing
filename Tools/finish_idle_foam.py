"""Editor Python before PIE: initialize stopped spray and make foam a diffuse surface."""
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools
from editor_toolset.toolsets.material import MaterialTools

root = Path(unreal.Paths.project_dir())
bp_path = '/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn'
bp = unreal.load_asset(bp_path)
for name, file in [('ConfigureBoatMass', 'WaterBridge/ConfigureBoatMass.dsl'),
                   ('UpdateFXState_0', 'UpdateFXState.dsl')]:
    graph = BlueprintTools.get_graph(bp, name)
    BlueprintTools.write_graph_dsl(graph, (root / ('Tools/BlueprintDSL/' + file)).read_text())
    assert BlueprintTools.read_graph_dsl(graph).count('SetVisibility') == 3
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
assert unreal.EditorAssetLibrary.save_asset(bp_path, only_if_is_dirty=False)

path = '/Game/Water/Materials/BoatContact/M_WaterBoatContact'
material = unreal.load_asset(path)
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-water-contact/water-before-diffuse-foam.uasset'
if not backup.exists():
    shutil.copy2(Path(unreal.Paths.project_content_dir()) / (path[6:] + '.uasset'), backup)
expressions = MaterialTools.get_expressions(material)
foam = next(e for e in expressions if e.get_editor_property('desc') == 'BoatRippleFoam')
final = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionMakeMaterialAttributes))
original = next(i.expression for i in MaterialTools.get_expression_inputs(material, final)
                if i.input_name == 'Opacity')
assert isinstance(original, unreal.MaterialExpressionBreakMaterialAttributes) or original.get_editor_property('desc') == 'BoatFoamOpacity'
if original.get_editor_property('desc') != 'BoatFoamOpacity':
    opacity = unreal.MaterialEditingLibrary.create_material_expression(
        material, unreal.MaterialExpressionLinearInterpolate, 2700, 1350)
    opacity.set_editor_property('desc', 'BoatFoamOpacity')
    opacity.set_editor_property('const_b', .95)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(original, 'Opacity', opacity, 'A')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(foam, '', opacity, 'Alpha')
    assert unreal.MaterialEditingLibrary.connect_material_expressions(opacity, '', final, 'Opacity')
foam.set_editor_property('code', '''
// ponytail: amplitude-driven foam; transport a foam RT when independent persistence is required.
float disturbed = smoothstep(0.08, 1.2, abs(FluidDelta.z));
float2 uv = World.xy / 160.0 + float2(View.GameTime * 0.015, View.GameTime * 0.006);
float2 warp = float2(Texture2DSample(FoamTexture, FoamTextureSampler, uv * 0.43).r,
                    Texture2DSample(FoamTexture, FoamTextureSampler, uv * 0.43 + 0.37).r);
uv += (warp - 0.5) * 0.18;
float large = Texture2DSample(FoamTexture, FoamTextureSampler, uv).r;
float fine = Texture2DSample(FoamTexture, FoamTextureSampler, uv * 2.31 + float2(0.37, 0.13)).r;
return saturate(disturbed * smoothstep(0.15, 0.65, large) * (0.8 + 0.2 * fine) * 1.35);
''')
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
print('BOAT_IDLE_INITIALIZATION_AND_DIFFUSE_FOAM_SAVED')

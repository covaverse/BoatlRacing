"""Editor Python: shade foam from the existing fluid displacement, preserving the hull mask."""
import json
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools

path = '/Game/Water/Materials/BoatContact/M_WaterBoatContact'
material = unreal.load_asset(path)
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-water-contact/M_WaterBoatContact-before-foam.uasset'
if not backup.exists():
    shutil.copy2(Path(unreal.Paths.project_content_dir()) / 'Water/Materials/BoatContact/M_WaterBoatContact.uasset', backup)
expressions = MaterialTools.get_expressions(material)
assert not any(e.get_editor_property('desc') == 'BoatRippleFoam' for e in expressions), 'Foam already installed'
fluid = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionMaterialFunctionCall)
             and e.get_editor_property('material_function').get_name() == 'SampleFluidSimulation')
original = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionBreakMaterialAttributes))
final = next(e for e in expressions if isinstance(e, unreal.MaterialExpressionMakeMaterialAttributes))
source = next(i for i in MaterialTools.get_expression_inputs(material, fluid) if i.input_name == 'Attributes')
assert source.expression


def node(cls, x, y):
    return unreal.MaterialEditingLibrary.create_material_expression(material, cls, x, y)


def connect(a, output, b, pin):
    assert unreal.MaterialEditingLibrary.connect_material_expressions(a, output, b, pin), (output, pin)


before = node(unreal.MaterialExpressionBreakMaterialAttributes, 1900, 900)
after = node(unreal.MaterialExpressionBreakMaterialAttributes, 1900, 1100)
connect(source.expression, source.output_name, before, 'Attr')
connect(fluid, 'Attributes', after, 'Attr')
delta = node(unreal.MaterialExpressionSubtract, 2150, 950)
connect(after, 'WorldPositionOffset', delta, 'A')
connect(before, 'WorldPositionOffset', delta, 'B')
world = node(unreal.MaterialExpressionWorldPosition, 2150, 1250)
foam = node(unreal.MaterialExpressionCustom, 2400, 950)
foam.set_editor_property('desc', 'BoatRippleFoam')
custom_inputs = []
for name in ('FluidDelta', 'World'):
    item = unreal.CustomInput()
    item.set_editor_property('input_name', name)
    custom_inputs.append(item)
foam.set_editor_property('inputs', custom_inputs)
assert unreal.ToolsetLibrary.set_object_properties(foam, json.dumps({
    'OutputType': 'CMOT_Float1',
    'Code': '''
// ponytail: foam follows wave amplitude; transport a foam RT if lingering bubbles are needed.
float disturbed = smoothstep(1.0, 5.0, abs(FluidDelta.z));
float2 p = World.xy + float2(View.GameTime * 8.0, View.GameTime * 3.0);
float grain = frac(sin(dot(floor(p / 12.0), float2(127.1, 311.7))) * 43758.5453);
float bubble = 1.0 - smoothstep(0.2, 0.49, length(frac(p / 5.0) - 0.5));
return disturbed * smoothstep(0.12, 0.8, grain) * (0.65 + 0.35 * bubble);
'''}))
connect(delta, '', foam, 'FluidDelta')
connect(world, '', foam, 'World')
white = node(unreal.MaterialExpressionConstant3Vector, 2450, 1200)
white.set_editor_property('constant', unreal.LinearColor(.88, .94, .95, 1))
color = node(unreal.MaterialExpressionLinearInterpolate, 2700, 850)
connect(original, 'BaseColor', color, 'A')
connect(white, '', color, 'B')
connect(foam, '', color, 'Alpha')
connect(color, '', final, 'BaseColor')
rough = node(unreal.MaterialExpressionLinearInterpolate, 2700, 1100)
rough.set_editor_property('const_b', .65)
connect(original, 'Roughness', rough, 'A')
connect(foam, '', rough, 'Alpha')
connect(rough, '', final, 'Roughness')
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
print('BOAT_RIPPLE_FOAM_GRAPH_SAVED')

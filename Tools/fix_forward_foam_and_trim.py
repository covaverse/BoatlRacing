"""Editor Python: suppress boat-induced forward foam and give the visual hull stern draft."""
import datetime
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

root = Path(unreal.Paths.project_dir())
assets = unreal.EditorAssetLibrary
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
material = unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE first'
backup = root / 'Saved/Backups' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-forward-foam-trim')
backup.mkdir(parents=True)
for asset in (bp, material):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False)
    path = asset.get_path_name().split('.')[0].replace('/Game/', 'Content/') + '.uasset'
    shutil.copy2(root / path, backup / Path(path).name)

graph = BlueprintTools.get_graph(bp, 'ApplyVisualTrim')
old = BlueprintTools.read_graph_dsl(graph)
(backup / 'ApplyVisualTrim.dsl').write_text(old)
# Bow is -X. Negative UE pitch lowers +X (stern), including at idle.
needle = '(- (* (select (> (Variables|Default|GetThrottle)'
assert needle in old or '(-3.0' in old, 'Unexpected trim graph; do not replace user edits'
if needle in old and '(+ -3.0 ' not in old:
    start = old.index(needle)
    depth = 0
    for end in range(start, len(old)):
        depth += (old[end] == '(') - (old[end] == ')')
        if depth == 0:
            break
    target = old[start:end + 1]
    updated = old[:start] + '(+ -3.0 ' + target + ')' + old[end + 1:]
    BlueprintTools.write_graph_dsl(graph, updated)
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)

expressions = MaterialTools.get_expressions(material)
custom = next(e for e in expressions if e.get_editor_property('desc') == 'BoatRippleFoam')
old_code = custom.get_editor_property('code')
(backup / 'ripple-foam.hlsl').write_text(old_code)
inputs = list(custom.get_editor_property('inputs'))
collection = unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
for name in ('Origin', 'AxisX'):
    if not any(str(i.get_editor_property('input_name')) == name for i in inputs):
        item = unreal.CustomInput()
        item.set_editor_property('input_name', name)
        inputs.append(item)
        custom.set_editor_property('inputs', inputs)
        param = unreal.MaterialEditingLibrary.create_material_expression(material, unreal.MaterialExpressionCollectionParameter, 1800, 2700 if name == 'Origin' else 2850)
        param.set_editor_property('collection', collection)
        param.set_editor_property('parameter_name', name)
        assert unreal.MaterialEditingLibrary.connect_material_expressions(param, '', custom, name)
# Replacing the input array copies structs; reconnect after the final array assignment.
for name in ('Origin', 'AxisX'):
    param = next(e for e in MaterialTools.get_expressions(material)
                 if isinstance(e, unreal.MaterialExpressionCollectionParameter)
                 and str(e.get_editor_property('parameter_name')) == name)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(param, '', custom, name)
if 'forwardFoamGate' not in old_code:
    assert 'return max(live, trail);' in old_code
    custom.set_editor_property('code', old_code.replace('return max(live, trail);', '''
// Fluid waves propagate both ways; boat foam belongs at the hull and behind it.
float hullX = dot(World - Origin.rgb, AxisX.rgb);
float forwardFoamGate = smoothstep(-330.0, -270.0, hullX);
return max(live, trail) * forwardFoamGate;
'''))
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)
for asset in (bp, material):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False)
print('FORWARD_FOAM_AND_VISUAL_STERN_DRAFT_SAVED', str(backup))

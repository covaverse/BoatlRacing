"""Birth foam from the running fluid field instead of painting a hull rim."""
import datetime, shutil, re
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

assets = unreal.EditorAssetLibrary
root = Path(unreal.Paths.project_dir())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE before asset changes'
folder = '/Game/Water/Materials/BoatContact/'
water = unreal.load_asset(folder + 'M_WaterBoatContact')
foam = unreal.load_asset(folder + 'M_BoatFoamComposite')
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
backup = root / 'Saved/Backups' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-wave-driven-foam')
backup.mkdir(parents=True)
for asset in (water, foam, bp):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False)
    file = asset.get_path_name().split('.')[0].replace('/Game/', 'Content/') + '.uasset'
    shutil.copy2(root / file, backup / Path(file).name)

ex = MaterialTools.get_expressions(foam)
c = next(e for e in ex if isinstance(e, unreal.MaterialExpressionCustom))
code = c.get_editor_property('code')
(backup / 'birth-before.hlsl').write_text(code)
if 'waveDrivenBirth' not in code:
    needle = 'float added = rim * rim * Birth * moving * dt;'
    replacement = '''// waveDrivenBirth: sample the real simulation in its own world frame.
float2 simUV = (world - SimOrigin.rg) / max(SimSize, 1.0) + 0.5;
float2 simEdge = abs(simUV - 0.5);
float simWindow = 1.0 - smoothstep(0.46, 0.495, max(simEdge.x, simEdge.y));
float3 wave = Texture2DSampleLevel(WaveNormals, WaveNormalsSampler, saturate(simUV), 0).rgb;
// Native NormalRT stores signed normal XY and signed height in B.
float steepness = length(wave.rg);
float threshold = clamp(BreakingThreshold, 0.01, 0.8);
float breaking = smoothstep(threshold * 0.5, threshold, steepness)
               * smoothstep(0.05, 0.5, max(wave.b, 0.0)) * simWindow;
// Let the bow disturb the surface first; foam begins farther down the hull.
float wakeRegion = smoothstep(-200.0, -110.0, p.x)
                 * (1.0 - smoothstep(1000.0, 1800.0, p.x))
                 * (1.0 - smoothstep(420.0, 650.0, abs(p.y)));
float outsideHull = lerp(1.0, smoothstep(-3.0, 5.0, abs(p.y) - width), valid);
float added = breaking * outsideHull * wakeRegion * Birth * moving * dt;'''
    assert needle in code
    c.set_editor_property('code', code.replace(needle, replacement))
    inputs = list(c.get_editor_property('inputs'))
    for name in ('WaveNormals', 'SimOrigin', 'SimSize', 'BreakingThreshold'):
        i = unreal.CustomInput()
        i.set_editor_property('input_name', name)
        inputs.append(i)
    c.set_editor_property('inputs', inputs)
    mpc = unreal.load_asset('/Water/Materials/MPC/MPC_Water')
    for index, name in enumerate(('WaveNormals', 'SimOrigin', 'SimSize', 'BreakingThreshold')):
        if name == 'WaveNormals':
            e = unreal.MaterialEditingLibrary.create_material_expression(foam, unreal.MaterialExpressionTextureObjectParameter, 0, 2400)
            e.set_editor_property('parameter_name', 'WaveNormalHeight')
            e.set_editor_property('texture', unreal.load_asset('/Engine/EngineResources/Black'))
            e.set_editor_property('sampler_type', unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
        elif name == 'BreakingThreshold':
            e = unreal.MaterialEditingLibrary.create_material_expression(foam, unreal.MaterialExpressionScalarParameter, 0, 2600)
            e.set_editor_property('parameter_name', 'FoamBreakingThreshold')
            e.set_editor_property('default_value', .12)
            e.set_editor_property('group', 'Foam Birth')
            e.set_editor_property('slider_min', .01)
            e.set_editor_property('slider_max', .8)
            e.set_editor_property('desc', 'ความชันคลื่นที่เริ่มเกิดฟอง: ลด = ขึ้นง่าย / เพิ่ม = ต้องคลื่นแรง; เริ่ม 0.12. Breaking wave tilt threshold.')
        else:
            e = unreal.MaterialEditingLibrary.create_material_expression(foam, unreal.MaterialExpressionCollectionParameter, 0, 2800 + index * 140)
            e.set_editor_property('collection', mpc)
            e.set_editor_property('parameter_name', 'SimLocation' if name == 'SimOrigin' else 'FluidSimSize')
        assert unreal.MaterialEditingLibrary.connect_material_expressions(e, '', c, name)

wc = next(e for e in MaterialTools.get_expressions(water) if str(e.get_editor_property('desc')) == 'BoatRippleFoam')
wcode = wc.get_editor_property('code')
old = 'return max(max(live, trail), contactFoam * forwardFoamGate * clamp(WakeFoamGain,0.0,1.0));'
assert old in wcode or 'return max(live, trail);' in wcode
wc.set_editor_property('code', wcode.replace(old, 'return max(live, trail);'))

graph = BlueprintTools.get_graph(bp, 'UpdateFoamCapture')
dsl = BlueprintTools.read_graph_dsl(graph)
(backup / 'UpdateFoamCapture.dsl').write_text(dsl)
if '"WaveNormalHeight"' not in dsl:
    needle = '  (Rendering|DrawMaterialToRenderTarget _foamrt (Variables|Default|GetFoamCompositeMID))\n  (Variables|Default|SetPrevCaptureLoc (Math|Vector|MakeVector _returnvalue_12 _returnvalue_14)))'
    insert = '''  (bind _fluid_actor (Actor|GetActorOfClass "/Water/FluidSimulation/Blueprints/BP_FluidSim_01.BP_FluidSim_01_C"))
  (Utilities|IsValid _fluid_actor
    (:"Is Valid"
      (Rendering|Material|SetTextureParameterValue (Variables|Default|GetFoamCompositeMID) "WaveNormalHeight" (Class|BPFluidSim01|GetNormalRT _fluid_actor))
      (Rendering|DrawMaterialToRenderTarget _foamrt (Variables|Default|GetFoamCompositeMID))
      (Variables|Default|SetPrevCaptureLoc (Math|Vector|MakeVector _returnvalue_12 _returnvalue_14)))
    (:"Is Not Valid"
      (Rendering|DrawMaterialToRenderTarget _foamrt (Variables|Default|GetFoamCompositeMID))
      (Variables|Default|SetPrevCaptureLoc (Math|Vector|MakeVector _returnvalue_12 _returnvalue_14)))))
'''
    assert needle in dsl
    updated = dsl.replace(needle, insert)
    # The reader emits numeric binds; the current writer requires literal arguments.
    for name, value in re.findall(r'\(bind (\w+) (-?[0-9.]+)\)', updated):
        updated = re.sub(r'\s*\(bind ' + re.escape(name) + r' ' + re.escape(value) + r'\)', '', updated)
        updated = re.sub(r'(?<![\w])' + re.escape(name) + r'(?![\w])', value, updated)
    (backup / 'attempted.dsl').write_text(updated)
    BlueprintTools.write_graph_dsl(graph, updated)
    BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
    actual = BlueprintTools.read_graph_dsl(graph)
    assert 'WaveNormalHeight' in actual and 'GetNormalRT' in actual, actual
    assert actual.count('DrawMaterialToRenderTarget') == 3, actual

MaterialTools.recompile(foam)
MaterialTools.recompile(water)
for asset in (foam, water, bp):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False)
print('WAVE_DRIVEN_FOAM_SAVED', str(backup))

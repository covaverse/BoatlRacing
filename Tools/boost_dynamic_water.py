"""Editor Python: stronger dynamic water and editable runtime material instance."""
import datetime,re,shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools
root=Path(unreal.Paths.project_dir());assets=unreal.EditorAssetLibrary
assert not unreal.EditorLevelLibrary.get_game_world(),'Stop PIE before editing'
base='/Game/Water/Materials/BoatContact/M_BoatHullFluidForce'
instance='/Game/Water/Materials/BoatContact/MI_BoatHullFluidForce'
m=unreal.load_asset(base);bp=unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-surging-water')
backup.mkdir(parents=True)
for asset in (m,bp):
 assert assets.save_loaded_asset(asset,only_if_is_dirty=False)
 file=asset.get_path_name().split('.')[0].replace('/Game/','Content/')+'.uasset'
 shutil.copy2(root/file,backup/Path(file).name)
ex=MaterialTools.get_expressions(m)
shape=next(e for e in ex if e.get_editor_property('desc')=='MeasuredHullPressure')
code=shape.get_editor_property('code');(backup/'pressure-before.hlsl').write_text(code)
parameters={'WaterStrength':24.0,'SideLift':2.0,'BowLift':2.0,'WaveWidthCm':60.0}
inputs=list(shape.get_editor_property('inputs'))
sources={}
for index,(name,default) in enumerate(parameters.items()):
 if not any(str(i.get_editor_property('input_name'))==name for i in inputs):
  i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
 e=next((e for e in ex if isinstance(e,unreal.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))==name),None)
 if not e:e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionScalarParameter,300,1100+index*140)
 e.set_editor_property('parameter_name',name);e.set_editor_property('default_value',default)
 e.set_editor_property('group','Boat Water Surge')
 e.set_editor_property('slider_min',0.0 if name!='WaveWidthCm' else 20.0)
 e.set_editor_property('slider_max',64.0 if name=='WaterStrength' else 120.0 if name=='WaveWidthCm' else 4.0)
 sources[name]=e
shape.set_editor_property('inputs',inputs)
for name,e in sources.items():assert unreal.MaterialEditingLibrary.connect_material_expressions(e,'',shape,name)
if 'clamp(WaterStrength' not in code:
 assert 'Force * 6.0' in code and '(1.0+bow*0.65)' in code
 code=code.replace('smoothstep(10.0,34.0,edge)','smoothstep(10.0,clamp(WaveWidthCm,20.0,120.0),edge)')
 code=code.replace('(1.0+bow*0.65)','clamp(SideLift,0.0,4.0) * (1.0+bow*clamp(BowLift,0.0,4.0))')
 code=code.replace('Force * 6.0','Force * clamp(WaterStrength,0.0,64.0)')
 shape.set_editor_property('code',code)
MaterialTools.recompile(m)
assert assets.save_loaded_asset(m,only_if_is_dirty=False)
if not assets.does_asset_exist(instance):
 mi=unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_BoatHullFluidForce','/Game/Water/Materials/BoatContact',unreal.MaterialInstanceConstant,unreal.MaterialInstanceConstantFactoryNew())
else:mi=unreal.load_asset(instance)
assert mi
unreal.MaterialEditingLibrary.set_material_instance_parent(mi,m)
unreal.MaterialEditingLibrary.update_material_instance(mi)
print('SURGE_PARAMETER_NAMES',unreal.MaterialEditingLibrary.get_scalar_parameter_names(m),unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi))
for name,default in parameters.items():
 unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,name,default)
 actual=unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,name)
 assert abs(actual-default)<.001,(name,actual,default)
unreal.MaterialEditingLibrary.update_material_instance(mi)
assert assets.save_loaded_asset(mi,only_if_is_dirty=False)
graph=BlueprintTools.get_graph(bp,'UpdateFXState_0')
old=BlueprintTools.read_graph_dsl(graph);(backup/'UpdateFXState.dsl').write_text(old)
# Change only material defaults; preserve water sampling signatures and graph wiring.
editor=unreal.BlueprintGraphEditor.get_graph_editor(graph)
changed=0
for node in BlueprintTools.get_node_infos(list(editor.list_all_nodes())):
 for pin in node.input_pins:
  if base+'.M_BoatHullFluidForce' in pin.value:
   BlueprintTools.set_pin_value(pin.pin_id,instance+'.MI_BoatHullFluidForce')
   actual=BlueprintTools.get_pin_value(pin.pin_id)
   assert 'MI_BoatHullFluidForce' in actual,(pin.name,actual)
   changed+=1
print('SURGE_MATERIAL_PINS_CHANGED',changed)
BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
readback=BlueprintTools.read_graph_dsl(graph)
assert readback.count('MI_BoatHullFluidForce')>=4,readback
assert readback.count('ApplyFluidForceImpulse')==2
assert assets.save_loaded_asset(bp,only_if_is_dirty=False)
print('SURGING_WATER_SAVED',parameters,str(backup))

"""Editor GPU check for exterior water pressure and rendered displacement wiring."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
world=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
collection=unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
names=('Origin','AxisX','AxisY','AxisZ')
old={n:unreal.MaterialLibrary.get_vector_parameter_value(world,collection,n) for n in names}
instance='/Game/Water/Materials/BoatContact/MI_BoatHullFluidForce'
material=unreal.load_asset(instance if unreal.EditorAssetLibrary.does_asset_exist(instance) else '/Game/Water/Materials/BoatContact/M_BoatHullFluidForce')
mid=unreal.MaterialLibrary.create_dynamic_material_instance(world,material)
rt=unreal.RenderingLibrary.create_render_target2d(world,128,128,unreal.TextureRenderTargetFormat.RTF_RGBA16F)
results=[]
try:
 for label,yaw,z,force in [('slow',0,375,-.00625),('fast',0,375,-.025),('turn',90,375,-.025),('dry',0,600,-.025),('stopped',0,375,0)]:
  rot=unreal.Rotator(pitch=0,yaw=yaw,roll=0)
  x=unreal.MathLibrary.get_forward_vector(rot);y=unreal.MathLibrary.get_right_vector(rot)
  for n,v in zip(names,[unreal.LinearColor(0,0,z,0),unreal.LinearColor(x.x,x.y,x.z,1),unreal.LinearColor(y.x,y.y,y.z,.016),unreal.LinearColor(0,0,1,400)]):unreal.MaterialLibrary.set_vector_parameter_value(world,collection,n,v)
  mid.set_scalar_parameter_value('F',force)
  unreal.RenderingLibrary.clear_render_target2d(world,rt)
  unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
  samples=unreal.RenderingLibrary.read_render_target_raw(world,rt,False)
  if isinstance(samples,tuple):samples=next(i for i in samples if not isinstance(i,bool))
  heights=[c.r for c in samples]
  if label in ('dry','stopped'):assert max(abs(h) for h in heights)<.00001,label
  else:
   assert heights[64*128+64]<0,label
   assert min(heights)<-.03 and max(heights)>.02,(label,min(heights),max(heights))
  results.append(dict(case=label,minimum=min(heights),maximum=max(heights)))
 assert abs(results[1]['minimum']/results[0]['minimum']-4)<.01
 assert abs(results[1]['maximum']-results[2]['maximum'])<.002
 if material.get_name()=='MI_BoatHullFluidForce':
  gain=mid.get_scalar_parameter_value('WaterStrength')
  assert gain==24.0,gain
  mid.set_scalar_parameter_value('F',-.025)
  for label,strength in [('double_strength',48.0),('zero_strength',0.0)]:
   mid.set_scalar_parameter_value('WaterStrength',strength)
   unreal.RenderingLibrary.clear_render_target2d(world,rt)
   unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
   samples=unreal.RenderingLibrary.read_render_target_raw(world,rt,False)
   if isinstance(samples,tuple):samples=next(i for i in samples if not isinstance(i,bool))
   hs=[c.r for c in samples]
   if strength==0:assert max(abs(h) for h in hs)<.00001
   else:assert abs(min(hs)/results[1]['minimum']-2)<.01
   results.append(dict(case=label,minimum=min(hs),maximum=max(hs)))
  mid.set_scalar_parameter_value('WaterStrength',gain)

 m=unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
 ex=MaterialTools.get_expressions(m)
 surface=next(e for e in ex if e.get_editor_property('desc')=='DynamicWaterSurface')
 final=next(e for e in ex if isinstance(e,unreal.MaterialExpressionMakeMaterialAttributes))
 inputs={i.input_name:i.expression for i in MaterialTools.get_expression_inputs(m,final)}
 assert all(inputs[n]==surface for n in ('WorldPositionOffset','Normal'))
 source=MaterialTools.get_expression_inputs(m,surface)[0].expression
 assert source.get_editor_property('material_function').get_name()=='SampleFluidSimulation'
finally:
 for n,v in old.items():unreal.MaterialLibrary.set_vector_parameter_value(world,collection,n,v)
 unreal.RenderingLibrary.release_render_target2d(rt)
(Path(unreal.Paths.project_saved_dir())/'Automation/BoatContact/dynamic-water-check.json').write_text(json.dumps(results,indent=2))
print('DYNAMIC_WATER_GPU_AND_SURFACE_PASS',results)

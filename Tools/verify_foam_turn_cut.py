"""Editor GPU regression: historical foam remains visible as the current boat rotates."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
def verify():
 subsystem=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
 # This diagnostic only changes the editor world's MPC, never the PIE world's.
 world=unreal.load_object(None,'/Game/Maps/M_WaterPhysicsTest.M_WaterPhysicsTest')
 assert world and 'UEDPIE' not in world.get_path_name()
 assert world,'Editor map must be ready'
 water=unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
 source=next(e for e in MaterialTools.get_expressions(water) if e.get_editor_property('desc')=='BoatRippleFoam')
 code=source.get_editor_property('code')
 fixed='return max(live, trail);'
 assert fixed in code
 collection=unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
 names=('Origin','AxisX','AxisY','AxisZ','FoamFrame')
 old={n:unreal.MaterialLibrary.get_vector_parameter_value(world,collection,n) for n in names}
 # Diagnostic shader stays transient; no test asset or force-delete is needed.
 m=unreal.Material()
 white=unreal.RenderingLibrary.create_render_target2d(world,4,4,unreal.TextureRenderTargetFormat.RTF_RGBA16F)
 rt=unreal.RenderingLibrary.create_render_target2d(world,4,4,unreal.TextureRenderTargetFormat.RTF_RGBA16F)
 black=unreal.RenderingLibrary.create_render_target2d(world,4,4,unreal.TextureRenderTargetFormat.RTF_RGBA16F)
 rows=[]
 mid=None
 texture_expressions=[]
 fallback=unreal.load_asset('/Game/Water/Materials/BoatContact/T_BoatOuterProfile')
 style_names=('WaveFoamGain','WakeFoamGain','FoamPatternScale','FoamBreakup')
 ocean=unreal.load_asset('/Game/Water/Materials/BoatContact/MI_WaterBoatOcean')
 style_values={n:unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(ocean,n) for n in style_names}
 try:
  unreal.RenderingLibrary.clear_render_target2d(world,white,unreal.LinearColor(1,1,1,1))
  m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
  custom=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionCustom,500,0)
  input_names=[str(i.get_editor_property('input_name')) for i in source.get_editor_property('inputs')]+['LegacyGate']
  ins=[]
  for name in input_names:
   i=unreal.CustomInput();i.set_editor_property('input_name',name);ins.append(i)
  custom.set_editor_property('inputs',ins)
  custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT1)
  custom.set_editor_property('code',code.replace(fixed,'return lerp(' + fixed.removeprefix('return ').removesuffix(';') + ', max(max(live, trail), contactFoam) * forwardFoamGate, LegacyGate);'))
  for index,name in enumerate(input_names):
   if name in names:
    e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionCollectionParameter,0,index*100)
    e.set_editor_property('collection',collection);e.set_editor_property('parameter_name',name)
   elif name=='World':
    e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionVectorParameter,0,index*100)
    e.set_editor_property('parameter_name','ProbeWorld');e.set_editor_property('default_value',unreal.LinearColor(-800,0,400,1))
   elif name=='FluidDelta':
    e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionVectorParameter,0,index*100)
    e.set_editor_property('parameter_name','ProbeFluidDelta');e.set_editor_property('default_value',unreal.LinearColor(0,0,0,0))
   elif name in ('FoamTexture','FoamRT','ContactProfile'):
    e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionTextureObjectParameter,0,index*100)
    e.set_editor_property('parameter_name',name)
    texture_expressions.append(e)
    e.set_editor_property('texture',unreal.load_asset('/Game/Water/Materials/BoatContact/T_BoatOuterProfile') if name=='ContactProfile' else white)
    e.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
   elif name in ('DispMul','LegacyGate') or name in style_names:
    e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionScalarParameter,0,index*100)
    e.set_editor_property('parameter_name',name);e.set_editor_property('default_value',style_values[name] if name in style_names else 1 if name=='DispMul' else 0)
   else:raise AssertionError(('Unexpected input',name))
   output='RGB' if name in ('FluidDelta','World') and 'RGB' in unreal.MaterialEditingLibrary.get_material_expression_output_names(e) else ''
   assert unreal.MaterialEditingLibrary.connect_material_expressions(e,output,custom,name)
  assert unreal.MaterialEditingLibrary.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
  MaterialTools.recompile(m)
  mid=unreal.MaterialLibrary.create_dynamic_material_instance(world,m,creation_flags=unreal.MIDCreationFlags.TRANSIENT)
  for label,legacy,yaw in [('old_cut',1,0),('fixed_0',0,0),('fixed_90',0,90),('fixed_180',0,180),('fixed_270',0,270)]:
   rot=unreal.Rotator(pitch=0,yaw=yaw,roll=0)
   x=unreal.MathLibrary.get_forward_vector(rot);y=unreal.MathLibrary.get_right_vector(rot)
   vals=[unreal.LinearColor(0,0,375,0),unreal.LinearColor(x.x,x.y,x.z,0),unreal.LinearColor(y.x,y.y,y.z,.016),unreal.LinearColor(0,0,1,400),unreal.LinearColor(-2048,-2048,4096,0)]
   for n,v in zip(names,vals):unreal.MaterialLibrary.set_vector_parameter_value(world,collection,n,v)
   mid.set_scalar_parameter_value('LegacyGate',legacy)
   unreal.RenderingLibrary.clear_render_target2d(world,rt)
   unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
   colors=unreal.RenderingLibrary.read_render_target_raw(world,rt,False)
   if isinstance(colors,tuple):colors=next(c for c in colors if not isinstance(c,bool))
   value=sum(c.r for c in colors)/len(colors)
   assert value<.001 if legacy else value>.7,(label,value)
   rows.append(dict(case=label,foam=value))
  assert max(r['foam'] for r in rows[1:])-min(r['foam'] for r in rows[1:])<.001,rows
  # Strong parameter contrasts prove the controls reach the GPU shader.
  mid.set_scalar_parameter_value('WakeFoamGain',0)
  unreal.RenderingLibrary.clear_render_target2d(world,rt)
  unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
  value=unreal.RenderingLibrary.read_render_target_raw_pixel(world,rt,0,0,False).r
  assert value<.001,('wake_off',value)
  rows.append(dict(case='wake_off',foam=value))
  mid.set_scalar_parameter_value('WakeFoamGain',style_values['WakeFoamGain'])
  if 'clamp(WaveFoamGain' in code:
   unreal.RenderingLibrary.clear_render_target2d(world,black)
   mid.set_texture_parameter_value('FoamRT',black)
   for label,height in [('gentle_wave',1.0),('raised_crest',8.0),('trough',-8.0)]:
    mid.set_vector_parameter_value('ProbeFluidDelta',unreal.LinearColor(0,0,height,0))
    unreal.RenderingLibrary.clear_render_target2d(world,rt)
    unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
    colors=unreal.RenderingLibrary.read_render_target_raw(world,rt,False)
    if isinstance(colors,tuple):colors=next(c for c in colors if not isinstance(c,bool))
    value=sum(c.r for c in colors)/len(colors)
    if label=='raised_crest':assert abs(value-style_values['WaveFoamGain'])<.002,(label,value)
    else:assert value<.001,(label,value)
    rows.append(dict(case=label,foam=value))
 
  mid.set_vector_parameter_value('ProbeFluidDelta',unreal.LinearColor(0,0,0,0))
  unreal.MaterialLibrary.set_vector_parameter_value(world,collection,'AxisX',unreal.LinearColor(1,0,0,1))
  unreal.MaterialLibrary.set_vector_parameter_value(world,collection,'AxisY',unreal.LinearColor(0,1,0,.016))
  mid.set_vector_parameter_value('ProbeWorld',unreal.LinearColor(0,28,400,1))
  unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
  value=unreal.RenderingLibrary.read_render_target_raw_pixel(world,rt,0,0,False).r
  assert value<.001,('flat_hull_no_instant_foam',value)
  rows.append(dict(case='flat_hull_no_instant_foam',foam=value))
  mid.set_vector_parameter_value('ProbeWorld',unreal.LinearColor(-800,0,400,1))
  mid.set_vector_parameter_value('ProbeFluidDelta',unreal.LinearColor(0,0,8,0))
  unreal.RenderingLibrary.clear_render_target2d(world,white,unreal.LinearColor(.4,.4,.4,1))
  erosion=[]
  for breakup in (0,.65):
   mid.set_scalar_parameter_value('FoamBreakup',breakup)
   unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
   erosion.append(unreal.RenderingLibrary.read_render_target_raw_pixel(world,rt,0,0,False).r)
  assert erosion[0]>.05 and erosion[1]<.001,erosion
  rows.extend([dict(case='breakup_0',foam=erosion[0]),dict(case='breakup_065',foam=erosion[1])])
 finally:
  for n,v in old.items():unreal.MaterialLibrary.set_vector_parameter_value(world,collection,n,v)
  for e in texture_expressions:e.set_editor_property('texture',fallback)
  if mid:
   for name in ('FoamTexture','FoamRT','ContactProfile'):mid.set_texture_parameter_value(name,fallback)
  unreal.RenderingLibrary.release_render_target2d(white);unreal.RenderingLibrary.release_render_target2d(rt);unreal.RenderingLibrary.release_render_target2d(black)
 (Path(unreal.Paths.project_saved_dir())/'Automation/BoatContact/foam-turn-cut-check.json').write_text(json.dumps(rows,indent=2))
 print('FOAM_TURN_HISTORY_GPU_PASS',rows)

verify()

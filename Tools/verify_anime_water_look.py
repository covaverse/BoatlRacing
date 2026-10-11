"""GPU check of actual illustrated shader: style blend, palette controls and foam color."""
import json
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
def verify():
 world=unreal.load_object(None,'/Game/Maps/M_WaterPhysicsTest.M_WaterPhysicsTest')
 water=unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
 ocean=unreal.load_asset('/Game/Water/Materials/BoatContact/MI_WaterBoatOcean')
 source=next(e for e in MaterialTools.get_expressions(water) if e.get_editor_property('desc')=='AnimeIllustratedSurface')
 input_sources={i.input_name:i.expression for i in MaterialTools.get_expression_inputs(water,source)}
 noise=input_sources['Noise'].get_editor_property('texture')
 m=unreal.Material();m.set_editor_property('shading_model',unreal.MaterialShadingModel.MSM_UNLIT)
 custom=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionCustom,500,0)
 custom.set_editor_property('inputs',list(source.get_editor_property('inputs')))
 custom.set_editor_property('additional_outputs',list(source.get_editor_property('additional_outputs')))
 custom.set_editor_property('output_type',source.get_editor_property('output_type'))
 custom.set_editor_property('code',source.get_editor_property('code'))
 params={}
 constants={'DispMul':3,'Foam':0,'OriginalRoughness':.02,'OriginalSpecular':.225,'OriginalOpacity':.1}
 vectors={'FluidDelta':(0,0,0),'OriginalBase':(.2,.3,.4),'OriginalEmission':(.01,.02,.03)}
 for idx,i in enumerate(custom.get_editor_property('inputs')):
  name=str(i.get_editor_property('input_name'))
  if name=='World':
   uv=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionTextureCoordinate,0,0)
   e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionCustom,150,0)
   ci=unreal.CustomInput();ci.set_editor_property('input_name','UV');e.set_editor_property('inputs',[ci])
   e.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
   e.set_editor_property('code','return float3(UV*2048.0,400.0);')
   assert unreal.MaterialEditingLibrary.connect_material_expressions(uv,'',e,'UV')
  elif name=='Noise':
   e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionTextureObjectParameter,0,idx*100)
   e.set_editor_property('parameter_name',name);e.set_editor_property('texture',noise)
  elif name in vectors or name in ('FoamTint','AnimeDeepColor','AnimeWaterColor','AnimeHighlightColor'):
   e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionVectorParameter,0,idx*100)
   val=unreal.LinearColor(*vectors[name],1) if name in vectors else unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(ocean,'AnimeFoamTint' if name=='FoamTint' else name)
   e.set_editor_property('parameter_name',name);e.set_editor_property('default_value',val)
  else:
   e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionScalarParameter,0,idx*100)
   val=constants[name] if name in constants else unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(ocean,name)
   if name=='AnimeWaveSpeed':val=0
   e.set_editor_property('parameter_name',name);e.set_editor_property('default_value',val)
  params[name]=e
  assert unreal.MaterialEditingLibrary.connect_material_expressions(e,'RGB' if isinstance(e,unreal.MaterialExpressionVectorParameter) else '',custom,name)
 assert unreal.MaterialEditingLibrary.connect_material_property(custom,'',unreal.MaterialProperty.MP_EMISSIVE_COLOR)
 MaterialTools.recompile(m)
 mid=unreal.MaterialLibrary.create_dynamic_material_instance(world,m,creation_flags=unreal.MIDCreationFlags.TRANSIENT)
 rt=unreal.RenderingLibrary.create_render_target2d(world,32,32,unreal.TextureRenderTargetFormat.RTF_RGBA16F)
 def render():
  unreal.RenderingLibrary.draw_material_to_render_target(world,rt,mid)
  colors=unreal.RenderingLibrary.read_render_target_raw(world,rt,False)
  if isinstance(colors,tuple):colors=next(c for c in colors if not isinstance(c,bool))
  return [(c.r,c.g,c.b) for c in colors]
 def mean(values):return [sum(v[c] for v in values)/len(values) for c in range(3)]
 rows=[]
 try:
  samples=[]
  for style in (0,.5,1):
   mid.set_scalar_parameter_value('AnimeStyleStrength',style)
   values=render();samples.append(values);rows.append({'style':style,'mean':mean(values)})
  assert max(abs(v-c) for pixel in samples[0] for v,c in zip(pixel,(.2,.3,.4)))<.002,rows
  blend_error=max(abs(half-(a+b)*.5) for a_pixel,h_pixel,b_pixel in zip(*samples) for a,half,b in zip(a_pixel,h_pixel,b_pixel))
  assert blend_error<.002,blend_error
  changed=sum(abs(a-b) for pa,pb in zip(samples[0],samples[2]) for a,b in zip(pa,pb))/(len(samples[0])*3)
  assert changed>.04,changed
  # The palette and size controls must change actual pixels, beyond simply updating MI metadata.
  mid.set_vector_parameter_value('AnimeWaterColor',unreal.LinearColor(.6,.02,.03,1))
  red=render();assert mean(red)[0]-mean(samples[2])[0]>.1,(mean(red),rows)
  mid.set_vector_parameter_value('AnimeWaterColor',unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(ocean,'AnimeWaterColor'))
  mid.set_scalar_parameter_value('AnimeHighlightGain',0);no_highlight=render()
  mid.set_scalar_parameter_value('AnimeHighlightGain',2);strong_highlight=render()
  highlight_difference=mean(strong_highlight)[1]-mean(no_highlight)[1]
  assert highlight_difference>.001,highlight_difference
  mid.set_scalar_parameter_value('AnimeHighlightGain',unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(ocean,'AnimeHighlightGain'))
  mid.set_scalar_parameter_value('AnimeWaveScaleCm',150);small=render()
  mid.set_scalar_parameter_value('AnimeWaveScaleCm',1000);large=render()
  size_difference=sum(abs(a-b) for pa,pb in zip(small,large) for a,b in zip(pa,pb))/(len(small)*3)
  assert size_difference>.015,size_difference
  mid.set_scalar_parameter_value('Foam',1)
  white=render();tint=unreal.MaterialEditingLibrary.get_material_instance_vector_parameter_value(ocean,'AnimeFoamTint')
  assert max(abs(v-c) for pixel in white for v,c in zip(pixel,(tint.r,tint.g,tint.b)))<.003,mean(white)
  final=next(e for e in MaterialTools.get_expressions(water) if isinstance(e,unreal.MaterialExpressionMakeMaterialAttributes))
  wiring={i.input_name:i.expression.get_editor_property('desc') if i.expression else None for i in MaterialTools.get_expression_inputs(water,final)}
  assert wiring['Normal']==wiring['WorldPositionOffset']=='DynamicWaterSurface'
  assert all(wiring[n]=='AnimeIllustratedSurface' for n in ('BaseColor','EmissiveColor','Roughness','Specular','Opacity')),wiring
  report={'samples':rows,'style_difference':changed,'half_blend_error':blend_error,'scale_difference':size_difference,'highlight_difference':highlight_difference,'palette_control_mean':mean(red),'foam_color':mean(white),'dynamic_surface_preserved':True}
  (Path(unreal.Paths.project_saved_dir())/'Automation/BoatContact/anime-look-gpu-check.json').write_text(json.dumps(report,indent=2))
  print('ANIME_LOOK_GPU_PASS',report)
 finally:
  unreal.RenderingLibrary.release_render_target2d(rt)
verify()

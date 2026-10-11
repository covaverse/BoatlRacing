"""Editor Python: add a visible illustrated layer to the existing dynamic SLW surface."""
import datetime,json,shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
def install():
 assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
 root=Path(unreal.Paths.project_dir());folder='/Game/Water/Materials/BoatContact/'
 m=unreal.load_asset(folder+'M_WaterBoatContact');mi=unreal.load_asset(folder+'MI_WaterBoatOcean')
 backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-illustrated-water')
 backup.mkdir(parents=True)
 for asset in (m,mi):
  assert unreal.EditorAssetLibrary.save_loaded_asset(asset,only_if_is_dirty=False)
  file=asset.get_path_name().split('.')[0].replace('/Game/','Content/')+'.uasset'
  shutil.copy2(root/file,backup/Path(file).name)
 ex=MaterialTools.get_expressions(m)
 final=next(e for e in ex if isinstance(e,unreal.MaterialExpressionMakeMaterialAttributes))
 original=next(e for e in ex if e.get_name()=='MaterialExpressionBreakMaterialAttributes_0')
 foam=next(e for e in ex if e.get_editor_property('desc')=='BoatRippleFoam')
 custom=next((e for e in ex if e.get_editor_property('desc')=='AnimeIllustratedSurface'),None)
 existing={i.input_name:(i.expression,i.output_name) for i in MaterialTools.get_expression_inputs(m,final)}
 # Keep the native source graph and foam simulation intact. Only final appearance changes.
 if not custom:
  custom=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionCustom,3100,1000)
  custom.set_editor_property('desc','AnimeIllustratedSurface')
  custom.set_editor_property('description','Illustrated palette and broad painted reflections; white foam still comes from wave history.')
  ins=[]
  names=('World','Noise','FluidDelta','DispMul','Foam','FoamTint','OriginalBase','OriginalEmission','OriginalRoughness','OriginalSpecular','OriginalOpacity','AnimeStyleStrength','AnimeWaveScaleCm','AnimeHighlightGain','AnimeWaveSpeed','AnimeDeepColor','AnimeWaterColor','AnimeHighlightColor')
  for name in names:
   i=unreal.CustomInput();i.set_editor_property('input_name',name);ins.append(i)
  custom.set_editor_property('inputs',ins)
  custom.set_editor_property('output_type',unreal.CustomMaterialOutputType.CMOT_FLOAT3)
  outs=[]
  for name,typ in [('IllustratedEmission',unreal.CustomMaterialOutputType.CMOT_FLOAT3),('IllustratedRoughness',unreal.CustomMaterialOutputType.CMOT_FLOAT1),('IllustratedSpecular',unreal.CustomMaterialOutputType.CMOT_FLOAT1),('IllustratedOpacity',unreal.CustomMaterialOutputType.CMOT_FLOAT1)]:
   o=unreal.CustomOutput();o.set_editor_property('output_name',name);o.set_editor_property('output_type',typ);outs.append(o)
  custom.set_editor_property('additional_outputs',outs)
  for source,output,pin in [(existing['BaseColor'][0],'','OriginalBase'),(original,'EmissiveColor','OriginalEmission'),(existing['Roughness'][0],'','OriginalRoughness'),(original,'Specular','OriginalSpecular'),(existing['Opacity'][0],'','OriginalOpacity'),(foam,'','Foam')]:
   assert unreal.MaterialEditingLibrary.connect_material_expressions(source,output,custom,pin),pin
  sources={i.input_name:(i.expression,i.output_name) for i in MaterialTools.get_expression_inputs(m,foam)}
  for source_name,pin in [('World','World'),('FoamTexture','Noise'),('FluidDelta','FluidDelta'),('DispMul','DispMul')]:
   src,output=sources[source_name]
   assert unreal.MaterialEditingLibrary.connect_material_expressions(src,output,custom,pin),pin
  tint=next(e for e in ex if isinstance(e,unreal.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='AnimeFoamTint')
  assert unreal.MaterialEditingLibrary.connect_material_expressions(tint,'RGB',custom,'FoamTint')
 scalars={
  'AnimeStyleStrength':(0,0,1,'0 = original water, 1 = full illustrated palette, matte surface and grouped foam.'),
  'AnimeWaveScaleCm':(500,150,1200,'Painted reflection length in centimeters. Larger values make broader strokes.'),
  'AnimeHighlightGain':(.7,0,2,'Strength of pale blue painted reflections. These are highlights, not white foam.'),
  'AnimeWaveSpeed':(12,0,60,'Painted reflection drift in centimeters per second. Does not change boat physics or the fluid simulation.')
 }
 vectors={'AnimeDeepColor':(.025,.18,.30),'AnimeWaterColor':(.045,.42,.52),'AnimeHighlightColor':(.38,.75,.78)}
 for idx,(name,(default,lo,hi,desc)) in enumerate(scalars.items()):
  e=next((e for e in ex if isinstance(e,unreal.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))==name),None)
  if not e:e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionScalarParameter,2500,2300+idx*150)
  for prop,val in [('parameter_name',name),('default_value',default),('group','Anime Water - Look'),('slider_min',lo),('slider_max',hi),('desc',desc),('sort_priority',idx)]:e.set_editor_property(prop,val)
  assert unreal.MaterialEditingLibrary.connect_material_expressions(e,'',custom,name)
 for idx,(name,rgb) in enumerate(vectors.items()):
  e=next((e for e in ex if isinstance(e,unreal.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))==name),None)
  if not e:e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionVectorParameter,2500,2950+idx*150)
  e.set_editor_property('parameter_name',name);e.set_editor_property('default_value',unreal.LinearColor(*rgb,1));e.set_editor_property('group','Anime Water - Look');e.set_editor_property('sort_priority',10+idx)
  assert unreal.MaterialEditingLibrary.connect_material_expressions(e,'RGB',custom,name)
 code="""
// Illustrated color layer. Dynamic displacement, water normals, cavity and foam history remain upstream.
float style = saturate(AnimeStyleStrength);
float scale = max(AnimeWaveScaleCm, 50.0);
float2 uv = (World.xy + View.GameTime * AnimeWaveSpeed * float2(1.0,0.12)) / float2(scale,scale*0.24);
float warp = Texture2DSample(Noise, NoiseSampler, uv*0.27).r;
uv += (warp-0.5)*float2(0.25,0.65);
float n = Texture2DSample(Noise, NoiseSampler, uv).r;
float gate = Texture2DSample(Noise, NoiseSampler, uv*0.37+float2(0.31,0.19)).r;
float aa = max(fwidth(n),0.025);
float region = smoothstep(0.42-aa,0.42+aa,n);
float streak = smoothstep(0.76-aa,0.76+aa,n)*smoothstep(0.38,0.62,gate);
float distanceFade = 1.0-smoothstep(2000.0,8000.0,length(World-View.WorldCameraOrigin));
float3 palette = lerp(AnimeDeepColor,AnimeWaterColor,lerp(0.6,region,distanceFade));
palette = lerp(palette,AnimeHighlightColor,saturate(streak*AnimeHighlightGain)*distanceFade);
// A small color accent follows the real raised surface, not boat-facing decorative geometry.
float raised = smoothstep(2.0,14.0,max(FluidDelta.z/max(DispMul,1.0),0.0));
palette = lerp(palette,AnimeHighlightColor,raised*0.18);
float groupedFoam = smoothstep(0.12,0.62,saturate(Foam));
float3 illustrated = lerp(palette,FoamTint,groupedFoam);
IllustratedEmission = lerp(OriginalEmission,illustrated*0.18,style);
IllustratedRoughness = lerp(OriginalRoughness,lerp(0.52,0.70,groupedFoam),style);
IllustratedSpecular = lerp(OriginalSpecular,0.08,style);
// SLW opacity is surface-vs-volume weight: color must have surface weight to be visible.
IllustratedOpacity = lerp(OriginalOpacity,lerp(0.78,1.0,groupedFoam),style);
return lerp(OriginalBase,illustrated,style);
"""
 custom.set_editor_property('code',code)
 for output,pin in [('', 'BaseColor'),('IllustratedEmission','EmissiveColor'),('IllustratedRoughness','Roughness'),('IllustratedSpecular','Specular'),('IllustratedOpacity','Opacity')]:
  assert unreal.MaterialEditingLibrary.connect_material_expressions(custom,output,final,pin),(output,pin)
 MaterialTools.recompile(m)
 assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
 values={name:args[0] for name,args in scalars.items()};values['AnimeStyleStrength']=1
 for name,value in values.items():
  unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,name,value)
  assert abs(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,name)-value)<.001,name
 for name,rgb in vectors.items():unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,name,unreal.LinearColor(*rgb,1))
 unreal.MaterialEditingLibrary.update_material_instance(mi)
 assert unreal.EditorAssetLibrary.save_loaded_asset(mi,only_if_is_dirty=False)
 read={i.input_name:(i.expression.get_editor_property('desc') if i.expression else None) for i in MaterialTools.get_expression_inputs(m,final)}
 assert read['WorldPositionOffset']=='DynamicWaterSurface' and read['Normal']=='DynamicWaterSurface',read
 report={'backup':str(backup),'scalars':values,'preserved_dynamic_wpo_and_normal':True,'final_inputs':read}
 (root/'Saved/Automation/BoatContact/anime-look-install.json').write_text(json.dumps(report,indent=2))
 print('ILLUSTRATED_WATER_INSTALLED',report)
install()

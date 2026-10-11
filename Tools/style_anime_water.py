"""Editor Python: style the existing dynamic ocean toward clear illustrated anime water."""
import datetime,shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
assets=unreal.EditorAssetLibrary;root=Path(unreal.Paths.project_dir())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
folder='/Game/Water/Materials/BoatContact/'
m=unreal.load_asset(folder+'M_WaterBoatContact');mi=unreal.load_asset(folder+'MI_WaterBoatOcean')
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-anime-water')
backup.mkdir(parents=True)
for asset in (m,mi):
 assert assets.save_loaded_asset(asset,only_if_is_dirty=False)
 file=asset.get_path_name().split('.')[0].replace('/Game/','Content/')+'.uasset'
 shutil.copy2(root/file,backup/Path(file).name)
ex=MaterialTools.get_expressions(m)
foam=next(e for e in ex if e.get_editor_property('desc')=='BoatRippleFoam')
old=foam.get_editor_property('code');(backup/'foam-before.hlsl').write_text(old)
parameters={'WaveFoamGain':.22,'WakeFoamGain':.95,'FoamPatternScale':1.8,'FoamBreakup':.28}
inputs=list(foam.get_editor_property('inputs'));sources={}
for index,(name,default) in enumerate(parameters.items()):
 if not any(str(i.get_editor_property('input_name'))==name for i in inputs):
  i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
 e=next((e for e in ex if isinstance(e,unreal.MaterialExpressionScalarParameter) and str(e.get_editor_property('parameter_name'))==name),None)
 if not e:e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionScalarParameter,1900,3600+index*140)
 e.set_editor_property('parameter_name',name);e.set_editor_property('default_value',default);e.set_editor_property('group','Anime Water')
 e.set_editor_property('slider_min',.25 if name=='FoamPatternScale' else 0)
 e.set_editor_property('slider_max',4 if name=='FoamPatternScale' else .7 if name=='FoamBreakup' else 1)
 sources[name]=e
foam.set_editor_property('inputs',inputs)
for name,e in sources.items():assert unreal.MaterialEditingLibrary.connect_material_expressions(e,'',foam,name)
if 'clamp(WaveFoamGain' not in old:
 changes={
 'float amp = max(simDelta.z, 0.0) + max(-simDelta.z, 0.0) * 0.45;':'float amp = max(simDelta.z, 0.0); // Illustrated foam belongs to raised crests, not every trough.',
 'smoothstep(0.12, 1.4, amp)':'smoothstep(1.5, 7.0, amp)',
 'World.xy / 160.0':'World.xy / (160.0 * max(FoamPatternScale, 0.25))',
 'smoothstep(0.10, 0.72, large) * (0.78 + 0.22 * fine)':'smoothstep(clamp(FoamBreakup,0.0,0.7), 0.82, large) * (0.85 + 0.15 * fine)',
 'saturate(disturbed * grain) * 0.72':'saturate(disturbed * grain) * clamp(WaveFoamGain,0.0,1.0)',
 'saturate(trail * 1.6) * grain * 0.82':'saturate(trail * 1.6) * grain * 0.82 * clamp(WakeFoamGain,0.0,1.0)'}
 code=old
 for a,b in changes.items():assert a in code,a;code=code.replace(a,b)
 assert 'contactFoam * forwardFoamGate' in code
 foam.set_editor_property('code',code)
# Tinted foam uses the existing foam blend, preserving the water shading pipeline.
final=next(e for e in ex if isinstance(e,unreal.MaterialExpressionMakeMaterialAttributes))
blend=next(i.expression for i in MaterialTools.get_expression_inputs(m,final) if i.input_name=='BaseColor')
assert isinstance(blend,unreal.MaterialExpressionLinearInterpolate)
tint=next((e for e in ex if isinstance(e,unreal.MaterialExpressionVectorParameter) and str(e.get_editor_property('parameter_name'))=='AnimeFoamTint'),None)
if not tint:tint=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionVectorParameter,2450,1300)
tint.set_editor_property('parameter_name','AnimeFoamTint');tint.set_editor_property('default_value',unreal.LinearColor(.82,.96,1,1));tint.set_editor_property('group','Anime Water')
assert unreal.MaterialEditingLibrary.connect_material_expressions(tint,'',blend,'B')
# Boat foam gain controls both the old wake and fresh hull foam.
code=foam.get_editor_property('code')
code=code.replace('contactFoam * forwardFoamGate);','contactFoam * forwardFoamGate * clamp(WakeFoamGain,0.0,1.0));')
foam.set_editor_property('code',code)
m.modify();MaterialTools.recompile(m)
assert assets.save_loaded_asset(m,only_if_is_dirty=False)
scalars={'Water Roughness':.10,'Water Fresnel Roughness':.16,'Water Specular':.26,'Default Near Normal Strength':.14,'Default Distant Normal Strength':.16,'Default Distant Normal StrengthB':.12,'Default Near Water Scale':700,'Fluidsim Normal Strength':.70,**parameters}
vectors={'Water Albedo':unreal.LinearColor(.32,.82,1,.5),'Scattering':unreal.LinearColor(.6,.95,1,.65),'Absorption':unreal.LinearColor(8,180,500,8),'AnimeFoamTint':unreal.LinearColor(.82,.96,1,1)}
for name,value in scalars.items():
 unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,name,value)
 actual=unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,name)
 assert abs(actual-value)<.001,(name,actual,value)
for name,value in vectors.items():unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(mi,name,value)
unreal.MaterialEditingLibrary.update_material_instance(mi)
assert assets.save_loaded_asset(mi,only_if_is_dirty=False)
# The active actor already uses this instance; force its visual MID to refresh in the editor.
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.WaterBody):
 for c in a.get_components_by_class(unreal.WaterBodyComponent):
  if c.get_editor_property('WaterMaterial')==mi:c.set_editor_property('WaterMaterial',mi)
print('ANIME_WATER_STYLE_SAVED',str(backup),scalars)

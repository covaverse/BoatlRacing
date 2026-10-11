"""Editor Python: place side spray on water and render immediate exterior contact foam."""
import datetime, shutil, re
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

root=Path(unreal.Paths.project_dir())
assets=unreal.EditorAssetLibrary
bp=unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
m=unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
assert not unreal.EditorLevelLibrary.get_game_world()
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-surface-contact')
backup.mkdir(parents=True)
for a in (bp,m):
    assert assets.save_loaded_asset(a,only_if_is_dirty=False)
    file=a.get_path_name().split('.')[0].replace('/Game/','Content/')+'.uasset'
    shutil.copy2(root/file,backup/Path(file).name)
graph=BlueprintTools.get_graph(bp,'UpdateSideSpray')
old=BlueprintTools.read_graph_dsl(graph)
(backup/'UpdateSideSpray.dsl').write_text(old)
if '_surfaceanchor' not in old:
    # The graph reader emits literal binds that its writer cannot consume.
    # Inline those values before round-tripping the existing graph.
    for match in list(re.finditer(r'^  \(bind (\w+) (-?\d+(?:\.\d+)?)\)\r?\n',old,re.M)):
        name,value=match.groups()
        old=old.replace(match.group(0),'')
        old=re.sub(r'(?<!\w)'+re.escape(name)+r'(?!\w)',value,old)
    marker='  (Niagara|SetNiagaraVariable(Float) _sidesprayfx'
    assert marker in old
    insertion='''  (bind _visualpos (Transformation|GetWorldLocation (Variables|Default|GetBoatVisual)))
  (bind _surfaceanchor (Math|Vector|MakeVector (.x _visualpos) (.y _visualpos) (+ (Variables|Default|GetWaterSurfaceZ) 2.0)))
  (bind _surfacerot (Math|Rotator|MakeRotator 0.0 0.0 (.yaw (Transformation|GetWorldRotation (Variables|Default|GetBoatVisual)))))
  (Transformation|SetWorldLocation _sidesprayfx _surfaceanchor)
  (Transformation|SetWorldRotation _sidesprayfx _surfacerot)
  (Transformation|SetWorldLocation _spraymistfx _surfaceanchor)
  (Transformation|SetWorldRotation _spraymistfx _surfacerot)
'''
    BlueprintTools.write_graph_dsl(graph,old.replace(marker,insertion+marker,1))
    BlueprintTools.compile_blueprint(bp,warnings_as_errors=True)
    assert len(BlueprintTools.find_nodes(graph,'Set World Location')) >= 2, 'Surface anchor graph was not installed'

expressions=MaterialTools.get_expressions(m)
custom=next(e for e in expressions if e.get_editor_property('desc')=='BoatRippleFoam')
code=custom.get_editor_property('code')
(backup/'water-foam.hlsl').write_text(code)
inputs=list(custom.get_editor_property('inputs'))
collection=unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
sources={}
for name in ('AxisY','AxisZ','ContactProfile'):
    if not any(str(i.get_editor_property('input_name'))==name for i in inputs):
        i=unreal.CustomInput();i.set_editor_property('input_name',name);inputs.append(i)
    if name=='ContactProfile':
        e=next((e for e in expressions if isinstance(e,unreal.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='ExteriorContactProfile'),None)
        if not e:
            e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionTextureObjectParameter,1900,3100)
            e.set_editor_property('parameter_name','ExteriorContactProfile')
            e.set_editor_property('texture',unreal.load_asset('/Game/Water/Materials/BoatContact/T_BoatOuterProfile'))
            e.set_editor_property('sampler_type',unreal.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR)
    else:
        e=next((e for e in expressions if isinstance(e,unreal.MaterialExpressionCollectionParameter) and str(e.get_editor_property('parameter_name'))==name),None)
        if not e:
            e=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionCollectionParameter,1900,3300 if name=='AxisY' else 3450)
            e.set_editor_property('collection',collection);e.set_editor_property('parameter_name',name)
    sources[name]=e
# Update once and preserve all existing links. Append inputs without overwriting earlier connections.
custom.set_editor_property('inputs',inputs)
for name,e in sources.items():assert unreal.MaterialEditingLibrary.connect_material_expressions(e,'',custom,name)
if 'exteriorContact' not in code:
    needle='return max(live, trail) * forwardFoamGate;'
    assert needle in code
    custom.set_editor_property('code',code.replace(needle,'''// Immediate contact uses the rendered water surface; history remains in the foam RT.
float3 contactDelta = World - Origin.rgb;
float3 contactLocal = float3(hullX, dot(contactDelta, AxisY.rgb), dot(contactDelta, AxisZ.rgb));
float2 contactUV = (contactLocal.xz + float2(320.0,16.0)) / float2(640.0,128.0);
float2 exterior = Texture2DSampleLevel(ContactProfile, ContactProfileSampler, saturate(contactUV), 0).rg;
float contactValid = exterior.g * step(0.0,contactUV.x) * step(contactUV.x,1.0)
                              * step(0.0,contactUV.y) * step(contactUV.y,1.0);
float contactEdge = abs(contactLocal.y) - exterior.r * 64.0;
float exteriorContact = (1.0-smoothstep(2.0,12.0,abs(contactEdge-2.0))) * contactValid;
float contactMoving = smoothstep(0.03,0.4,AxisX.a);
float contactFoam = exteriorContact * contactMoving * (0.45+grain*0.45);
return max(max(live, trail), contactFoam) * forwardFoamGate;
'''))
m.modify();unreal.MaterialEditingLibrary.recompile_material(m)
for a in (bp,m):assert assets.save_loaded_asset(a,only_if_is_dirty=False)
print('SURFACE_CONTACT_SAVED',str(backup))

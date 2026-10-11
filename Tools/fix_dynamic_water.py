"""Editor Python: use measured exterior pressure to drive the existing dynamic ripple field."""
import datetime,shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
root=Path(unreal.Paths.project_dir())
assert not unreal.EditorLevelLibrary.get_game_world()
m=unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatHullFluidForce')
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-dynamic-water')
backup.mkdir(parents=True)
unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
shutil.copy2(root/'Content/Water/Materials/BoatContact/M_BoatHullFluidForce.uasset',backup/m.get_name().replace('Force','Force.uasset'))
expressions=MaterialTools.get_expressions(m)
shape=next(e for e in expressions if e.get_editor_property('desc')=='MeasuredHullPressure')
(backup/'pressure-before.hlsl').write_text(shape.get_editor_property('code'))
profile=next(e for e in expressions if isinstance(e,unreal.MaterialExpressionTextureObjectParameter) and str(e.get_editor_property('parameter_name'))=='Hull Profile')
profile.set_editor_property('texture',unreal.load_asset('/Game/Water/Materials/BoatContact/T_BoatOuterProfile'))
shape.set_editor_property('code','''
// ponytail: exterior pressure drives the native height-field solver; no volumetric CFD.
// The impulse canvas is 720 cm across and follows the visual hull frame.
float3 d = float3((UV - 0.5) * 720.0, AxisZ.a - Origin.z);
float3 p = float3(dot(d, AxisX.rgb), dot(d, AxisY.rgb), dot(d, AxisZ.rgb));
float2 profileUV = (p.xz + float2(320.0,16.0)) / float2(640.0,128.0);
float2 exterior = Texture2DSampleLevel(Profile, ProfileSampler, saturate(profileUV), 0).rg;
float valid = exterior.g * step(0.0,profileUV.x) * step(profileUV.x,1.0)
                         * step(0.0,profileUV.y) * step(profileUV.y,1.0);
float width = exterior.r * 64.0;
float edge = abs(p.y) - width;
float core = 1.0-smoothstep(-6.0,6.0,edge);
// Raised shoulders start at the outer shell, rather than the dry interior liner.
float bank = smoothstep(-2.0,6.0,edge)*(1.0-smoothstep(10.0,34.0,edge));
float bow = 1.0-smoothstep(-260.0,-90.0,p.x);
float pressure = core - bank * max(width,8.0)/20.0 * (1.0+bow*0.65);
// Existing impulse F supplies speed, vertical entry velocity and frame-time scaling.
return float3(Force * 6.0 * valid * pressure,0.0,0.0);
''')
m.modify()
MaterialTools.recompile(m)
assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
print('DYNAMIC_WATER_PRESSURE_SAVED',str(backup))

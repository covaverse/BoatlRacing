"""Keep parameter effects visible and document units in material tooltips."""
import unreal,datetime,shutil,json
from pathlib import Path
from editor_toolset.toolsets.material import MaterialTools
assets=unreal.EditorAssetLibrary;root=Path(unreal.Paths.project_dir())
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
folder='/Game/Water/Materials/BoatContact/'
m=unreal.load_asset(folder+'M_WaterBoatContact')
force=unreal.load_asset(folder+'M_BoatHullFluidForce')
mi=unreal.load_asset(folder+'MI_BoatHullFluidForce')
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-water-controls')
backup.mkdir(parents=True)
for asset in (m,force,mi):
 assert assets.save_loaded_asset(asset,only_if_is_dirty=False)
 file=asset.get_path_name().split('.')[0].replace('/Game/','Content/')+'.uasset'
 shutil.copy2(root/file,backup/Path(file).name)
ex=MaterialTools.get_expressions(m)
foam=next(e for e in ex if str(e.get_editor_property('desc'))=='BoatRippleFoam')
code=foam.get_editor_property('code')
old='return max(max(live, trail), contactFoam * forwardFoamGate);'
new='return max(max(live, trail), contactFoam * forwardFoamGate * clamp(WakeFoamGain,0.0,1.0));'
assert old in code or new in code or 'return max(live, trail);' in code
foam.set_editor_property('code',code.replace(old,new))
desc={
'WaveFoamGain':'\u0e1f\u0e2d\u0e07\u0e1a\u0e19\u0e22\u0e2d\u0e14\u0e04\u0e25\u0e37\u0e48\u0e19\u0e17\u0e35\u0e48\u0e40\u0e23\u0e37\u0e2d\u0e2a\u0e23\u0e49\u0e32\u0e07: 0 \u0e1b\u0e34\u0e14 / 1 \u0e21\u0e32\u0e01\u0e2a\u0e38\u0e14; \u0e19\u0e49\u0e33\u0e40\u0e23\u0e35\u0e22\u0e1a\u0e44\u0e21\u0e48\u0e21\u0e35\u0e04\u0e25\u0e37\u0e48\u0e19\u0e08\u0e30\u0e44\u0e21\u0e48\u0e40\u0e1b\u0e25\u0e35\u0e48\u0e22\u0e19. Raised simulated crest foam, 0-1.',
'WakeFoamGain':'\u0e1f\u0e2d\u0e07\u0e02\u0e2d\u0e1a\u0e40\u0e23\u0e37\u0e2d\u0e41\u0e25\u0e30\u0e23\u0e2d\u0e22\u0e17\u0e49\u0e32\u0e22\u0e40\u0e23\u0e37\u0e2d: 0 \u0e1b\u0e34\u0e14 / 1 \u0e40\u0e15\u0e47\u0e21; \u0e44\u0e21\u0e48\u0e40\u0e1b\u0e25\u0e35\u0e48\u0e22\u0e19\u0e2a\u0e40\u0e1b\u0e23\u0e22\u0e4c Niagara. Hull + historical wake foam, 0-1.',
'FoamPatternScale':'\u0e02\u0e19\u0e32\u0e14\u0e25\u0e32\u0e22\u0e1f\u0e2d\u0e07: \u0e40\u0e1e\u0e34\u0e48\u0e21 = \u0e01\u0e49\u0e2d\u0e19\u0e43\u0e2b\u0e0d\u0e48; \u0e25\u0e2d\u0e07 0.5 \u0e01\u0e31\u0e1a 3 \u0e40\u0e1e\u0e37\u0e48\u0e2d\u0e40\u0e17\u0e35\u0e22\u0e1a. Pattern size multiplier, 0.25-4.',
'FoamBreakup':'\u0e0a\u0e48\u0e2d\u0e07\u0e27\u0e48\u0e32\u0e07\u0e43\u0e19\u0e25\u0e32\u0e22\u0e1f\u0e2d\u0e07: \u0e40\u0e1e\u0e34\u0e48\u0e21 = \u0e02\u0e2d\u0e1a\u0e41\u0e15\u0e01/\u0e42\u0e1b\u0e23\u0e48\u0e07\u0e21\u0e32\u0e01\u0e02\u0e36\u0e49\u0e19; \u0e25\u0e2d\u0e07 0 \u0e01\u0e31\u0e1a 0.65. Foam erosion threshold, 0-0.7.',
'AnimeFoamTint':'\u0e2a\u0e35\u0e1f\u0e2d\u0e07\u0e1a\u0e19\u0e1c\u0e34\u0e27\u0e19\u0e49\u0e33; \u0e44\u0e21\u0e48\u0e43\u0e0a\u0e48\u0e2a\u0e35\u0e17\u0e30\u0e40\u0e25\u0e2b\u0e23\u0e37\u0e2d\u0e2a\u0e40\u0e1b\u0e23\u0e22\u0e4c Niagara. Surface foam tint, RGB linear color.'
}
for e in ex:
 if isinstance(e,(unreal.MaterialExpressionScalarParameter,unreal.MaterialExpressionVectorParameter)):
  name=str(e.get_editor_property('parameter_name'))
  if name in desc:e.set_editor_property('desc',desc[name])
force_desc={
'WaterStrength':'\u0e41\u0e23\u0e07\u0e41\u0e2b\u0e27\u0e01\u0e19\u0e49\u0e33: 0 \u0e1b\u0e34\u0e14; \u0e40\u0e1e\u0e34\u0e48\u0e21 = \u0e41\u0e23\u0e07\u0e01\u0e14/\u0e22\u0e01\u0e1c\u0e34\u0e27\u0e19\u0e49\u0e33\u0e21\u0e32\u0e01\u0e02\u0e36\u0e49\u0e19\u0e15\u0e32\u0e21\u0e04\u0e27\u0e32\u0e21\u0e40\u0e23\u0e47\u0e27. Force gain, 0-64. Separate from displayed height.',
'SideLift':'\u0e04\u0e27\u0e32\u0e21\u0e41\u0e23\u0e07\u0e02\u0e2d\u0e07\u0e2a\u0e31\u0e19\u0e19\u0e49\u0e33\u0e2a\u0e2d\u0e07\u0e02\u0e49\u0e32\u0e07\u0e40\u0e23\u0e37\u0e2d: 0 \u0e1b\u0e34\u0e14 / 1 \u0e1b\u0e01\u0e15\u0e34 / 2 \u0e41\u0e23\u0e07. Side shoulder gain, 0-4.',
'BowLift':'\u0e40\u0e1e\u0e34\u0e48\u0e21\u0e2a\u0e31\u0e19\u0e19\u0e49\u0e33\u0e43\u0e01\u0e25\u0e49\u0e2b\u0e31\u0e27\u0e40\u0e23\u0e37\u0e2d: 0 \u0e44\u0e21\u0e48\u0e40\u0e1e\u0e34\u0e48\u0e21 / 2 \u0e40\u0e14\u0e48\u0e19. Additional bow shoulder gain, 0-4.',
'WaveWidthCm':'\u0e04\u0e27\u0e32\u0e21\u0e01\u0e27\u0e49\u0e32\u0e07\u0e2a\u0e31\u0e19\u0e19\u0e49\u0e33\u0e40\u0e1b\u0e47\u0e19\u0e40\u0e0b\u0e19\u0e15\u0e34\u0e40\u0e21\u0e15\u0e23: 20-120; 0.2 \u0e44\u0e21\u0e48\u0e43\u0e0a\u0e48 20% \u0e41\u0e25\u0e30\u0e08\u0e30\u0e16\u0e39\u0e01\u0e08\u0e33\u0e01\u0e31\u0e14\u0e40\u0e1b\u0e47\u0e19 20. Shoulder width in cm.'
}
for e in MaterialTools.get_expressions(force):
 if isinstance(e,unreal.MaterialExpressionScalarParameter):
  name=str(e.get_editor_property('parameter_name'))
  if name in force_desc:e.set_editor_property('desc',force_desc[name])
MaterialTools.recompile(m);MaterialTools.recompile(force)
for asset in (m,force):assert assets.save_loaded_asset(asset,only_if_is_dirty=False)
values={str(n):unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,n) for n in force_desc}
(root/'Saved/Automation/BoatContact/force-current-settings.json').write_text(json.dumps(values,indent=2))
print('WATER_CONTROLS_SAVED',values,str(backup))

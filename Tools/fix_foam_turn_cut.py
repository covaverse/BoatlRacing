"""Editor Python: preserve old world-space foam when the current boat rotates."""
import datetime,shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
assert not unreal.EditorLevelLibrary.get_game_world()
root=Path(unreal.Paths.project_dir());m=unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-foam-turn-cut')
backup.mkdir(parents=True)
assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
shutil.copy2(root/'Content/Water/Materials/BoatContact/M_WaterBoatContact.uasset',backup/'M_WaterBoatContact.uasset')
foam=next(e for e in MaterialTools.get_expressions(m) if e.get_editor_property('desc')=='BoatRippleFoam')
code=foam.get_editor_property('code');(backup/'foam-before.hlsl').write_text(code)
old='return max(max(live, trail), contactFoam) * forwardFoamGate;'
new='return max(max(live, trail), contactFoam * forwardFoamGate);'
assert old in code or new in code or 'return max(live, trail);' in code,'Unexpected foam shader; preserve other edits'
code=code.replace('// Fluid waves propagate both ways; boat foam belongs at the hull and behind it.', '// Only new hull contact is bow-gated. World-space history and propagating waves survive turns.')
foam.set_editor_property('code',code.replace(old,new))
m.modify();MaterialTools.recompile(m)
assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
print('FOAM_TURN_CUT_FIXED',str(backup))

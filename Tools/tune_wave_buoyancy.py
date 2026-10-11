"""Editor only: give the small-wave boat reserve lift while retaining a submerged keel."""
import json
import re
from pathlib import Path
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_name() == 'M_WaterSmallWavesTest'
assert not unreal.EditorLevelLibrary.get_game_world(), 'Stop PIE before editing'
boat = next(a for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
            if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C')
buoyancy = boat.get_component_by_class(unreal.BuoyancyComponent)
state = json.loads(unreal.ToolsetLibrary.get_object_properties(buoyancy, ['BuoyancyData']))
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-foam-blend/small-wave-buoyancy.json'
if not backup.exists():
    backup.write_text(json.dumps(state, indent=2))
data = buoyancy.get_editor_property('buoyancy_data')
text = re.sub(r'BuoyancyCoefficient=[^,)]*', 'BuoyancyCoefficient=1.6', data.export_text())
# Raise virtual float centres to compensate for extra lift at the resting waterline.
text = re.sub(r'(RelativeLocation=\(X=[^,]+,Y=[^,]+,Z=)[^)]+', r'\g<1>35.0', text)
buoyancy.modify()
assert data.import_text(text)
actual = buoyancy.get_editor_property('buoyancy_data')
assert abs(actual.get_editor_property('buoyancy_coefficient') - 1.6) < .001
assert all(p.relative_location.z == 35 for p in actual.pontoons)
print('WAVE_RESERVE_SET_UNSAVED')

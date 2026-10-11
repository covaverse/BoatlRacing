"""Editor Python before PIE: restore hull-matched draft on all water test maps."""
import json
import shutil
from pathlib import Path
import unreal

path = '/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling'
asset = unreal.load_asset(path)
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-water-contact/handling-before-draft.uasset'
if not backup.exists():
    shutil.copy2(Path(unreal.Paths.project_content_dir()) / (path[6:] + '.uasset'), backup)
asset.modify()
assert unreal.ToolsetLibrary.set_object_properties(asset, json.dumps({
    'FrontPontoonRadiusCm': 60, 'RearPontoonRadiusCm': 55}))
assert unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
print('BOAT_DRAFT_PROFILE_SAVED', 60, 55)

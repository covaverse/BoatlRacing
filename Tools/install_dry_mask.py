"""Editor Python: replace rendering distance field without changing the collision hull."""
import shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools

path = '/Game/Boats/ThaiLongtail/Physics/SM_BoatDryCavity'
task = unreal.AssetImportTask()
task.set_editor_property('filename', str(Path(unreal.Paths.project_dir()) / 'SourceAssets/Physics/SM_BoatDryCavity.obj'))
task.set_editor_property('destination_path', '/Game/Boats/ThaiLongtail/Physics')
task.set_editor_property('destination_name', 'SM_BoatDryCavity')
task.set_editor_property('automated', True)
task.set_editor_property('save', True)
task.set_editor_property('replace_existing', True)
options = unreal.FbxImportUI()
options.set_editor_property('automated_import_should_detect_type', False)
options.set_editor_property('import_as_skeletal', False)
options.set_editor_property('import_materials', False)
options.set_editor_property('import_textures', False)
options.static_mesh_import_data.set_editor_property('convert_scene', False)
options.static_mesh_import_data.set_editor_property('combine_meshes', True)
task.set_editor_property('options', options)
unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
mask = unreal.load_asset(path)
assert isinstance(mask, unreal.StaticMesh)
bounds = mask.get_bounds()
assert abs(bounds.origin.x - 35.5) < 1 and bounds.box_extent.x > 260, bounds
assert bounds.box_extent.y < 55 and 15 < bounds.origin.z < 65, bounds
hull_path = '/Game/Boats/ThaiLongtail/Physics/SM_BoatPhysicsHull'
backup = Path(unreal.Paths.project_saved_dir()) / 'Backups/2026-10-02-water-contact/hull-before-dry-field.uasset'
if not backup.exists():
    shutil.copy2(Path(unreal.Paths.project_content_dir()) / (hull_path[6:] + '.uasset'), backup)
hull = unreal.load_asset(hull_path)
editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
settings = editor.get_lod_build_settings(hull, 0)
settings.set_editor_property('distance_field_replacement_mesh', mask)
settings.set_editor_property('distance_field_resolution_scale', 4)
editor.set_lod_build_settings(hull, 0, settings)
assert unreal.EditorAssetLibrary.save_asset(hull_path, only_if_is_dirty=False)
material = unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
edge = next(e for e in MaterialTools.get_expressions(material) if isinstance(e, unreal.MaterialExpressionIf))
edge.set_editor_property('const_b', -.5)
material.modify()
unreal.MaterialEditingLibrary.recompile_material(material)
assert unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
print('BOAT_FITTED_DRY_FIELD_INSTALLED', bounds)

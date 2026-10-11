import unreal,json,datetime,shutil
from pathlib import Path
folder='/Game/Water/Materials/BoatContact/'
mi=unreal.load_asset(folder+'MI_WaterBoatOcean')
root=Path(unreal.Paths.project_dir());assets=unreal.EditorAssetLibrary
assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-water-wall')
backup.mkdir(parents=True)
assert assets.save_loaded_asset(mi,only_if_is_dirty=False)
shutil.copy2(root/'Content/Water/Materials/BoatContact/MI_WaterBoatOcean.uasset',backup/'MI_WaterBoatOcean.uasset')
values={'Fluid Displacement Multiplier':3.,'Max Fluid Displacement':40.,'Fluidsim Flow Density':.25,'Fluidsim Normal Strength':.70}
for n,v in values.items():
 unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi,n,v)
 assert abs(unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi,n)-v)<.001
unreal.MaterialEditingLibrary.update_material_instance(mi)
assert assets.save_loaded_asset(mi,only_if_is_dirty=False)
w=unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
rows=[]
for a in unreal.GameplayStatics.get_all_actors_of_class(w,unreal.WaterBody):
 for c in a.get_components_by_class(unreal.WaterBodyComponent):
  mat=c.get_editor_property('WaterMaterial')
  mid=c.get_water_material_instance()
  rows.append({'actor':a.get_actor_label(),'water_material':mat.get_path_name() if mat else None,'mid':mid.get_path_name() if mid else None,'values':{n:mid.get_scalar_parameter_value(n) for n in values} if mid else {}})
  if mat==mi:assert all(abs(mid.get_scalar_parameter_value(n)-v)<.001 for n,v in values.items()),rows
(Path(unreal.Paths.project_saved_dir())/'Automation/BoatContact/water-wall-check.json').write_text(json.dumps(rows,indent=2))
print('WATER_WALL_SETTINGS_AND_RENDER_MID_PASS',rows,str(backup))

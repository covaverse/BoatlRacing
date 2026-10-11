"""Editor Python: route simulated water height and normals to the rendered surface."""
import datetime,shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
root=Path(unreal.Paths.project_dir())
assert not unreal.EditorLevelLibrary.get_game_world()
m=unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
backup=root/'Saved/Backups'/(datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-dynamic-surface')
backup.mkdir(parents=True)
unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
shutil.copy2(root/'Content/Water/Materials/BoatContact/M_WaterBoatContact.uasset',backup/'M_WaterBoatContact.uasset')
expressions=MaterialTools.get_expressions(m)
fluid=next(e for e in expressions if isinstance(e,unreal.MaterialExpressionMaterialFunctionCall) and e.get_editor_property('material_function').get_name()=='SampleFluidSimulation')
final=next(e for e in expressions if isinstance(e,unreal.MaterialExpressionMakeMaterialAttributes))
after=next((e for e in expressions if e.get_editor_property('desc')=='DynamicWaterSurface'),None)
if not after:
 after=unreal.MaterialEditingLibrary.create_material_expression(m,unreal.MaterialExpressionBreakMaterialAttributes,2200,700)
 after.set_editor_property('desc','DynamicWaterSurface')
assert unreal.MaterialEditingLibrary.connect_material_expressions(fluid,'Attributes',after,'Attr')
for pin in ('WorldPositionOffset','Normal'):
 assert unreal.MaterialEditingLibrary.connect_material_expressions(after,pin,final,pin)
m.modify()
MaterialTools.recompile(m)
assert unreal.EditorAssetLibrary.save_loaded_asset(m,only_if_is_dirty=False)
print('DYNAMIC_WATER_SURFACE_SAVED',str(backup))

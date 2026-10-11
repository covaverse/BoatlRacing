"""Run in Editor Python before PIE; tune the existing water and duplicate spray."""
import json
import unreal
from pathlib import Path

root = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
root.mkdir(parents=True, exist_ok=True)
assets = unreal.EditorAssetLibrary
spray = '/Game/Boats/ThaiLongtail/FX/NS_LongtailBowSplash'
if not assets.does_asset_exist(spray):
    assert assets.duplicate_asset('/Game/Boats/ThaiLongtail/FX/NS_LongtailPropSpray', spray)
assert assets.save_asset(spray)
system = unreal.load_asset(spray)
bp_path = '/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn'
bp = unreal.load_asset(bp_path)
subobjects = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
library = unreal.SubobjectDataBlueprintFunctionLibrary
templates = {}
for handle in subobjects.k2_gather_subobject_data_for_blueprint(bp):
    data = library.get_data(handle)
    obj = library.get_object_for_blueprint(data, bp)
    if isinstance(obj, unreal.NiagaraComponent) and obj.get_name().startswith('BowSplashFX'):
        templates[obj.get_path_name()] = obj
assert len(templates) == 1, list(templates)
template = next(iter(templates.values()))
template.modify()
template.set_editor_property('asset', system)
bp.modify()
unreal.BlueprintEditorLibrary.compile_blueprint(bp)
assert assets.save_asset(bp_path, only_if_is_dirty=False)
for name in ('M_WaterPhysicsTest', 'M_WaterSmallWavesTest', 'M_WaterHighWavesTest'):
    assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/' + name)
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    boats = [a for a in actors if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C']
    assert len(boats) == 1
    bow = boats[0].get_editor_property('BowSplashFX')
    prop = boats[0].get_editor_property('PropSprayFX')
    bow.set_editor_property('asset', system)
    assert bow.get_asset() == system
    assert prop.get_asset().get_name() == 'NS_LongtailPropSpray'
    sims = [a for a in actors if a.get_class().get_name() == 'BP_FluidSim_01_C']
    assert len(sims) == 1
    sim = sims[0]
    assert unreal.ToolsetLibrary.set_object_properties(sim, json.dumps({
        'Resolution': 1024, 'Simulate Wave Foam': False}))
    zones = [a for a in actors if isinstance(a, unreal.WaterZone)]
    for zone in zones:
        mesh = zone.get_component_by_class(unreal.WaterMeshComponent)
        mesh.set_editor_property('tessellation_factor', 9)
    assert unreal.EditorLoadingAndSavingUtils.save_current_level()
    print('BOAT_WATER_DETAIL_SAVED', name)
assert unreal.EditorLoadingAndSavingUtils.load_map('/Game/Maps/M_WaterPhysicsTest')
mi = unreal.load_asset('/Game/Water/Materials/BoatContact/MI_WaterBoatOcean')
names = unreal.MaterialEditingLibrary.get_scalar_parameter_names(mi)
values = {str(n): unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(mi, n)
          for n in names if any(s in str(n).lower() for s in ('foam', 'fluid', 'normal', 'detail'))}
(root / 'water-detail-parameters.json').write_text(json.dumps(values, indent=2))
print('BOAT_WATER_DETAIL_PREP_PASS')

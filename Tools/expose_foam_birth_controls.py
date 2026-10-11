"""Use an editable instance for wave-driven foam generation."""
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
folder = '/Game/Water/Materials/BoatContact/'
parent = unreal.load_asset(folder + 'M_BoatFoamComposite')
path = folder + 'MI_BoatFoamComposite'
assets = unreal.EditorAssetLibrary
if assets.does_asset_exist(path):
    mi = unreal.load_asset(path)
else:
    mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset('MI_BoatFoamComposite', folder.rstrip('/'), unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    unreal.MaterialEditingLibrary.set_material_instance_parent(mi, parent)
    unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(mi, 'FoamBreakingThreshold', .12)

descriptions = {
    'Birth': 'ปริมาณฟองที่เพิ่มต่อวินาทีเมื่อคลื่นแตก; น้ำเรียบยังไม่สร้างฟอง. Foam birth per second at disturbed crests.',
    'Decay': 'อัตราจางต่อวินาที: เพิ่ม = หายเร็ว / ลด = รอยฟองอยู่นาน. Foam density decay per second.',
    'Diffusion': 'ความนุ่มของรอยฟอง: เพิ่ม = กระจาย/เบลอมากขึ้น. Foam diffusion in capture UV.',
    'NoiseAmount': 'การหมุนวนของรอยฟอง: เพิ่ม = รอยโค้ง/แตกมากขึ้น. Noise-driven drift in capture UV.',
    'SurfaceFlowCmPerSec': 'ทิศและความเร็วการไหลของฟองใน world XY หน่วย ซม./วินาที. Surface flow XY in cm/s.',
}
for e in MaterialTools.get_expressions(parent):
    if isinstance(e, (unreal.MaterialExpressionScalarParameter, unreal.MaterialExpressionVectorParameter)):
        name = str(e.get_editor_property('parameter_name'))
        if name in descriptions:
            e.set_editor_property('desc', descriptions[name])
            e.set_editor_property('group', 'Foam Transport' if name != 'Birth' else 'Foam Birth')
MaterialTools.recompile(parent)
unreal.MaterialEditingLibrary.update_material_instance(mi)
assert assets.save_loaded_asset(parent, only_if_is_dirty=False)
assert assets.save_loaded_asset(mi, only_if_is_dirty=False)
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
graph = BlueprintTools.get_graph(bp, 'SetupFoamCapture')
editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
for node in BlueprintTools.get_node_infos(list(editor.list_all_nodes())):
    for pin in node.input_pins:
        if folder + 'M_BoatFoamComposite.M_BoatFoamComposite' in pin.value:
            BlueprintTools.set_pin_value(pin.pin_id, path + '.MI_BoatFoamComposite')
            assert 'MI_BoatFoamComposite' in BlueprintTools.get_pin_value(pin.pin_id)
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
actual = BlueprintTools.read_graph_dsl(graph)
assert 'MI_BoatFoamComposite' in actual
assert assets.save_loaded_asset(bp, only_if_is_dirty=False)
print('FOAM_BIRTH_INSTANCE_SAVED', path)

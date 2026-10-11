"""Editor GPU check: pressure pushes water outwards, rotates with the hull, and stops when dry/idle."""
import json
from pathlib import Path
import unreal

world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
collection = unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
names = ('Origin', 'AxisX', 'AxisY', 'AxisZ')
old = {name: unreal.MaterialLibrary.get_vector_parameter_value(world, collection, name) for name in names}
material = unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatHullFluidForce')
mid = unreal.MaterialLibrary.create_dynamic_material_instance(world, material)
rt = unreal.RenderingLibrary.create_render_target2d(world, 128, 128, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
results = []
try:
    for label, yaw, z, force in [('straight', 0, 375, -.03), ('turn', 90, 375, -.03),
                                  ('keel_contact', 0, 410, -.03), ('dry', 0, 600, -.03), ('idle', 0, 375, 0)]:
        rotation = unreal.Rotator(pitch=0, yaw=yaw, roll=0)
        x = unreal.MathLibrary.get_forward_vector(rotation)
        y = unreal.MathLibrary.get_right_vector(rotation)
        values = [unreal.LinearColor(0, 0, z, 1), unreal.LinearColor(x.x, x.y, x.z, 0),
                  unreal.LinearColor(y.x, y.y, y.z, 0), unreal.LinearColor(0, 0, 1, 400)]
        for name, value in zip(names, values):
            unreal.MaterialLibrary.set_vector_parameter_value(world, collection, name, value)
        mid.set_scalar_parameter_value('F', force)
        unreal.RenderingLibrary.clear_render_target2d(world, rt)
        unreal.RenderingLibrary.draw_material_to_render_target(world, rt, mid)
        samples = unreal.RenderingLibrary.read_render_target_raw(world, rt, False)
        if isinstance(samples, tuple):
            samples = next(item for item in samples if not isinstance(item, bool))
        heights = [c.r for c in samples]
        def sample(x, y):
            return heights[int((y / 720 + .5) * 128) * 128 + int((x / 720 + .5) * 128)]
        if label in ('dry', 'idle'):
            assert max(abs(v) for v in heights) < .00001, label
        else:
            assert sample(0, 0) < -.02, (label, 'under hull', sample(0, 0))
            bank = sample(0, 45) if yaw == 0 else sample(45, 0)
            assert bank > .001, (label, 'outside bank', bank)
            assert (sample(150, 0) if yaw == 0 else sample(0, 150)) < -.01, label
            assert abs(sample(0, 150) if yaw == 0 else sample(150, 0)) < .00001, label
        results.append(dict(case=label, minimum=min(heights), maximum=max(heights)))
finally:
    for name, value in old.items():
        unreal.MaterialLibrary.set_vector_parameter_value(world, collection, name, value)
    unreal.RenderingLibrary.release_render_target2d(rt)
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
(folder / 'hull-pressure-gpu-check.json').write_text(json.dumps(results, indent=2))
print('BOAT_HULL_PRESSURE_GPU_PASS', results)

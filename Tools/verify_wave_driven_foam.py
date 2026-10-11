"""GPU check: actual wave normals gate foam birth, while old foam survives."""
import json
from pathlib import Path
import unreal


def verify():
    world = unreal.load_object(None, '/Game/Maps/M_WaterPhysicsTest.M_WaterPhysicsTest')
    assert world and 'UEDPIE' not in world.get_path_name()
    ml, rl = unreal.MaterialLibrary, unreal.RenderingLibrary
    boat_mpc = unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
    water_mpc = unreal.load_asset('/Water/Materials/MPC/MPC_Water')
    names = ('Origin', 'AxisX', 'AxisY', 'AxisZ', 'FoamFrame', 'FoamShift')
    previous = {n: ml.get_vector_parameter_value(world, boat_mpc, n) for n in names}
    old_location = ml.get_vector_parameter_value(world, water_mpc, 'SimLocation')
    old_size = ml.get_scalar_parameter_value(world, water_mpc, 'FluidSimSize')
    fallback = unreal.load_asset('/Engine/EngineResources/Black')
    material = unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatFoamComposite')
    mid = ml.create_dynamic_material_instance(world, material, creation_flags=unreal.MIDCreationFlags.TRANSIENT)
    copy = ml.create_dynamic_material_instance(world, unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatFoamCopy'), creation_flags=unreal.MIDCreationFlags.TRANSIENT)
    targets = [rl.create_render_target2d(world, 256, 256, unreal.TextureRenderTargetFormat.RTF_RGBA16F) for _ in range(2)]
    wave = rl.create_render_target2d(world, 4, 4, unreal.TextureRenderTargetFormat.RTF_RGBA16F)
    rt, buffer = targets
    rows = []

    def publish(name, color):
        ml.set_vector_parameter_value(world, boat_mpc, name, color)

    def sample(x, y):
        return rl.read_render_target_raw_pixel(world, rt, int((x + 2048) / 16), int((y + 2048) / 16), False).r

    def step():
        copy.set_texture_parameter_value('Source', rt)
        rl.draw_material_to_render_target(world, buffer, copy)
        rl.draw_material_to_render_target(world, rt, mid)

    try:
        mid.set_texture_parameter_value('FoamBuffer', buffer)
        mid.set_texture_parameter_value('WaveNormalHeight', wave)
        mid.set_scalar_parameter_value('NoiseAmount', 0)
        mid.set_scalar_parameter_value('Birth', 2)
        mid.set_scalar_parameter_value('Decay', .1)
        mid.set_vector_parameter_value('SurfaceFlowCmPerSec', unreal.LinearColor(0, 0, 0, 0))
        for n, v in zip(names, [unreal.LinearColor(0, 0, 0, 1), unreal.LinearColor(1, 0, 0, 1), unreal.LinearColor(0, 1, 0, .1), unreal.LinearColor(0, 0, 1, 25), unreal.LinearColor(-2048, -2048, 4096, 0), unreal.LinearColor(0, 0, 0, 0)]):
            publish(n, v)
        ml.set_vector_parameter_value(world, water_mpc, 'SimLocation', unreal.LinearColor(0, 0, 0, 0))
        ml.set_scalar_parameter_value(world, water_mpc, 'FluidSimSize', 4096)
        for label, normal, height, speed in [('flat', 0, 0, 1), ('high_flat', 0, 8, 1), ('breaking_crest', .4, 8, 1), ('trough', .4, -8, 1), ('stopped', .4, 8, 0)]:
            rl.clear_render_target2d(world, rt)
            rl.clear_render_target2d(world, buffer)
            rl.clear_render_target2d(world, wave, unreal.LinearColor(normal, 0, height, 1))
            publish('AxisX', unreal.LinearColor(1, 0, 0, speed))
            step()
            aft, bow = sample(200, 128), sample(-260, 20)
            assert bow < .001, (label, bow)
            assert aft > .1 if label == 'breaking_crest' else aft < .001, (label, aft)
            rows.append(dict(case=label, aft=aft, ahead=bow))
        publish('AxisX', unreal.LinearColor(1, 0, 0, 1))
        rl.clear_render_target2d(world, wave, unreal.LinearColor(.4, 0, 8, 1))
        for _ in range(5):
            step()
        start = sample(200, 128)
        rl.clear_render_target2d(world, wave)
        publish('AxisX', unreal.LinearColor(0, 1, 0, 0))
        publish('AxisY', unreal.LinearColor(-1, 0, 0, .1))
        step()
        turned = sample(200, 128)
        assert turned > .1, (start, turned)
        for _ in range(10):
            step()
        faded = sample(200, 128)
        assert 0 < faded < turned, (start, turned, faded)
        rows.append(dict(case='history_turn_and_fade', initial=start, turned=turned, faded=faded))
    finally:
        for n, v in previous.items():
            publish(n, v)
        ml.set_vector_parameter_value(world, water_mpc, 'SimLocation', old_location)
        ml.set_scalar_parameter_value(world, water_mpc, 'FluidSimSize', old_size)
        mid.set_texture_parameter_value('FoamBuffer', fallback)
        mid.set_texture_parameter_value('WaveNormalHeight', fallback)
        copy.set_texture_parameter_value('Source', fallback)
        for target in targets + [wave]:
            rl.release_render_target2d(target)
    (Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact/wave-driven-foam-check.json').write_text(json.dumps(rows, indent=2))
    print('WAVE_DRIVEN_FOAM_GPU_PASS', rows)


verify()

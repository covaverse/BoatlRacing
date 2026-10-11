"""Editor Python during PIE: verify stopped spray and actual GPU foam decay."""
import json
from pathlib import Path
import unreal

world = unreal.EditorLevelLibrary.get_game_world()
assert world and 'UEDPIE' in world.get_path_name(), 'Start PIE first'
boat = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C')
hull = boat.get_editor_property('StaticMesh')
buoyancy = boat.get_editor_property('Buoyancy')
collection = unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
old_tick = boat.is_actor_tick_enabled()
old_buoyancy_tick = buoyancy.is_component_tick_enabled()
old_velocity = hull.get_component_velocity()
boat.set_actor_tick_enabled(False)
buoyancy.set_component_tick_enabled(False)
results = {}
try:
    for speed in (1600, 0):
        hull.set_physics_linear_velocity(unreal.Vector(-speed, 0, 0), False)
        boat.call_method('UpdateShaftState', (.1,))
        boat.call_method('UpdateFXState_0')
        boat.call_method('UpdateSideSpray', (.1,))
        rates = {name: boat.get_editor_property(name).get_variable_float('SpawnRate')[0]
                 for name in ('BowSplashFX', 'SideSprayFX', 'SprayMistFX', 'WakeFX')}
        if not speed:
            assert all(rate == 0 for rate in rates.values()), rates
        else:
            assert rates['SideSprayFX'] > 0 and rates['SprayMistFX'] > 0, rates
        results[str(speed)] = rates

    # Publish fixed dt for this controlled GPU test, keeping the real hull frame.
    x = unreal.MaterialLibrary.get_vector_parameter_value(world, collection, 'AxisX')
    y = unreal.MaterialLibrary.get_vector_parameter_value(world, collection, 'AxisY')
    unreal.MaterialLibrary.set_vector_parameter_value(world, collection, 'AxisX',
        unreal.LinearColor(x.r, x.g, x.b, 1))
    unreal.MaterialLibrary.set_vector_parameter_value(world, collection, 'AxisY',
        unreal.LinearColor(y.r, y.g, y.b, .1))
    rt = boat.get_editor_property('FoamRT')
    # The single-pixel reader expects RGBA; convert the R16f foam before sampling.
    probe = unreal.RenderingLibrary.create_render_target2d(world, rt.size_x, rt.size_y,
        unreal.TextureRenderTargetFormat.RTF_RGBA16F, unreal.LinearColor(0, 0, 0, 0))
    unreal.RenderingLibrary.clear_render_target2d(world, rt, unreal.LinearColor(0, 0, 0, 0))
    for _ in range(20):
        boat.call_method('UpdateFoamCapture', (.1,))
    frame = unreal.MaterialLibrary.get_vector_parameter_value(world, collection, 'FoamFrame')
    origin = unreal.MaterialLibrary.get_vector_parameter_value(world, collection, 'Origin')
    # Sample both V wings at three stations, in the shader's local hull frame.
    points = []
    for aft, width in ((0, 78), (200, 128), (400, 178)):
        for side in (-1, 1):
            px = origin.r + x.r * aft + y.r * width * side
            py = origin.g + x.g * aft + y.g * width * side
            points.append((int((px - frame.r) / frame.b * rt.size_x),
                           int((py - frame.g) / frame.b * rt.size_y)))

    def sample():
        copy_mid = boat.get_editor_property('FoamCopyMID')
        copy_mid.set_texture_parameter_value('Source', rt)
        unreal.RenderingLibrary.draw_material_to_render_target(world, probe, copy_mid)
        assert unreal.RenderingLibrary.read_render_target_raw_pixel(world, probe, 0, 0, False).r < .01
        return max(unreal.RenderingLibrary.read_render_target_raw_pixel(world, probe, px, py, False).r
                   for px, py in points)

    levels = [sample()]
    assert levels[0] > .05, ('Foam was not rendered', levels)
    unreal.MaterialLibrary.set_vector_parameter_value(world, collection, 'AxisX',
        unreal.LinearColor(x.r, x.g, x.b, 0))
    for _ in range(35):
        boat.call_method('UpdateFoamCapture', (.1,))
        levels.append(sample())
    assert all(b <= a + .002 for a, b in zip(levels, levels[1:])), levels
    assert levels[5] > .05 and levels[15] > .01 and levels[-1] < .01, levels
    results['foam_decay_0_0.5_1.5_3.5_seconds'] = [levels[i] for i in (0, 5, 15, 35)]
finally:
    hull.set_physics_linear_velocity(old_velocity, False)
    buoyancy.set_component_tick_enabled(old_buoyancy_tick)
    boat.set_actor_tick_enabled(old_tick)

folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
folder.mkdir(parents=True, exist_ok=True)
(folder / 'v-foam-check.json').write_text(json.dumps(results, indent=2))
print('BOAT_V_FOAM_AND_STOP_PASS', json.dumps(results))

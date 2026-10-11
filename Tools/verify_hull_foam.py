"""PIE check: visual hull frame, stationary rates, measured contact, wind drift and fade."""
import json
from pathlib import Path
import unreal

world = unreal.EditorLevelLibrary.get_game_world()
assert world and 'UEDPIE' in world.get_path_name(), 'Run during PIE'
boat = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C')
hull = boat.get_editor_property('StaticMesh')
visual = boat.get_editor_property('BoatVisual')
collection = unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame')
ml = unreal.MaterialLibrary
rl = unreal.RenderingLibrary
names = ('Origin', 'AxisX', 'AxisY', 'AxisZ', 'FoamFrame', 'FoamShift')
old = {n: ml.get_vector_parameter_value(world, collection, n) for n in names}
velocity = hull.get_component_velocity()
rotation = visual.get_editor_property('relative_rotation')
results = {}

def publish(name, r, g, b, a=0):
    ml.set_vector_parameter_value(world, collection, name, unreal.LinearColor(r, g, b, a))

try:
    visual.set_relative_rotation(unreal.Rotator(pitch=8, yaw=12, roll=3), False, True)
    boat.call_method('UpdateFXState_0')
    axis = ml.get_vector_parameter_value(world, collection, 'AxisX')
    expected = visual.get_forward_vector()
    assert max(abs(axis.r - expected.x), abs(axis.g - expected.y), abs(axis.b - expected.z)) < 1e-4
    results['visual_frame_follows_trim'] = True
    visual.set_relative_rotation(rotation, False, True)
    for speed in (1600, 0):
        hull.set_physics_linear_velocity(unreal.Vector(-speed, 0, 0), False)
        boat.call_method('UpdateShaftState', (.1,))
        boat.call_method('UpdateFXState_0')
        boat.call_method('UpdateSideSpray', (.1,))
        water_z = boat.get_editor_property('WaterSurfaceZ')
        for name in ('SideSprayFX', 'SprayMistFX'):
            fx = boat.get_editor_property(name)
            assert abs(fx.get_world_location().z - water_z - 2) < .01, (name, fx.get_world_location(), water_z)
            assert abs(fx.get_world_rotation().pitch) < .01 and abs(fx.get_world_rotation().roll) < .01
        rates = {n: boat.get_editor_property(n).get_variable_float('SpawnRate')[0]
                 for n in ('BowSplashFX', 'SideSprayFX', 'SprayMistFX', 'WakeFX')}
        assert (all(v == 0 for v in rates.values()) if speed == 0 else rates['SideSprayFX'] > 0), rates
        assert rates['BowSplashFX'] <= 1000
        results['rates_' + str(speed)] = rates
        results['side_spray_on_water_surface'] = True
        if not speed:
            for _ in range(30):
                boat.call_method('ApplyVisualTrim', (.1,))
            frame = visual.get_world_transform()
            bow = unreal.MathLibrary.transform_location(frame, unreal.Vector(-200, 0, 0))
            stern = unreal.MathLibrary.transform_location(frame, unreal.Vector(200, 0, 0))
            assert bow.z - stern.z > 15, ('Stern must sit below bow', bow, stern)
            results['visual_stern_below_bow_cm'] = bow.z - stern.z

    material = unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatFoamComposite')
    composite = ml.create_dynamic_material_instance(world, material)
    copy = ml.create_dynamic_material_instance(world, unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatFoamCopy'))
    targets = [rl.create_render_target2d(world, 1024, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA16F,
               unreal.LinearColor(0, 0, 0, 0)) for _ in range(2)]
    rt, buffer = targets
    composite.set_texture_parameter_value('FoamBuffer', buffer)
    composite.set_vector_parameter_value('SurfaceFlowCmPerSec', unreal.LinearColor(0, 0, 0, 0))
    composite.set_scalar_parameter_value('NoiseAmount', 0)
    publish('Origin', 0, 0, 0, 1)
    publish('AxisX', 1, 0, 0, 1)
    publish('AxisY', 0, 1, 0, .1)
    publish('AxisZ', 0, 0, 1, 25.5)
    publish('FoamFrame', -2048, -2048, 4096)
    publish('FoamShift', 0, 0, 0)

    def step(count=1):
        for _ in range(count):
            copy.set_texture_parameter_value('Source', rt)
            rl.draw_material_to_render_target(world, buffer, copy)
            rl.draw_material_to_render_target(world, rt, composite)

    def sample(x, y):
        return rl.read_render_target_raw_pixel(world, rt, int((x + 2048) / 4), int((y + 2048) / 4), False).r

    step()
    contact = [sample(-219.5, side * 15.5) for side in (-1, 1)]
    assert min(contact) > .07, contact
    assert max(sample(200, side * 128) for side in (-1, 1)) < .005, 'Old rigid V still being born'
    assert sample(-400, 0) < .005, 'Foam ahead of the hull'
    results['both_bow_contact_pixels'] = contact
    step(19)
    # A turn adds foam at the new pose while retaining world-space history.
    before = sample(-220, 16)
    publish('Origin', -120, 120, 0, 1)
    publish('AxisX', .70710678, .70710678, 0, 1)
    publish('AxisY', -.70710678, .70710678, 0, .1)
    step()
    assert sample(-220, 16) > before * .6, 'History rotated with the boat'
    assert sample(-120 - 220 * .707 - 16 * .707, 120 - 220 * .707 + 16 * .707) > .04
    results['turn_retains_history'] = True
    # Controlled wind: no new birth, transport 40 cm sideways in half a second.
    for target in targets:
        rl.clear_render_target2d(world, target, unreal.LinearColor(0, 0, 0, 0))
    publish('Origin', 0, 0, 0, 1)
    publish('AxisX', 1, 0, 0, 1)
    publish('AxisY', 0, 1, 0, .1)
    step(20)
    publish('AxisX', 1, 0, 0, 0)
    composite.set_vector_parameter_value('SurfaceFlowCmPerSec', unreal.LinearColor(0, 80, 0, 0))

    def centroid():
        row = [(y, sample(0, y)) for y in range(-160, 164, 4)]
        mass = sum(v for _, v in row)
        assert mass > .01
        return sum(y * v for y, v in row) / mass

    start = centroid()
    step(5)
    drift = centroid() - start
    assert 32 < drift < 48, drift
    results['wind_drift_cm_in_half_second'] = drift
    composite.set_vector_parameter_value('SurfaceFlowCmPerSec', unreal.LinearColor(0, 0, 0, 0))
    level = max(sample(0, y) for y in range(-40, 120, 4))
    assert level > .05, 'Foam vanished instantly at stop'
    step(55)
    final = max(sample(0, y) for y in range(-80, 160, 4))
    assert final < .005, final
    results['fade_half_second_and_six_seconds'] = [level, final]
finally:
    visual.set_relative_rotation(rotation, False, True)
    hull.set_physics_linear_velocity(velocity, False)
    boat.call_method('UpdateShaftState', (.1,))
    for name, value in old.items():
        ml.set_vector_parameter_value(world, collection, name, value)

path = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact/hull-foam-check.json'
path.write_text(json.dumps(results, indent=2))
print('HULL_FOAM_CONTACT_TURN_WIND_FADE_PASS', json.dumps(results))

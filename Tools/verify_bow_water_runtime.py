"""Run in PIE on the flat map; exercises the actual Blueprint at controlled speeds."""
import json
import unreal
from pathlib import Path

prefix = '/Game/Maps/UEDPIE_0_M_WaterPhysicsTest.M_WaterPhysicsTest:PersistentLevel.'
boat = unreal.load_object(None, prefix + 'BP_LongtailPhysicsPawn_C_0')
assert boat
hull = boat.get_editor_property('StaticMesh')
buoyancy = boat.get_editor_property('Buoyancy')
spray = boat.get_editor_property('BowSplashFX')
old_location = boat.get_actor_location()
old_velocity = hull.get_component_velocity()
old_tick = boat.is_actor_tick_enabled()
boat.set_actor_tick_enabled(False)
buoyancy.set_component_tick_enabled(False)
results = []
try:
    for speed, z in [(0, 400), (10, 400), (30, 400), (100, 400),
                     (800, 400), (1600, 400), (2400, 400), (800, 650)]:
        boat.set_actor_location(unreal.Vector(old_location.x, old_location.y, z), False, True)
        hull.set_physics_linear_velocity(unreal.Vector(-speed, 0, 0), False)
        boat.call_method('UpdateFXState_0')
        rate, valid = spray.get_variable_float('SpawnRate')
        launch, _ = spray.get_variable_float('SpraySpeed')
        spread, _ = spray.get_variable_float('SpraySpread')
        alpha = min(speed / 1600, 1)
        expected = 130 * alpha if speed > 80 and z == 400 else 0
        assert valid and abs(rate - expected) < .01, (speed, z, rate, expected)
        assert spray.get_editor_property('visible') == (expected > 0), (speed, z)
        assert abs(launch - (60 + 380 * alpha)) < .01, (speed, launch)
        assert abs(spread - (25 + 45 * alpha)) < .01, (speed, spread)
        results.append(dict(speed=speed, z=z, rate_per_side=rate, launch=launch, spread=spread))
finally:
    boat.set_actor_location(old_location, False, True)
    hull.set_physics_linear_velocity(old_velocity, False)
    buoyancy.set_component_tick_enabled(True)
    boat.set_actor_tick_enabled(old_tick)
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
(folder / 'bow-branches.json').write_text(json.dumps(results, indent=2))
print('BOAT_BOW_CONTACT_SPEED_BRANCHES_PASS')

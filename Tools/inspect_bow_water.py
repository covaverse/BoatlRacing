"""Run in PIE: record actual bow spray parameters."""
import json
import unreal
from pathlib import Path

prefix = '/Game/Maps/UEDPIE_0_M_WaterPhysicsTest.M_WaterPhysicsTest:PersistentLevel.'
boat = unreal.load_object(None, prefix + 'BP_LongtailPhysicsPawn_C_0')
assert boat
spray = boat.get_editor_property('BowSplashFX')
velocity = boat.get_editor_property('StaticMesh').get_component_velocity()
speed = (velocity.x ** 2 + velocity.y ** 2) ** .5
rate, valid = spray.get_variable_float('SpawnRate')
launch, launch_valid = spray.get_variable_float('SpraySpeed')
spread, spread_valid = spray.get_variable_float('SpraySpread')
assert valid and launch_valid and spread_valid
alpha = min(speed / 1600, 1)
assert abs(launch - (60 + 380 * alpha)) < 15, (speed, launch)
assert abs(spread - (25 + 45 * alpha)) < 2, (speed, spread)
assert spray.is_active() and 'NS_LongtailBowSplash' in spray.get_asset().get_path_name()
result = dict(speed=speed, rate=rate, launch=launch, spread=spread,
              active=spray.is_active(), location=str(boat.get_actor_location()))
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
label = globals().pop('BOW_LABEL', 'current')
(folder / ('bow-' + label + '.json')).write_text(json.dumps(result, indent=2))
print('BOAT_BOW_RUNTIME_MEASURED', json.dumps(result))

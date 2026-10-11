"""Editor Python during PIE: inspect rear jet and aim the camera at the stern."""
import json
from pathlib import Path
import unreal

prefix = '/Game/Maps/UEDPIE_0_M_WaterPhysicsTest.M_WaterPhysicsTest:PersistentLevel.'
boat = unreal.load_object(None, prefix + 'BP_LongtailPhysicsPawn_C_0')
assert boat
jet = boat.get_editor_property('PropSprayFX')
rate, valid = jet.get_variable_float('SpawnRate')
speed, _ = jet.get_variable_float('JetSpeed')
spread, _ = jet.get_variable_float('JetSpread')
assert valid and jet.is_active()
result = dict(rpm=boat.get_editor_property('ShaftRPM'), immersion=boat.get_editor_property('PropImmersion'),
              rate=rate, launch=speed, spread=spread, position=str(boat.get_editor_property('PropWorldPosition')))
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
(folder / 'prop-jet-runtime.json').write_text(json.dumps(result, indent=2))
boat.get_editor_property('ChaseBoom').set_component_tick_enabled(False)
transform = boat.get_actor_transform()
eye = unreal.MathLibrary.transform_location(transform, unreal.Vector(1400, -850, 750))
target = unreal.MathLibrary.transform_location(transform, unreal.Vector(200, 0, 0))
camera = boat.get_component_by_class(unreal.CameraComponent)
camera.set_world_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, target), False, True)
print('BOAT_REAR_JET_MEASURED', json.dumps(result))

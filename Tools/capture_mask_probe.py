"""PIE-only controlled draft probe; never saves physics or map overrides."""
import json
from pathlib import Path
import unreal

world = unreal.EditorLevelLibrary.get_game_world()
assert world and 'UEDPIE' in world.get_path_name()
boat = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
            if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C')
boat.set_actor_tick_enabled(False)
boat.get_editor_property('Buoyancy').set_component_tick_enabled(False)
hull = boat.get_editor_property('StaticMesh')
hull.set_simulate_physics(False)
boat.set_actor_location(unreal.Vector(6000, 1500, 365), False, True)
boat.set_actor_rotation(unreal.Rotator(), True)
assert abs(hull.get_world_location().z - 365) < .1
assert not boat.is_actor_tick_enabled() and not hull.is_simulating_physics()
for component in boat.get_components_by_class(unreal.NiagaraComponent):
    component.set_visibility(False, True)
boat.get_editor_property('ChaseBoom').set_component_tick_enabled(False)
eye, target = unreal.Vector(6450, 1260, 750), unreal.Vector(6000, 1500, 390)
boat.get_component_by_class(unreal.CameraComponent).set_world_location_and_rotation(
    eye, unreal.MathLibrary.find_look_at_rotation(eye, target), False, True)
unreal.EditorLevelLibrary.set_level_viewport_camera_info(eye, unreal.MathLibrary.find_look_at_rotation(eye, target))
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
(folder / 'mask-probe.json').write_text(json.dumps(dict(
    world=world.get_path_name(), location=str(hull.get_world_location()),
    tick=boat.is_actor_tick_enabled(), simulating=hull.is_simulating_physics()), indent=2))
unreal.SystemLibrary.execute_console_command(world, 'HighResShot 1280x720 filename="' + str(folder / 'mask-probe.png') + '"')
print('BOAT_CONTROLLED_MASK_PROBE_READY')
def update_probe_frame(delta, boat=boat, world=world):
    active_world = unreal.EditorLevelLibrary.get_game_world()
    if not active_world or active_world != world:
        return
    boat.call_method('UpdateFXState_0')
    if globals().get('MASK_PROBE_DISABLED', False):
        unreal.MaterialLibrary.set_vector_parameter_value(boat,
            unreal.load_asset('/Game/Water/Materials/BoatContact/MPC_BoatContactFrame'),
            'Origin', unreal.LinearColor(0, 0, 0, -100000))
probe_frame_callback = unreal.register_slate_post_tick_callback(update_probe_frame)

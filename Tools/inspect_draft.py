"""Editor Python in PIE: measure the hull waterline without changing physics."""
import json
from pathlib import Path
import unreal

boat = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(
    unreal.EditorLevelLibrary.get_game_world(), unreal.load_class(None,
    '/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn.BP_LongtailPhysicsPawn_C')))
hull = boat.get_editor_property('StaticMesh')
data = boat.get_editor_property('Buoyancy').get_editor_property('buoyancy_data')
result = {'location': str(boat.get_actor_location()), 'rotation': str(boat.get_actor_rotation()),
          'velocity': str(hull.get_component_velocity()), 'mass': hull.get_mass(),
          'com': str(hull.get_center_of_mass()),
          'pontoons': [dict(center=str(p.center_location), radius=p.radius,
                            water=p.water_height, immersion=p.immersion_depth,
                            force=str(p.local_force)) for p in data.pontoons],
          'components': [dict(name=c.get_name(), location=str(c.get_world_location()))
                         for c in boat.get_components_by_class(unreal.SceneComponent)]}
for name in ('EngineRPM', 'ShaftRPM', 'PropImmersion', 'Throttle', 'WaterSurfaceZ'):
    result[name] = boat.get_editor_property(name)
for name in ('BowSplashFX', 'PropSprayFX'):
    component = boat.get_editor_property(name)
    result[name] = component.get_variable_float('SpawnRate')[0]
    result[name + '_user_rate'] = component.get_variable_float('User.SpawnRate')
    result[name + '_asset'] = component.get_asset().get_path_name()
for c in boat.get_components_by_class(unreal.ChildActorComponent):
    child = c.get_editor_property('child_actor')
    if child:
        result['visual'] = [dict(name=m.get_name(), bounds=str(m.get_local_bounds()),
                                transform=str(m.get_world_transform()),
                                asset=m.get_editor_property('static_mesh').get_path_name())
                            for m in child.get_components_by_class(unreal.StaticMeshComponent)
                            if m.get_editor_property('static_mesh') and
                            ('Hull' in m.get_name() or 'Transom' in m.get_name())]
label = globals().pop('DRAFT_LABEL', 'current')
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
(folder / ('draft-' + label + '.json')).write_text(json.dumps(result, indent=2))
view = globals().pop('DRAFT_VIEW', '')
if view in ('side', 'interior'):
    boat.get_editor_property('ChaseBoom').set_component_tick_enabled(False)
    frame = boat.get_actor_transform()
    eye = unreal.MathLibrary.transform_location(frame, unreal.Vector(50, -850, 120) if view == 'side' else unreal.Vector(450, -240, 400))
    target = unreal.MathLibrary.transform_location(frame, unreal.Vector(0, 0, 40))
    camera = boat.get_component_by_class(unreal.CameraComponent)
    camera.set_world_location_and_rotation(eye, unreal.MathLibrary.find_look_at_rotation(eye, target), False, True)
print('BOAT_DRAFT_MEASURED', label, result['location'], result['BowSplashFX'], result['PropSprayFX'])


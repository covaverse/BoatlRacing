"""Run in PIE: sample 12 simulation seconds at rest and 12 underway; restore input."""
import json
import math
from pathlib import Path
import unreal

_wave_world = unreal.EditorLevelLibrary.get_game_world()
assert _wave_world and 'UEDPIE' in _wave_world.get_path_name()
_wave_boat = next(a for a in unreal.GameplayStatics.get_all_actors_of_class(_wave_world, unreal.Actor)
                  if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C')
_wave_buoyancy = _wave_boat.get_component_by_class(unreal.BuoyancyComponent)
_wave_old_input = {n: _wave_boat.get_editor_property(n) for n in ('bUseTestInput', 'TestThrottle')}
_wave_boat.set_editor_property('bUseTestInput', True)
_wave_boat.set_editor_property('TestThrottle', 0.)
_wave_start = unreal.GameplayStatics.get_time_seconds(_wave_world)
_wave_samples = []
_wave_next = 0.

def _wave_tick(_dt):
    global _wave_next
    try:
        elapsed = unreal.GameplayStatics.get_time_seconds(_wave_world) - _wave_start
        if elapsed < _wave_next:
            return
        _wave_next = elapsed + .25
        pos = _wave_boat.get_actor_location()
        rotation = _wave_boat.get_actor_rotation()
        water = unreal.BoatlRacingWaterLibrary.sample_wave_surface(_wave_buoyancy, pos)
        _wave_samples.append(dict(time=elapsed, z=pos.z, pitch=rotation.pitch, roll=rotation.roll,
                                  water=water[0] if water else None,
                                  speed=_wave_boat.get_velocity().length()))
        if elapsed >= 12:
            _wave_boat.set_editor_property('TestThrottle', .35)
        if elapsed < 24:
            return
        unreal.unregister_slate_post_tick_callback(_wave_handle)
        for name, value in _wave_old_input.items():
            _wave_boat.set_editor_property(name, value)
        idle = [s for s in _wave_samples if 2 < s['time'] < 12]
        report = dict(map=_wave_world.get_path_name(), samples=_wave_samples)
        out = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact/wave-response.json'
        out.write_text(json.dumps(report, indent=2))
        assert len(idle) > 10 and all(s['water'] is not None for s in idle)
        assert all(math.isfinite(s['z']) and abs(s['roll']) < 35 and abs(s['pitch']) < 35 for s in _wave_samples)
        assert max(s['water'] for s in idle) - min(s['water'] for s in idle) > 10
        assert max(s['z'] for s in idle) - min(s['z'] for s in idle) > 10
        assert max(s['speed'] for s in _wave_samples if s['time'] > 12) > 100
        print('WAVE_RESPONSE_PASS', len(_wave_samples), 'samples', str(out))
    except Exception:
        unreal.unregister_slate_post_tick_callback(_wave_handle)
        for name, value in _wave_old_input.items():
            if unreal.is_valid(_wave_boat):
                _wave_boat.set_editor_property(name, value)
        raise

_wave_handle = unreal.register_slate_post_tick_callback(_wave_tick)
print('WAVE_RESPONSE_STARTED')

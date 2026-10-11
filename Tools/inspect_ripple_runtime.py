"""Run inside Editor Python during PIE; measures the actual GPU water height field."""
import json
import hashlib
import struct
from pathlib import Path
import unreal

world = unreal.EditorLevelLibrary.get_game_world()
assert world and 'UEDPIE' in world.get_path_name(), 'Start PIE first'
actors = unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
sim = next(a for a in actors if a.get_class().get_name() == 'BP_FluidSim_01_C')
rt = sim.get_editor_property('NormalRT')
assert rt, 'Ripple solver did not allocate NormalRT'
samples = unreal.RenderingLibrary.read_render_target_raw(sim, rt, False)
if isinstance(samples, tuple):
    samples = next(item for item in samples if not isinstance(item, bool))
heights = [color.b for color in samples]
boat = next(a for a in actors if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C')
center = sim.get_editor_property('GridCenter')
width = rt.get_editor_property('size_x')
world_size = sim.get_editor_property('Simulation World Size')
hull = boat.get_actor_location()
prop = boat.get_editor_property('PropWorldPosition')
outside = 0
# Exclude the entire 360 cm hull stamp (plus one frame of motion), and the prop source.
margin = 360 + boat.get_velocity().length() * unreal.GameplayStatics.get_world_delta_seconds(world)
for i, h in enumerate(heights):
    x = center.x + ((i % width)/width - .5)*world_size
    y = center.y + ((i // width)/width - .5)*world_size
    if (x-hull.x)**2+(y-hull.y)**2 > margin**2 and (x-prop.x)**2+(y-prop.y)**2 > 100**2:
        outside += abs(h) > .0001
result = dict(passes=sim.get_editor_property('Passes'),
              texture=rt.get_path_name(), pixels=len(heights),
              min_height=min(heights), max_height=max(heights),
              mean_height=sum(heights)/len(heights),
              nonflat_pixels=sum(abs(h) > .0001 for h in heights),
              outside_source_pixels=outside,
              source_tick_enabled=boat.is_actor_tick_enabled(),
              hash=hashlib.sha256(struct.pack('<%df' % len(heights), *heights)).hexdigest())
folder = Path(unreal.Paths.project_saved_dir()) / 'Automation/BoatContact'
folder.mkdir(parents=True, exist_ok=True)
(folder/'ripple-runtime.json').write_text(json.dumps(result, indent=2))
label = globals().pop('RIPPLE_LABEL', 'current')
(folder/('ripple-'+label+'.json')).write_text(json.dumps(result, indent=2))
unreal.RenderingLibrary.export_render_target(sim, rt, str(folder), 'ripple-height.hdr')
print('RIPPLE_RUNTIME_MEASURED', json.dumps(result))

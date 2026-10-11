"""PIE check: drive boat pressure, stop source, measure propagation of the actual height RT."""
import unreal,time,json,hashlib,struct
from pathlib import Path
world=unreal.EditorLevelLibrary.get_game_world()
assert world
actors=unreal.GameplayStatics.get_all_actors_of_class(world,unreal.Actor)
boat=next(a for a in actors if a.get_class().get_name()=='BP_LongtailPhysicsPawn_C')
sim=next(a for a in actors if a.get_class().get_name()=='BP_FluidSim_01_C')
hull=boat.get_editor_property('StaticMesh')
buoyancy=boat.get_editor_property('Buoyancy')
boat.set_actor_tick_enabled(False);buoyancy.set_component_tick_enabled(False)
hull.set_enable_gravity(False)
for target in sim.get_editor_property('RippleRTs'):
 unreal.RenderingLibrary.clear_render_target2d(sim,target)
unreal.RenderingLibrary.clear_render_target2d(sim,sim.get_editor_property('ForcesRT'))
start=time.monotonic();rows=[]
forward=boat.get_actor_forward_vector()
state={'phase':0,'handle':None}
def capture(label):
 rt=sim.get_editor_property('NormalRT')
 colors=unreal.RenderingLibrary.read_render_target_raw(sim,rt,False)
 if isinstance(colors,tuple):colors=next(c for c in colors if not isinstance(c,bool))
 hs=[c.b for c in colors]
 center=sim.get_editor_property('GridCenter');p=boat.get_actor_location()
 width=rt.get_editor_property('size_x');size=sim.get_editor_property('Simulation World Size')
 outside=sum(abs(h)>.001 for i,h in enumerate(hs) if (center.x+((i%width)/width-.5)*size-p.x)**2+(center.y+((i//width)/width-.5)*size-p.y)**2>450**2)
 rows.append(dict(phase=label,minimum=min(hs),maximum=max(hs),energy=sum(h*h for h in hs)/len(hs),outside_source_pixels=outside,passes=sim.get_editor_property('Passes'),hash=hashlib.sha256(struct.pack('<%df'%len(hs),*hs)).hexdigest()))
def tick(delta):
 try:
  elapsed=time.monotonic()-start
  velocity=forward*(-800 if elapsed<1 else 0)
  hull.set_physics_linear_velocity(velocity,False)
  if elapsed<1:boat.call_method('UpdateFXState_0')
  if state['phase']==0 and elapsed>=1:capture('moving');state['phase']=1
  elif state['phase']==1 and elapsed>=4:
   capture('stopped_3s')
   assert rows[0]['minimum']<-.001 and rows[0]['maximum']>.001,rows
   assert rows[1]['outside_source_pixels']>0,rows
   assert rows[0]['hash']!=rows[1]['hash'],rows
   assert rows[1]['energy']<rows[0]['energy'],rows
   (Path(unreal.Paths.project_saved_dir())/'Automation/BoatContact/dynamic-runtime-check.json').write_text(json.dumps(rows,indent=2))
   print('DYNAMIC_RUNTIME_PROPAGATION_DECAY_PASS',rows)
   unreal.unregister_slate_post_tick_callback(state['handle'])
 except Exception as e:
  print('DYNAMIC_RUNTIME_CHECK_FAILED',repr(e),rows)
  unreal.unregister_slate_post_tick_callback(state['handle'])
state['handle']=unreal.register_slate_post_tick_callback(tick)
print('DYNAMIC_RUNTIME_CHECK_STARTED')


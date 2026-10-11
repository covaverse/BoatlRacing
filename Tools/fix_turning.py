"""Editor Python: hull yaw damping, bank from real lateral g, rooster tail follows the tail angle.

Stop PIE first. Backs up BP_LongtailPhysicsPawn before editing. Idempotent.
"""
import datetime, shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as B

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE before editing'
root = Path(unreal.Paths.project_dir())
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
backup = root / 'Saved/Backups' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-turning')
backup.mkdir(parents=True)
shutil.copy2(root / 'Content/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn.uasset', backup / 'BP_LongtailPhysicsPawn.uasset')

YAW_DAMPING = 0.0021  # 1/cm: extra yaw damping rate = YawDamping * (speed cm/s + 800)

if 'YawDamping' not in [str(v) for v in B.list_variables(bp)]:
    B.add_variable(bp, 'YawDamping', 'float')
    B.set_variable_category(bp, 'YawDamping', 'Handling')
    B.set_variable_instance_editable(bp, 'YawDamping', True)
    B.compile_blueprint(bp, warnings_as_errors=True)
cdo = unreal.get_default_object(bp.generated_class())
if not cdo.get_editor_property('YawDamping'):
    cdo.set_editor_property('YawDamping', YAW_DAMPING)

MESH = '(Variables|Default|GetStaticMesh)'
VEL = f'(Transformation|GetComponentVelocity {MESH})'
SPEED_XY = f'(Math|Vector|VectorLength (Math|Vector|MakeVector (.x {VEL}) (.y {VEL})))'

# --- Yaw damping: the hull sweeping sideways through water resists yaw, more so at speed --------
# Pure world-Z torque in acceleration mode: no roll/pitch coupling (moving the side force capsized
# the boat twice) and independent of the hull's inertia. Always opposes yaw, so it cannot add energy.
# ponytail: explicit damping is stable while YawDamping*(v+800)*dt < 1, about 8 fps at 110 km/h.
# Lives in its own function: ApplyHydrodynamicDrag's DSL does not round-trip (vector*vector node),
# so it is never rewritten; only one call node is wired after its AddForce.
if 'ApplyYawDamping' not in [g.get_name() for g in B.list_graphs(bp)]:
    B.add_function_graph(bp, 'ApplyYawDamping')
    B.compile_blueprint(bp)
yaw = B.get_graph(bp, 'ApplyYawDamping')
B.write_graph_dsl(yaw, f'''(fn ApplyYawDamping ()
  (Physics|AddTorqueinRadians {MESH} (Math|Vector|MakeVector 0.0 0.0 (* (* -1.0 (Variables|Handling|GetYawDamping)) (* (.z (Physics|GetPhysicsAngularVelocityinRadians {MESH})) (+ {SPEED_XY} 800.0)))) "None" true))
''')
drag = B.get_graph(bp, 'ApplyHydrodynamicDrag')
old = B.read_graph_dsl(drag)
(backup / 'ApplyHydrodynamicDrag-before.dsl').write_text(old)
if 'ApplyYawDamping' not in old:
    force_node = B.find_nodes(drag, 'Add Force', None, False)
    assert len(force_node) == 1, force_node
    info = B.get_node_infos(force_node)[0]
    then = next(p for p in info.output_pins if str(p.name) == 'then')
    call = B.create_node(drag, 'CallFunction|ApplyYawDamping', unreal.Vector2D(info.position.x + 400, info.position.y))
    execute = next(p for p in B.get_node_infos([call])[0].input_pins if str(p.name) == 'execute')
    B.connect_pins(then.pin_id, execute.pin_id)

# --- Visual: bank from real lateral acceleration, rooster tail swings with the tail ---------------
trim = B.get_graph(bp, 'ApplyVisualTrim')
old = B.read_graph_dsl(trim)
(backup / 'ApplyVisualTrim-before.dsl').write_text(old)
SPD = '(Variables|Default|GetForwardSpeedKmh)'
steer_bank = (f'(* 0.2 (* (Variables|Default|GetSteeringDegrees) (select (> (/ {SPD} 70.0) 1.0) 1.0 '
              f'(select (< (/ {SPD} 70.0) 0.0) 0.0 (/ {SPD} 70.0)))))')
# 11 degrees per g of v*r, capped at 18; sign matches the old steering term (steer + gives yaw rate -).
g_bank = (f'(Math|Float|Clamp(Float) (* -0.0054 (* {SPD} (.z (Physics|GetPhysicsAngularVelocityinDegrees {MESH})))) -18.0 18.0)')
new = old
if steer_bank in new:
    new = new.replace(steer_bank, g_bank)
assert g_bank.lower() in new.lower(), 'bank term not found'  # readback spells it ...InDegrees
# Jet leaves opposite the thrust (-cos s, -sin s), i.e. local +X yawed by +SteeringDegrees.
spray = '(Transformation|SetRelativeRotation (Variables|Default|GetPropSprayFX) (Math|Rotator|MakeRotator 0.0 0.0 (Variables|Default|GetSteeringDegrees)))'
if 'GetPropSprayFX' not in new:
    new = new.rstrip()[:-1] + '\n  ' + spray + ')\n'
if new != old:
    B.write_graph_dsl(trim, new)

B.compile_blueprint(bp, warnings_as_errors=True)
assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
d, y, t = B.read_graph_dsl(drag), B.read_graph_dsl(yaw), B.read_graph_dsl(trim)
(backup / 'ApplyHydrodynamicDrag-after.dsl').write_text(d)
(backup / 'ApplyYawDamping-after.dsl').write_text(y)
(backup / 'ApplyVisualTrim-after.dsl').write_text(t)
for token, text in (('ApplyYawDamping', d), ('AddForce', d), ('AddTorqueInRadians', y), ('GetYawDamping', y), ('true', y),
                    ('-0.0054', t), ('GetPropSprayFX', t), ('SetRelativeLocation', t)):
    assert token in text, token
print('YawDamping default', unreal.get_default_object(bp.generated_class()).get_editor_property('YawDamping'))
assert unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False)
print('TURNING_SAVED', str(backup))

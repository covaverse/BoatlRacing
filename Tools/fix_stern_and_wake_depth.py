"""Editor Python: stern rides on the water when planing, and the fluid-sim wake is shown at a visible depth.

Stop PIE first. Backs up the three touched assets before editing.
"""
import datetime, shutil
from pathlib import Path
import unreal
from editor_toolset.toolsets.material import MaterialTools
from editor_toolset.toolsets.blueprint import BlueprintTools

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), 'Stop PIE before editing'
root = Path(unreal.Paths.project_dir())
assets = unreal.EditorAssetLibrary
bp = unreal.load_asset('/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn')
water = unreal.load_asset('/Game/Water/Materials/BoatContact/M_WaterBoatContact')
ocean = unreal.load_asset('/Game/Water/Materials/BoatContact/MI_WaterBoatOcean')

backup = root / 'Saved/Backups' / (datetime.datetime.now().strftime('%Y%m%d-%H%M%S') + '-stern-wake-depth')
backup.mkdir(parents=True)
for asset in (bp, water, ocean):
    file = asset.get_path_name().split('.')[0].replace('/Game/', 'Content/') + '.uasset'
    shutil.copy2(root / file, backup / Path(file).name)

# --- Stern: gentler trim, pivot so the transom rides the water instead of the midship -------------
SPD = '(Variables|Default|GetForwardSpeedKmh)'
VIS = '(Variables|Default|GetBoatVisual)'
def clamp01(x):
    return f'(select (> {x} 1.0) 1.0 (select (< {x} 0.0) 0.0 {x}))'
hump = clamp01(f'(- 1.0 (/ (Math|Float|Absolute(Float) (- {SPD} 28.0)) 26.0))')
# Bank from real lateral g (speed x yaw rate), kept in sync with Tools/fix_turning.py.
roll = (f'(Math|Interpolation|FInterpTo (.roll (Class|SceneComponent|GetRelativeRotation {VIS})) '
        f'(+ (* -0.85 (.roll (Class|SceneComponent|GetRelativeRotation (Variables|Default|GetStaticMesh)))) '
        f'(Math|Float|Clamp(Float) (* -0.0054 (* {SPD} (.z (Physics|GetPhysicsAngularVelocityinDegrees (Variables|Default|GetStaticMesh))))) -18.0 18.0)) DeltaSeconds 6.0)')
# Planing trim settles at 3-5 deg bow up: -3 static + 1.5 at speed, +3 more through the hump (was 3.5 / 8).
pitch = (f'(Math|Interpolation|FInterpTo (.pitch (Class|SceneComponent|GetRelativeRotation {VIS})) '
         f'(+ -3.0 (- (* {clamp01("(Variables|Default|GetThrottle)")} '
         f'(+ (* -1.5 {clamp01(f"(/ {SPD} 40.0)")}) (* -3.0 {hump}))) '
         f'(.pitch (Class|SceneComponent|GetRelativeRotation (Variables|Default|GetStaticMesh))))) DeltaSeconds 2.5)')
# Planing lift: raise the visual so the transom bottom (local 310,0,19) sits 8 cm under the water at speed.
# Visual only, like the trim; physics pontoons keep their own draft.
lift_now = f'(.z (Class|SceneComponent|GetRelativeLocation {VIS}))'
transom = f'(.z (Math|Transform|TransformLocation (Transformation|GetWorldTransform {VIS}) (Math|Vector|MakeVector 310.0 0.0 19.0)))'
lift = (f'(* {clamp01(f"(/ {SPD} 50.0)")} (Math|Float|Clamp(Float) '
        f'(- (- (Variables|Default|GetWaterSurfaceZ) 8.0) (- {transom} {lift_now})) 0.0 45.0))')
dsl = f'''(fn ApplyVisualTrim (DeltaSeconds)
  (Transformation|SetRelativeRotation {VIS} (Math|Rotator|MakeRotator {roll} {pitch}))
  (Transformation|SetRelativeLocation {VIS} (Math|Vector|MakeVector 0.0 0.0 (Math|Interpolation|FInterpTo {lift_now} {lift} DeltaSeconds 3.0)))
  (Transformation|SetWorldLocation (Variables|Default|GetExhaustFX) (Math|Transform|TransformLocation (Transformation|GetWorldTransform {VIS}) (Math|Vector|MakeVector 366.0 34.0 143.0)))
  (Transformation|SetRelativeRotation (Variables|Default|GetPropSprayFX) (Math|Rotator|MakeRotator 0.0 0.0 (Variables|Default|GetSteeringDegrees))))
'''
graph = BlueprintTools.get_graph(bp, 'ApplyVisualTrim')
(backup / 'ApplyVisualTrim-before.dsl').write_text(BlueprintTools.read_graph_dsl(graph))
BlueprintTools.write_graph_dsl(graph, dsl)
BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)
readback = BlueprintTools.read_graph_dsl(graph)
(backup / 'ApplyVisualTrim-after.dsl').write_text(readback)
for token in ('SetRelativeLocation', 'GetExhaustFX', '310.0', '-1.5', '45.0'):
    assert token in readback, token

# --- Wake depth: show the sim height at 3x, keep foam thresholds in sim units -------------------
DEPTH = 3.0
ex = MaterialTools.get_expressions(water)
foam = next(e for e in ex if e.get_editor_property('desc') == 'BoatRippleFoam')
code = foam.get_editor_property('code')
(backup / 'BoatRippleFoam-before.hlsl').write_text(code)
old = 'float amp = max(FluidDelta.z, 0.0) + max(-FluidDelta.z, 0.0) * 0.45;'
if 'DispMul' not in code:
    assert old in code
    code = code.replace(old, '// FluidDelta is in displayed cm; foam ramps were tuned on raw sim units.\n'
                             'float3 simDelta = FluidDelta / max(DispMul, 1.0);\n'
                             'float amp = max(simDelta.z, 0.0) + max(-simDelta.z, 0.0) * 0.45;')
    inputs = list(foam.get_editor_property('inputs'))
    i = unreal.CustomInput(); i.set_editor_property('input_name', 'DispMul'); inputs.append(i)
    foam.set_editor_property('inputs', inputs)
    foam.set_editor_property('code', code)
    # Same name as the parameter inside SampleFluidSimulation, so one MI value drives both.
    p = unreal.MaterialEditingLibrary.create_material_expression(water, unreal.MaterialExpressionScalarParameter, -1400, 2200)
    p.set_editor_property('parameter_name', 'Fluid Displacement Multiplier')
    p.set_editor_property('default_value', 1.0)
    assert unreal.MaterialEditingLibrary.connect_material_expressions(p, '', foam, 'DispMul')
MaterialTools.recompile(water)

# The setter returns False even when it applies the override, so check the readback instead.
unreal.MaterialEditingLibrary.set_material_instance_scalar_parameter_value(ocean, 'Fluid Displacement Multiplier', DEPTH)
unreal.MaterialEditingLibrary.update_material_instance(ocean)
assert unreal.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(ocean, 'Fluid Displacement Multiplier') == DEPTH

# --- Planing pressure: the lifted hull carries the same weight on a smaller wetted footprint -----
# AxisX.a is the 0-1 speed alpha published by UpdateFXState_0 (saturates at 57.6 km/h). Planing lift
# grows with speed squared. x0.33 at rest so rest/spawn ripples look as before after the x3 display;
# x4 at speed (linear x1..x4 gave a 70 cm wake at 30 km/h and a 20 cm moat around the idle hull).
force = unreal.load_asset('/Game/Water/Materials/BoatContact/M_BoatHullFluidForce')
shutil.copy2(root / 'Content/Water/Materials/BoatContact/M_BoatHullFluidForce.uasset', backup / 'M_BoatHullFluidForce.uasset')
shape = next(e for e in MaterialTools.get_expressions(force) if e.get_editor_property('desc') == 'MeasuredHullPressure')
code = shape.get_editor_property('code')
(backup / 'MeasuredHullPressure-before.hlsl').write_text(code)
planing = 'Force * 6.0 * lerp(1.0 / DEPTH, 4.0, AxisX.a * AxisX.a) * valid'.replace('DEPTH', str(DEPTH))
if planing not in code:
    for old in ('(1.0 + 3.0 * AxisX.a) * ', '(1.0 + 3.0 * AxisX.a * AxisX.a) * '):
        code = code.replace(old, '')
    assert 'Force * 6.0 * valid' in code
    shape.set_editor_property('code', code.replace('Force * 6.0 * valid', planing))
    MaterialTools.recompile(force)

BlueprintTools.compile_blueprint(bp, warnings_as_errors=True)  # readback leaves the BP dirty
assert bp.get_editor_property('status') == unreal.BlueprintStatus.BS_UP_TO_DATE
for asset in (bp, water, ocean, force):
    assert assets.save_loaded_asset(asset, only_if_is_dirty=False), asset.get_path_name()
print('STERN_WAKE_DEPTH_SAVED', str(backup))

# Stern riding and wake depth — 2026-10-03

Measured on `M_WaterPhysicsTest` in PIE. Applied by `Tools/fix_stern_and_wake_depth.py`, which is idempotent.
Original assets: `Saved/Backups/20261003-213924-stern-wake-depth` (the later `-stern-wake-depth` folders hold intermediate states).

## Stern buried when running

`ApplyVisualTrim` pitched `BoatVisual` about its midship origin: -3 static, -3.5 at speed and -8 through the hump.
At 110 km/h the total pitch was -6.5 degrees. The transom bottom (local 310,0,19; hull keel Z 0, sheer 67) sat 41 cm under water with 7 cm freeboard.
Around 28 km/h the total reached about -13 degrees, which put the stern sheer under water.

Now:
- The speed term is -1.5 and the hump term is -3, giving a total of -4.5 degrees at speed, inside the 3-5 degree planing range.
- A visual planing lift `SetRelativeLocation(BoatVisual, Z)` is `clamp(spd/50) * clamp(water - 8 - transomZ_unlifted, 0, 45)`, smoothed with `FInterpTo` at rate 3. It keeps the transom bottom 8 cm under water at speed. The lift is visual only, like the trim, and the physics pontoons and draft are unchanged.
- `ExhaustFX` is placed every frame at visual-frame (366,34,143), so smoke stays on the pipe while the visual trims or lifts.

| 110 km/h | before | after |
|---|---|---|
| total pitch | -6.5 | -4.5 |
| transom bottom vs water | -41 cm | -8 cm |
| transom freeboard | 7 cm | 40 cm |
| visual lift | 0 | 22 cm |

At rest the lift is 0 and the pitch is still about -3, so `verify_hull_foam.py` (stern below bow at rest) still holds.

## Wake was only centimetres deep

`SampleFluidSimulation` displaces the water by `height * Fluid Displacement Multiplier`, and the multiplier was 1. At 110 km/h the sim peaked at -6.3/+4.7, so the parting the user saw was 6 cm deep.

- `MI_WaterBoatOcean` (used by all three test maps) now sets `Fluid Displacement Multiplier` = **3**.
- `BoatRippleFoam` in `M_WaterBoatContact` divides `FluidDelta` by the same parameter, through a new top-level `ScalarParameter` with the same name, so foam ramps stay in raw sim units.
- `M_BoatHullFluidForce` multiplies the pressure by `lerp(1/3, 4, AxisX.a^2)`. A lifted hull carries the same weight on a smaller wetted footprint, and the stamp follows the visual frame, so the wetted area shrinks when planing. At rest, 1/3 × 3 = the original visible ripple.

Measured displayed height near the hull: 110 km/h -22/+11 cm (5 m behind: -12/+10); 41 km/h accelerating -24/+17; at rest ±3.
Rejected along the way:
- Display ×4 with linear `1+3a` forcing reached -57 cm at 30 km/h and left a 20 cm moat around the idle hull.
- Display ×4 with `1+3a²` still clamped at 40 cm around 57-76 km/h.

`AxisX.a` saturates at 57.6 km/h (`v/1600`), so the forcing factor is flat above that speed. The wake falls off roughly as 1/speed, because the hull dwells less per cell at high speed. That falloff is physically right; do not "fix" it.

## Traps

- `set_editor_property` on a running component (for example `ChaseBoom.target_arm_length`) fires an edit notification that reset the boat's physics: it went to 300 km/h and rolled 66 degrees. During PIE use `PropertyAccessChangeNotifyMode.NEVER`.
- `MaterialEditingLibrary.set_material_instance_scalar_parameter_value` returned False while applying the override. Check the value with `get_material_instance_scalar_parameter_value` instead of the return value.
- The flat course is about 45 km long. At full throttle the boat runs off its end in about 13 s and then flies or falls, so measure within roughly 10 s of starting.
- Python remote execution was enabled (`Config/DefaultEngine.ini`, `bRemoteExecution=True`, localhost only) to run these scripts from outside the editor.

## Not checked

The small- and high-wave maps were not run. On waves the lift follows `WaterSurfaceZ` at the hull and is clamped to 0..45 cm.

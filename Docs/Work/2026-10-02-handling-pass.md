# Handling, trim and wake pass — 2026-10-02, Asia/Bangkok

All measurements are live PIE samples through the MCP endpoint. Saved-level test
overrides are false/zero and PIE is stopped.

## The boat was lifting out of the water in turns — fixed

A hard turn at speed raised the hull origin from 374 cm to **404 cm** against a
400 cm water plane, with propeller immersion falling to 0.56. The same lift
happened at the old 18 degree steering (394 cm), so widening the steering made
it worse but was not the cause.

The cause was in the EventGraph lateral drag:

```
AddForce(hull, TransformDirection(hullTransform, MakeVector(0, slip * -lateralDrag, 0)))
```

The force is built in hull space and transformed by the **full** hull transform,
so once the hull banks the side force tilts with it and part of it becomes
lift — about 9 percent of a very large force at 5 degrees of roll, applied
continuously through the turn. Propulsion was already projected onto world XY
for exactly this reason; the lateral drag had been missed.

Both `AddForce` sites now pass the transformed vector through
`BreakVector -> MakeVector(X, Y, 0)` so Z is forced to zero. After the fix the
hull holds **379.2-379.3 cm** for a whole 45 degree turn, roll settles at a
steady 3.48 degrees instead of oscillating, and propeller immersion stays at
0.99-1.00.

## Turning circle

Measured from yaw rate and speed at full lock:

| steering | lateral drag | yaw rate | radius | speed in turn |
|---|---|---|---|---|
| 18 (original) | 1200 | — | — | — |
| 26 | 1200 | 7.6 deg/s | 223 m | 106 km/h |
| 38 | 2400 | 12.8 deg/s | 109 m | 86-94 km/h |
| 45 | 3200 | 14.9 deg/s | 83 m | 75 km/h |

45/3200 made the hull roll ring badly (0.4 -> 10.4 -> 0.5 -> 12.2 degrees), so
the shipped values are **38 degrees and lateral drag 2400**. The six steering
literals live in three parallel branches of `UpdateDriveState_0`; all six were
changed together. Steering still interpolates at `FInterpTo ... 5.0`.

## Bow lift and bank are visual, not physical

Pushing the hull with torque does not work: at `launchPitchTorque` 150,000,000
the hull rocked to -2.3 degrees and overshot to +0.39 bow-down before the
buoyancy springs won. The launch system also fires into a dead frame because the
propeller is dry at the start. Those experiments were reverted.

New Blueprint function `ApplyVisualTrim(DeltaSeconds)`, called at the end of
Tick, rotates the non-colliding `BoatVisual` child actor instead:

- **Pitch** `-7 * clamp((60 - speed)/60) * clamp(throttle)`, smoothed at 2.5.
  Measured -5.7 degrees bow-up from a standstill, decaying to 0 by 75 km/h.
- **Roll** `-0.85 * hullRoll + 0.2 * steering * clamp(speed/70)`, smoothed at 6.
  The first term cancels the physical outward lean, the second banks **into**
  the turn the way a driver shifts weight. Net world roll holds a steady -6 to
  -7.5 degrees through a turn even while the hull itself still varies 3 to 8.6.

The physics body is untouched by this, so none of it can destabilise handling.
Keep the angles small: the interior water mask uses the collision hull's
distance field, so a large visual-only offset would desync the waterline.

## Stern trim, and why engine mass does not move it

`bCenterPontoonsOnCOM` is true, so the pontoons move with the centre of mass.
Shifting `engineCenterXcm` from 270 to 430 changed resting pitch from -1.90 to
-1.62 degrees — the supports simply followed the weight. Engine mass and offset
were restored to 200 kg at 270 cm.

The only effective lever is the rear pontoon radius, and it is a cliff:

| rear radius | rear submersion | resting pitch | prop immersion at rest |
|---|---|---|---|
| 55 (original) | 78% | -1.65 | 0.00 (dry) |
| 54 | 64% | -1.65 | 0.00 (dry) |
| 53.5 | 81% | -2.58 | 0.00 (dry) |
| **53 (shipped)** | 101% | **-4.90** | **1.00** |
| 50 | 163% (swamped) | -11.54 | 1.00 |

53 is the only value that both squats the stern and puts the propeller in the
water at rest, which also unblocks the launch gate. It leaves almost no reserve
buoyancy aft (101% means the rear spheres are just fully submerged), so rough
water needs rechecking on the high-wave map before this is accepted.

At steady 110 km/h propeller immersion reads 0.96-1.00; the zeros seen earlier
are transient during acceleration.

## Wake coverage and propeller spray

The collision hull spans local X **-310 to +310** and the pontoons sit at
±240, so each end has 70 cm of unsupported overhang. More importantly the two
hull wake impulses were both forward (-240 and -30), leaving the whole stern
half over undisturbed water. They are now at **(-240, +35, -20)** on the bow
port side and **(250, -35, -20)** at the stern on the starboard side, so the
disturbance covers the full length and bends with the boat.

Speed-driven wake was raised without touching the standing-still values, so the
side wake only grows when the boat is actually moving fast: bow speed term
0.10 -> **0.22**, propeller power term 0.06 -> **0.13**, bow impulse radius
55 -> **70**. The constant terms stay at 0.03 and 0.02.

Propeller spray now reads as a rooster tail rather than a thin mist: rate
multiplier 7 -> **12**, jet speed `120 + 500a` -> `200 + 900a`, spread
`15 + 20a` -> `22 + 35a`, droplets 3-8 cm -> **6-18 cm**, lifetime 0.2-0.65 s ->
**0.35-1.1 s**.

## FX popped out instead of fading

`UpdateFXState_0` called `SetVisibility` on BowSplashFX, PropSprayFX and
ExhaustFX from the same condition that gates their spawn rate. Hiding the
component removes every live particle at once, so lifting the propeller out of
the water made the whole spray vanish mid-air instead of the droplets falling
and dying normally.

All three `bNewVisibility` pins are now a literal `true`; the spawn rate alone
decides whether new particles appear, and the ones already in flight live out
their lifetime. A capture taken half a second after cutting throttle and
trimming the tail up shows the trail still present with no new burst at the hub.

Densities raised at the same time: propeller spray rate multiplier 12 -> **26**,
bow splash per side 130 -> **260**, propeller wash base 4 -> **10** and its
RPM term 24 -> **60**. Originals are in
`Saved/Backups/2026-10-02-foam-blend/fx_rates_before.json` and
`fx_visibility_before.json`. No particle budget was measured for this.

## Stern pivot (option B) — attempted twice, reverted

The request was for the bow to bite and the stern to slide out. The mechanism is
right: the lateral drag uses `AddForce`, which acts at the centre of mass and so
produces no yaw at all, and moving its application point forward of the COM is
what creates the weathervane moment.

Both attempts capsized the boat.

1. `AddForceAtLocation` at local `(-150, 0, 0)` via `TransformLocation` on the
   hull world transform: roll -51 degrees, pitch +35, hull sinking to 258 cm
   within three seconds.
2. Same point at `(-100, 0, 0)` with the location's Z replaced by the real
   centre-of-mass Z (reusing the same `GetCenterOfMass` break the propulsion
   uses, so the horizontal force has no vertical lever): still capsized, rolling
   through 63 -> 148 degrees.

With `lateralDrag` at 2400 and several hundred cm/s of sideslip, the side force
is of order 700,000 units. A one metre lever is roughly 70,000,000 of yaw
torque against a hull yaw inertia near 14,000,000 kg·cm² — the boat is simply
spun over. Relocating an existing large drag force is the wrong shape for this.

Both sites were restored to plain `Physics|AddForce` and verified stable
(radius 153-175 m, roll 10-27 degrees, no capsize). Node map of the original
wiring is in `Saved/Backups/2026-10-02-foam-blend/lateral_pivot_before.json`.

What this needs instead is a **separate, explicitly bounded yaw moment** — the
same shape as the existing `CalculateTailWaterForce`, which saturates and can
never exceed a cap — rather than moving the drag. That was not built.

## Rear pontoon radius is a real trade-off

Measured in a sustained 38 degree turn:

| rear radius | max roll | turn radius | prop at rest | resting pitch |
|---|---|---|---|---|
| 55 | 8.5 deg | 155 m | dry | -0.81 |
| **53 (shipped)** | **22.3 deg** | **17 m** | **wet** | -2.06 |

53 buys the stern squat, the wet propeller and a far tighter turn, at the cost
of heeling hard. 22 degrees with the rear spheres already at 101% submersion
leaves little margin, so the high-wave map still needs checking before this is
accepted. The choice is a design call, not a bug.

## ApplyLaunchPitch removed

It was **not** orphaned — `UpdateWaterPropState` called it every tick. The call
node was deleted (it was the end of that exec chain, so nothing needed
bridging). The function itself still exists, unreferenced.

## Wake strength raised again, with a ceiling that is not ours

Speed and power terms raised a second time: bow `0.03 + 0.22a` -> `0.03 + 0.55a`,
propeller `0.02 + 0.13a` -> `0.02 + 0.30a`. At-rest constants untouched, so a
stationary boat still makes no rings.

The request for the wake to rise **above the boat** cannot be met this way. The
height is clamped inside `/Water/Materials/Functions/SampleFluidSimulation`, a
201-node engine function, and the `BP_FluidSim_01` actor exposes no displacement
or amplitude property. Raising it means either editing engine content or
duplicating that function into the project and reparenting the water material to
the copy. Neither was done.

## Tall side spray added as particles, not simulation

Since the fluid simulation's height is clamped inside engine content, the
"spray higher than the boat" request is met with a dedicated Niagara system
instead.

`NS_LongtailBowSplash` was duplicated to
`/Game/Boats/ThaiLongtail/FX/NS_LongtailSideSpray` — it already carried two
mirrored emitters and `User.SpawnRate` / `User.SpraySpeed` / `User.SpraySpread`.
Changes from the copy: cone axes rotated to `(0, +/-0.55, 0.84)` so the sheet
goes up rather than out, and the spawn sphere widened from 8 cm to **180 cm** so
droplets appear along the hull instead of from one point.

Because no MCP tool can add a component to a Blueprint's construction script,
the component is spawned at runtime. Two new functions:

- `SetupSideSpray()` — `SpawnSystemAttached` on the hull, kept in a new
  `SideSprayFX` NiagaraComponent variable. Called at the end of BeginPlay.
- `UpdateSideSpray(DeltaSeconds)` — drives the three user variables from
  `clamp(speed/90)`: speed `450 + 950a`, spread `20 + 26a`, rate
  `300 + 1400a` above an 8% threshold. Called at the end of Tick.

Droplet size went through two passes. The first attempt at 8-26 cm read as
blobs rather than water, and was corrected to **1.5-5 cm** with the spawn rate
raised to compensate. Hang time was then cut so it falls like water rather than
drifting: gravity **-1900** (not the real -980), drag 0.25 -> **0.08**, lifetime
**0.30-0.85 s**.

## Open

- **Stern pivot** still not delivered; needs a bounded yaw-moment term, not a
  relocated drag force. See above.
- **Wake height above the boat** is now faked with `NS_LongtailSideSpray`
  particles. Raising the *simulated* surface still needs the engine's
  `SampleFluidSimulation` duplicated into the project first.
- Rear pontoons at 101% submersion with 22 degrees of roll in a hard turn: the
  high-wave map has not been run.
- No particle budget was measured after the density increases.

## Backups

`Saved/Backups/2026-10-02-foam-blend/` holds `steering_before.json`,
`handling_launch_before.json`, `lateral_drag_before.json`,
`fx_impulse_before.json`, `fx_impulse_points_before.json` and
`propspray_sternwake_before.json`.

## Traps hit while measuring

- Asset lookups and saves fail with "Asset does not exist" **while PIE is
  running**. One Blueprint edit was silently lost this way and had to be
  re-applied; always stop PIE, then save, then read the value back.
- Leaving the test throttle on for minutes drives the boat kilometres off the
  course, after which the fluid grid stops following and the wake vanishes.
- The boat needs roughly ten seconds to get moving from rest.

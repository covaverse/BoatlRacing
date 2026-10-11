# Exhaust smoke, foam blending and ripple domain — 2026-10-02, Asia/Bangkok

All work below was done against the live Editor through the MCP endpoint on
`127.0.0.1:8000`. Evidence is PIE screenshots taken with `CaptureEditorImage`
while PIE ran in the level viewport; `CaptureViewport` renders the **editor**
world, not the PIE world, so it cannot be used to inspect a moving boat.
Saved-level test overrides are false/zero and PIE is stopped.

## Exhaust read as soap bubbles

`NS_LongtailExhaust` used `/Niagara/DefaultAssets/DefaultSpriteMaterial`, the
stock soft white radial sprite, so every puff rendered as a clean translucent
circle. The emitter values themselves were already reasonable (18-42 cm sprites,
grey 0.28 at 0.45 alpha, 1.2-2.1 s life, 25 degree upward cone, drag 0.25);
only the renderer material was wrong. Deactivating the component by `bVisible`
does **not** stop a running Niagara component — the A/B that identified this
had to move the component instead.

Added `/Game/Boats/ThaiLongtail/FX/M_LongtailExhaustSmoke`: unlit, translucent,
two-sided. Opacity is a soft radial mask `saturate(1 - 2*|uv - 0.5|)` multiplied
by a slowly panning sample of the installed `/Water/Textures/Foam/
T_WaterFlow_03_Foam_Tiled`, then by particle alpha; emissive is particle colour.
No new texture was imported. Renderer `bCastShadows` is now false.

`bUsedWithNiagaraSprites` must be set on the material. Without it the sprites
fall back to the default opaque material and render as hard dark squares; this
was observed before the flag was set.

## Foam read as painted white, not aerated water

The foam lives in `M_WaterBoatContact` `MaterialExpressionCustom_3`. The old
code used `abs(FluidDelta.z)`, so crests and troughs foamed equally, and ended
with `saturate(... * 1.35)`, which clipped large areas to the full foam colour
and produced the flat white strip.

Now: crest-weighted amplitude `max(dz,0) + max(-dz,0) * 0.45`, ramp
`smoothstep(0.05, 1.0, amp)` instead of `smoothstep(0.08, 1.2, abs(dz))`, and
the result is capped at 0.88 rather than over-driven into saturation, so water
colour always shows through the foam. Texture sampling and warping are
unchanged. Before/after code is in `Saved/Backups/2026-10-02-foam-blend`.

## Ripple domain and impulse strength

`simulation World Size` raised 4096 -> 8192 cm on all three test maps at the
same 1024 resolution (4 cm cells become 8 cm). The wake lifetime was bounded by
the domain, not by the forcing: at 110 km/h a boat leaves a 4096 cm box in
1.3 seconds. `pawn Check Every N Frames` lowered 10 -> 1 so the grid tracks the
boat each frame instead of every ~170 ms.

**Raising the impulse forcing was tried and reverted.** Bow 0.03/0.10 -> 0.05/0.17,
prop 0.02/0.06 -> 0.035/0.11 and radii 55/55/70 -> 80/80/100 turned the wake into
concentric foam rings centred on the hull, because the per-frame point impulses
spread faster than the boat travels. Travel speed 0.35 -> 0.6 made this worse for
the same reason: a V-shaped wake requires the boat to outrun its own waves.
All forcing values and `travel Speed`/`damping` are back at their original
0.03/0.10, 0.02/0.06, 55/55/70, 0.35 and 0.005. Original values are recorded in
`Saved/Backups/2026-10-02-foam-blend/fx_impulse_before.json` and
`ripple_solver_before.json`.

## Simulation border fade — resolved

The hard rectangle is gone. **No Blueprint change was needed**: the Water
plugin already publishes the grid to `MPC_Water` as `SimLocation` and
`FluidSimSize`, and `/Water/FluidSimulation/Materials/Functions/
Fluidsim_WorldPosition_to_UV` turns a world position into the sim's own 0-1 UV
using exactly those, so the material can ask the sim where the border is rather
than being told.

Added to `M_WaterBoatContact`: that function (fed by a WorldPosition node),
then `|uv - 0.5|`, the larger of the two components, a `SmoothStep` over
**0.452 to 0.499** and a `OneMinus`. The result drives a new
`BlendMaterialAttributes` whose A is the attributes entering
`SampleFluidSimulation` (via `StaticSwitchParameter_2`) and whose B is the
attributes leaving it. All three former consumers of the function's `Attributes`
output — `MaterialFunctionCall_13.Attributes`,
`MaterialFunctionCall_13.'Additional Water Mask'` and
`BreakMaterialAttributes_8.Attr` — now read the blend instead, so displacement,
normals and the foam (which derives from `FluidDelta`) all fade out together.
Full node wiring from before the edit is in
`Saved/Backups/2026-10-02-foam-blend/M_WaterBoatContact_wiring_before.json`.

The fade band had to be pushed right out to the border, and that is worth
knowing: **the boat does not sit at the centre of the simulation grid.** Live
PIE samples put it at a constant `|uv - 0.5|` of about 0.377 in X and 0.188 in
Y, with the grid centred roughly 31 m *ahead* of the boat along its heading.
That leaves only about 10 m of domain behind the hull for the wake to live in,
while three quarters of the grid sits ahead of the boat where nothing is
happening. A wider fade (0.20-0.45 was tried) erases the wake completely,
because the wake is behind the boat and therefore even closer to the border.

Shifting the grid so the boat rides near its leading edge would give the wake
the whole domain and is the next real improvement. It was not attempted: the
offset is produced inside the stock `BP_FluidSim_01` follow logic, not by a
settable property on the actor.

An A/B that forced the blend fully to A confirmed the mechanism: with the fluid
contribution off the water is completely clean and the rectangle disappears, so
the seam was definitely the simulation region and nothing else.

Two measurement traps worth recording. Leaving the test throttle on for minutes
drives the boat kilometres past the course, after which the grid stops following
and the wake is simply absent — several captures were discarded for this. And
the boat takes roughly ten seconds to get moving from a standing start, so an
early capture shows no wake no matter what the material does.

## Camera-rotation smearing

Turning hard at speed swings the chase camera, and the white foam and exhaust
left soft ghost blobs that crossed the horizon into the sky while the whole
frame smeared. Two causes, both confirmed by reading the live CVars:

- `r.MotionBlurQuality` is 4 (very high) and nothing overrode the post-process
  defaults, so `MotionBlurAmount` 0.5 / `MotionBlurMax` 5 / `MotionBlurTargetFPS`
  30 applied. A target FPS of 30 scales the blur as if the game ran at 30, which
  roughly doubles it at 60.
- `M_LongtailExhaustSmoke` had `bOutputTranslucentVelocity` false, so the smoke
  wrote no velocity and TSR (`r.AntiAliasingMethod` 4) ghosted it.

Fixed by setting `bOutputTranslucentVelocity` on the smoke material and adding
an unbound `PostProcessVolume` named PP_BoatRacing (priority 1) to each of the
three test maps with MotionBlurAmount 0.15, MotionBlurMax 2 and
MotionBlurTargetFPS 0. The chase camera's own post-process overrides are still
all false, so the volume wins. `r.Water.SingleLayer.VelocityOutputPass` is
already 1, so the water surface itself was writing velocity correctly.

The project-wide `r.MotionBlurQuality` was left at 4; only the amount changed.

## Wake direction along the hull

The two bow impulses sat at local `(-240, +22, -20)` and `(-240, -22, -20)` —
44 cm apart, effectively one point — with the only other impulse at the
propeller far aft. That produced a blob at the bow and a blob at the stern
rather than a disturbance running down the boat.

They are now spread along the hull and across it: `(-230, +35, -20)` at the bow
on the port side and `(-30, -35, -20)` amidships on the starboard side. Each
point lays a continuous track as the boat moves, so the wake runs along the hull
toward the stern and bends with the boat when it turns. No nodes were added —
only four literal pins changed, recorded in
`Saved/Backups/2026-10-02-foam-blend/fx_impulse_points_before.json`.

Note for future passes: `write_graph_dsl` replaces a graph wholesale and HANDOFF
records an earlier DSL round-trip being rejected by review, so pin edits through
`set_pin_value` are the safer way to retune this function.

## Changed assets

- `/Game/Boats/ThaiLongtail/FX/M_LongtailExhaustSmoke` (new)
- `/Game/Boats/ThaiLongtail/FX/NS_LongtailExhaust` (renderer material, shadows)
- `/Game/Water/Materials/BoatContact/M_WaterBoatContact` (foam Custom node, plus the
  border-fade chain and BlendMaterialAttributes)
- `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn` (impulse pins,
  set then restored to the original values)
- `/Game/Maps/M_WaterPhysicsTest`, `M_WaterSmallWavesTest`, `M_WaterHighWavesTest`
  (solver domain and follow cadence, plus a new unbound PP_BoatRacing volume)

No automation test or commandlet verification was run for this pass; the
evidence is visual only. C++ cannot be built on this machine — see
`Docs/Work/2026-10-02-gpu-ripple-buoyancy.md`.

# GPU ripple heights into buoyancy — 2026-10-02, Asia/Bangkok

Closes the gap recorded in STATUS as "GPU heights still do not feed CPU
buoyancy". **The code is written but has never been compiled**: this machine has
no Visual Studio and no Windows SDK, and `Build.bat BoatlRacingEditor Win64
Development` stops at

```
Platform Win64 is not a valid platform to build. SDK validation failed:
  Sdk: not found. Required version 10.0.19041.0.
```

`Binaries/Win64/UnrealEditor-BoatlRacing.dll` was built elsewhere and copied in.
Every engine signature used below was checked against the installed UE 5.8
source, but nothing here is compile-verified, and `UBoatRippleFieldComponent` is
a new UCLASS, so Live Coding cannot load it — the Editor must be closed for a
full rebuild.

## What the solver actually exposes

`BP_FluidSim_01` allocates `NormalRT`, a **1024x1024 RTF_RGBA16f** render target
whose **B channel holds the height**, confirmed by live readback during PIE. The
grid is described by `GridCenter` and `Simulation World Size` (4096 cm at the
time of measurement, now 8192). `Tools/inspect_ripple_runtime.py` already maps
world XY to cell index the same way.

## Design

`Private/BoatRippleFieldMath.h` holds the pure, testable part: grid origin, the
world-to-cell mapping, bilinear sampling that returns 0 outside the readback
window and treats a non-finite cell as 0, the spherical-pontoon submerged volume,
the engine's speed ramp, and the buoyancy correction.

The correction reuses the engine's own model rather than inventing one. UE
computes, per pontoon,

```
SubDiff   = clamp(WaterLevel - (CenterZ - R), 0, 2R)
SubVolume = (pi/3) * SubDiff^2 * (3R - SubDiff)
Force     = clamp(SubVolume * CoefficientWithRamp, 0, MaxBuoyantForce) * PontoonCoefficient
```

so the ripple contribution is simply that force evaluated at `WaterLevel +
RippleHeight` minus the same force at `WaterLevel`. There is no new physics
constant to tune, the engine's force ceiling bounds the correction by
construction, and the damping term cancels exactly because it depends on
vertical velocity rather than on water level.

`Public/BoatRippleFieldComponent.h` / `Private/BoatRippleFieldComponent.cpp`
own the readback. `FRHIGPUTextureReadback` copies **a 256x256 cell window around
the boat**, not the whole texture: the full 1024² RGBA16f surface is 8 MB per
frame, the window is 512 KB. One copy is in flight at a time; the previous one is
resolved and published to the game thread as an immutable snapshot under a lock.
The readback state is held by a shared pointer so a render command that outlives
the component does not dangle. Expect two to three frames of latency, which is
why the window is far wider than the hull.

Blueprint surface: `UpdateRippleField(NormalRT, GridCenter, SimWorldSize,
FocusLocation)` once per tick, then `ApplyRippleBuoyancy(Buoyancy)`, which
returns the total force actually applied for QA. `GetRippleHeight(WorldLocation)`
and `GetResolvedFrameCount()` exist for telemetry — a frame count stuck at zero
means the readback never resolved.

`MaxRippleHeightCm` (default 50) clamps the sampled height so one bad readback
cannot launch the hull.

## Tests

`BoatlRacing.Physics.RippleField` in `Private/Tests/BoatlRacingWaterTests.cpp`
covers the grid origin, cell-centre and interpolated samples, rejection outside
the window, a non-finite world location, a corrupt NaN cell, a truncated buffer,
crest versus trough sign, a fully submerged and a fully dry pontoon, the force
ceiling, invalid radius/coefficient/height, and the ramp including a
zero-width ramp window. These are UE Automation tests, not the standalone MSVC
harness used for the interior-mask work, because the math uses UE types.

## To finish

1. Install the UE prerequisites (VS 2022 Build Tools, Desktop C++, Windows SDK)
   or build on the machine that produced the current DLL.
2. Close the Editor, rebuild `BoatlRacingEditor`, reopen.
3. Run `BoatlRacing.Physics.RippleField` through the automation toolset.
4. Add `UBoatRippleFieldComponent` to `BP_LongtailPhysicsPawn` and call the two
   functions from the existing FX/physics tick, feeding the solver actor's
   `NormalRT`, `GridCenter` and `Simulation World Size`.
5. Check `GetResolvedFrameCount()` advances in PIE before trusting any force.

## Files

- `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private/BoatRippleFieldMath.h`
- `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private/BoatRippleReadback.h`
- `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Public/BoatRippleFieldComponent.h`
- `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private/BoatRippleFieldComponent.cpp`
- `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private/Tests/BoatlRacingWaterTests.cpp`
- `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/BoatlRacingPhysics.Build.cs` (`RHI`, `RenderCore`)

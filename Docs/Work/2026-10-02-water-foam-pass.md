# Water and foam pass, continuing Codex — 2026-10-02, Asia/Bangkok

Worked entirely in **`M_WaterSmallWavesTest`** at the user's request; the editor
was already left there. Pawn in that map is `BP_LongtailPhysicsPawn_C_1`, not
`_C_0`.

## What Codex had added since the previous pass

- `/Game/Water/Materials/BoatContact/M_BoatHullFluidForce` — an additive, unlit
  material that stamps a **hull-shaped force** into the fluid simulation instead
  of point impulses. It reads the measured `T_BoatDryProfile` to get the hull
  half-width at each station, then pushes water **down** inside the footprint
  (`core`) and **up** just outside it (`bank`), masked along X from -245 to +315
  and only below the keel at Z -25. Applied through `ApplyFluidForceImpulse`
  with a 360 cm canvas stamp. The propeller still uses its own 70 cm impulse.
- `WW_SmallGerstner` retuned to a proper multi-directional spectrum: wavelengths
  4500 down to 2025 cm, amplitudes 30 to 16.5, steepness 0.20 to 0.30.

The two-point bow/stern impulses from the previous pass are gone, replaced by
that stamp. `ApplyVisualTrim`, `SetupSideSpray` and `UpdateSideSpray` survived.

## Foam was faint because of a ceiling, not a missing feature

The foam Custom node had been retuned alongside the stamp to
`smoothstep(0.25, 1.8, amp)` with a final multiplier of **0.30**, so foam could
never exceed 30% blend. Raised to `smoothstep(0.12, 1.4, amp)` and **0.72**.
That alone restored a strong white wake along the hull and behind it, with no
new system needed. Previous code is in
`Saved/Backups/2026-10-02-foam-blend/foam_codex_before.hlsl`.

## Splash now reacts to waves instead of only to speed

The reference clip could not be watched — YouTube refuses playback in the
automated tab, as it did at the start of the session, so only the title was
available: *Advanced Boat Simulation PART 1 — Building a buoyancy system using
Niagara in UE5*. The technique the title implies is that water probes on the
hull drive the splash, so spray fires where and when the hull actually meets
water rather than from a global speed value.

`UpdateSideSpray` previously drove everything from `clamp(speed/90)` alone,
which is why spray was uniform and ignored the waves. It now also reads the
hull's vertical velocity:

```
slam  = clamp(-velocityZ / 380, 0, 1)
burst = slam * slam
```

and adds `burst` on top of the speed term — spawn rate `+3200`, launch speed
`+1100`, spread `+18` for the droplets, and `+90` rate on the mist. Squaring it
keeps gentle heave quiet and only fires on a real slam. On the small-wave map
the boat now throws a burst each time it lands on a wave.

## Not done

- Foam still has no independent persistence; it fades with the ripple rather
  than lingering and decaying on its own. A transported foam render target
  remains the honest fix and was not built.
- The splash is driven by a single hull-wide vertical velocity, not per-pontoon.
  Per-pontoon entry speed would put the burst at the corner that actually hit,
  which is closer to what the reference title describes.

## Warning

The editor raised a **Memory Pressure Warning** again during this pass, after a
long series of PIE runs and shader recompiles. A restart is advisable before
more work.

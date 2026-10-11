# Propeller rooster tail — 2026-10-03

The user asked for a stronger, more scattered propeller effect. Measured on `M_WaterPhysicsTest`.
Originals: `Saved/Backups/20261003-220028-prop-spray` (`NS_LongtailPropSpray`, `NS_LongtailPropWash`, `BP_LongtailPhysicsPawn`, input dump).

## Why it looked weak

The rate was not the problem: at 110 km/h the prop is fully wet and `PropSprayFX` already spawned about 1,800 particles per second. The causes were:

- **The jet was nearly flat.** Cone axis (0.94, 0, 0.35) at 11 m/s gives 3.9 m/s of vertical speed, so the spray peaked at about 76 cm.
- **The particles are in world space and the boat leaves them at 30 m/s.** The rate was smeared into a line about 40 m long, roughly 60 drops per metre. A slow jet also peaks so far behind the boat that the chase camera never sees the top.
- **Tiny blue drops.** They were 6-18 cm, tinted (0.22, 0.74, 1.0), on `DefaultSpriteMaterial`, so they matched the water colour and read as bubbles.

## Changes

`NS_LongtailPropSpray`. Local +X is aft.

| emitter | input | before | after |
|---|---|---|---|
| Fountain (drops) | Color | 0.22, 0.74, 1.0, 0.8 | 0.92, 0.96, 1.0, 0.9 |
| | Size | uniform 6-18 | **random non-uniform (5,18)-(14,55)**, renderer **VelocityAligned**, so drops render as streaks |
| | Lifetime | 0.35-1.1 | 0.6-1.5 |
| | Sphere radius | 8 | 22 |
| | Cone axis | (0.94, 0, 0.35) | **(0.45, 0, 0.89)**, mostly up |
| | Drag | 0.25 | **3.0** |
| **Mist** (new) | — | — | copied from `NS_LongtailSprayMist:Fountain` (`M_LongtailSprayMist`, 8x8 flipbook) |
| | SpawnRate | — | `User.SpawnRate` × spawn probability **0.03**, so no new user variable is needed |
| | Color / size / life | — | alpha 0.28, 80-220 cm, 0.9-2.2 s, position offset off |
| | Velocity | — | `User.JetSpeed` / `User.JetSpread`, axis (0.45, 0, 0.89), gravity -300, drag 3.5 |

`BP_LongtailPhysicsPawn` → `UpdateFXState_0`, literal pins only, with no DSL rewrite:

- `JetSpeed` = 200 + 900a → **400 + 2400a** (a = |shaftRPM|/1400)
- `JetSpread` = 22 + 35a → **30 + 40a**
- PropSpray `SpawnRate` = wash × 26 → **× 60**

Fast launch plus strong drag is the point of this change. By calculation, drops reach about 2 m within 0.1 s (about 3 m behind the prop at 110 km/h) and top out near 6 m. A fast jet with low drag would go 30 m up; a slow jet never rises before the camera loses it.

The `SubUVAnimation` "Sprite Renderer: None" warning on Mist is copied from the source system, where the flipbook still plays.

## Not done

- The plume follows hull yaw, not the steered tail angle, because `PropSprayFX` takes the hull's rotation.
- Particle budget: about 4,200 drops/s at full RPM with 0.6-1.5 s life, so roughly 4-6k CPU particles. Not profiled.
- Wave maps not run.

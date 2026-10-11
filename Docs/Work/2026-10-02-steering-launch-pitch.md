# Steering range and launch pitch — 2026-10-02, Asia/Bangkok

## Steering widened to 26 degrees

`UpdateDriveState_0` sets `SteeringTargetDegrees` from three parallel branches,
each with its own pair of `Make Literal Float` nodes. All three pairs feed
`SteeringTargetDegrees` setters, so all six literals were changed from
+/-18 to +/-26 and the Blueprint recompiled. Originals are in
`Saved/Backups/2026-10-02-foam-blend/steering_before.json`.

Live PIE check at full lock: `steeringDegrees` reaches -26.00 and the hull yaws
at about 3.7 deg/s while holding 67 km/h. Steering still interpolates at
`FInterpTo ... 5.0` in the EventGraph, which was not changed.

## Launch pitch does not work, and why

Asked whether the bow should rise and the stern squat under acceleration: it
should, and at the moment it does not happen at all.

Measured from a standing start at full throttle, hull pitch stays flat the
whole way (negative is bow-up in this rig):

```
t= 0.7s pitch= -1.60  spd=  0.0     t= 8.7s pitch= -1.64  spd= 58.0
t= 2.3s pitch= -1.40  spd=  9.3     t=12.0s pitch= -1.60  spd= 81.6
t= 5.7s pitch= -1.56  spd= 33.6     t=18.7s pitch= -1.61  spd=109.6
```

Sampling the gate variables explains it. `ApplyLaunchPitch` requires
`PropImmersion > 0.1` and `DriveThrust > 0.1`, but **the propeller is dry for
the first ~2.5 seconds**:

```
t=0.3  thrust=0.0  immersion=0.000  pending=True
t=1.0  thrust=0.0  immersion=0.000  pending=False
t=3.0  thrust=2.2  immersion=0.401  env=0.000
```

`bLaunchPending` is already spent by t=1.0, before the propeller ever bites, so
the one-shot is consumed on a frame that cannot apply torque. After that the
`else` branch zeroes `LaunchPitchEnvelope` every tick and the sustain branch can
never run.

Raising the torque does not fix it, because the shape of the system is wrong
rather than its magnitude. At `launchPitchTorque` 150,000,000 over a 3 s pulse
the hull rocked to -2.31 degrees and then overshot to **+0.39 (bow down)**
before settling back; at 60,000,000 over 25 s the envelope still collapsed to
zero within one sample. A one-shot impulse cannot hold an attitude — it rings
the hull against the pontoon springs and the springs win.

Both experiments were reverted. `launchPitchTorque` is back at 12,000,000 and
`launchPulseSeconds` at 0.8, recorded in
`Saved/Backups/2026-10-02-foam-blend/handling_launch_before.json`.

## What the fix needs to be

A sustained, thrust-proportional bow-up moment while the boat is below planing
speed, not a launch impulse. The existing taper is already the right shape for
it: full torque while pitch is above -3 degrees, falling to zero at -7, which
self-limits at a believable planing attitude.

The smallest version is to let the sustain branch run continuously — the
envelope stops decaying and is re-armed whenever thrust drops rather than being
cancelled — so torque is applied for as long as `DriveThrust > 0.1` and the
propeller is wet. The torque constant then has to be re-tuned against the
pontoon stiffness until the hull settles near -4 to -6 degrees instead of
oscillating.

This was **not** applied. `ApplyLaunchPitch` contains three duplicated copies of
its logic (the same pattern as `UpdateDriveState_0`, where one DSL statement
turned out to be six literal nodes), so changing branch conditions by hand needs
all copies identified first, and this is handling code rather than a visual
tweak. Note also that the dry propeller at rest is a separate issue worth
checking on its own: a long-tail that cannot bite for two and a half seconds
from a standstill will not launch convincingly no matter how the pitch moment is
written.

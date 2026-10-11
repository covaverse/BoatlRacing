# Boat Camera, Drive, and Feedback Design

Date: 2026-09-29
Status: Approved; prototype implemented, with visual and production validation outstanding
Project: `A:\Project\Unreal Engine 5\BoatlRacing`

## Intent and Success

Extend the existing playable long-tail boat into a more legible racing prototype without replacing the assembled 98-part visual asset. The player can select four useful camera views, see the propeller meet the water when applying throttle, rev the engine against a disengaged clutch with Spacebar, then launch when releasing it. Propeller speed, spray, smoke, engine audio, and vibration must respond coherently to the same drive state. The screenshot is a reference for a long white stern spray at speed, not a texture to paste into the game.

## Existing Boundaries

- Keep `/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat` as the modular visual assembly.
- Extend `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn` and test in `/Game/Maps/M_WaterPhysicsTest`. Do not alter the user's `/Game/boat` map.
- The physics root is the low-poly convex hull; visual vibration and camera offsets must not shake the collision body.
- Save the current assets before editing. Compile with warnings as errors and save again after verification.

## Chosen Architecture

Use Blueprint-focused components/functions around the existing Pawn, not a monolithic new Pawn or a C++ rewrite. The drive layer owns engine and shaft state; the camera layer owns mode selection; Niagara and audio components consume read-only state. The physics Pawn remains the authority for buoyancy, force application, and actual boat velocity.

Drive state outputs each frame:

| Signal | Meaning | Consumers |
| --- | --- | --- |
| `EngineRPM` | Smoothed idle-to-redline engine speed | audio, smoke, engine vibration |
| `ShaftRPM` | Clutch-coupled propeller speed with spin-down | visual propeller, available thrust |
| `ClutchEngagement` | 0 while Spacebar held, ramps toward 1 on release | shaft speed, thrust |
| `BoatSpeed` | Magnitude of the rigid body's world velocity in cm/s | spray, wake, optional camera FOV |
| `PropImmersion` | Fraction of propeller below sampled water surface | thrust and water spray gate |

All signals are clamped and exposed for PIE inspection. Input is accepted only from the Pawn's owning local controller, so additional boats do not all read Player 0 input. Test overrides remain disabled in saved instances.

## Drive and Tail Motion

- `W` requests forward throttle; `S` requests reduced reverse throttle. The first throttle input starts the engine with a short transition to idle. It remains idling until the Pawn is shut down or destroyed. Releasing throttle lets RPM fall gradually to idle instead of snapping to zero.
- Holding Spacebar disengages the clutch: the engine may rev with W, but shaft RPM and propulsive force decay to zero. It is not a brake and does not remove existing hull momentum. Releasing Spacebar re-engages smoothly over a short interval so stored engine RPM produces a brisk but bounded launch. No arbitrary impulse or teleport is added.
- Shaft RPM follows coupled engine RPM with response/inertia. Releasing W leaves a brief visible propeller coast-down. Propeller visual rotation is integrated from shaft RPM, not directly from the key state or boat speed. Speed can affect load and VFX, but a moving boat with the engine off does not automatically drive the propeller at full RPM.
- On forward or reverse thrust request, automatic tail deployment seeks a shallow submerged propeller position. Compute the propeller's world position from the actual tail pivot, sample the active Water Body surface, and target about 4 cm below it in the current flat-water prototype. The tail pivot-to-hub distance is 246 cm; verify no mesh collision at the full range. `Q/E` adds a bounded manual trim offset around the automatic target.
- Thrust scales with clutch engagement, shaft RPM/engine torque approximation, and propeller immersion. A dry propeller produces no propulsive force. Keep its force horizontal and apply it at COM height with an aft steering lever arm; do not apply buoyancy or a vertical support force at the propeller. The propeller's measured position is for immersion gating and FX, not a rigid contact constraint. Retain hull buoyancy and lateral resistance until measured tuning justifies a change.

## Cameras and Input

`C` cycles four modes in order; third-person chase is the default:

1. Bow camera near the front, facing along the boat's forward direction.
2. Driver/hood camera behind the bow, framing the visible pointed tip.
3. Third-person chase on a collision-tested spring arm.
4. Free Orbit: follows the boat's position but mouse input rotates freely around it. It is **not** a detached spectator camera. Boat W/A/S/D controls continue to work. Entering or leaving Free Orbit preserves a sensible view direction and blends rather than cutting harshly.

Mouse-wheel adjusts distance only in chase/orbit views within safe limits. Camera transforms remain independent of engine vibration. On-screen controls are not required for this prototype; the bindings are documented in `Docs/HANDOFF.md`.

## Niagara, Audio, and Vibration

- Niagara stern wake/spray: white foam and mist emitted near the propeller and wake. Spawn rate, size, and trail length rise with actual boat speed; water contact and prop immersion gate the propeller spray. At rest it is quiet. Keep particle counts/bounds/scalability conservative for gameplay.
- Niagara exhaust smoke: emitted from the modeled exhaust outlet. Density and velocity follow engine RPM/throttle, including revving with Spacebar held. Smoke is subdued at idle and does not depend on boat speed.
- Placeholder engine audio: a looping test sound with pitch/volume driven by RPM plus a brief startup cue. It is explicitly temporary, spatialized at the engine, and does not use copyrighted footage audio.
- Engine visual vibration: small bounded oscillation of an engine-only visual group during engaged launch and near the speed cap, with a smoothed envelope. It neither changes the physics collider nor detaches engine parts. It is off at steady mid-speed and during stationary clutch-disengaged revving.

## Verification

- PIE idle, forward, reverse, turning, and waterline checks at the saved test spawn.
- `W` deploys the tail so the propeller is at the water surface before appreciable thrust. When the propeller is above water, thrust and prop spray stop.
- Spacebar + W: engine audio/smoke/RPM rise while shaft and thrust remain near zero; the hull is not artificially braked. Release Spacebar: shaft and thrust rise smoothly and the boat accelerates. Release W: propeller coasts briefly, then slows.
- Confirm each camera's framing at the starting position and while turning; Free Orbit remains tethered while the boat moves. Check mouse interaction and camera collision.
- Inspect Niagara at idle, moderate, and high speed; smoke at idle, startup, and held rev. Verify no excessive particles, giant bounds, persistent emitters after stopping, or audio clipping.
- Compile affected Blueprints with warnings treated as errors, inspect PIE logs, and save assets. Request an Astra read-only review; record all unresolved findings in `Docs/STATUS.md` and `Docs/HANDOFF.md`.

## Known Constraints

This pass remains a single-player racing prototype, not a calibrated marine simulator. Water-body sampling and the actual propeller height must be verified against the imported mesh in PIE. The placeholder engine sound is not final production audio. Advanced cavitation, planing, damage, network replication, and race rules are outside this pass.

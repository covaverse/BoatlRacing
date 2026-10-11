# Boat Handling, Stern Trim, Speed, and Waves Design

Date: 2026-09-30
Status: Design for review; not implemented
Project: `A:\Project\Unreal Engine 5\BoatlRacing`

## Intent and Acceptance

The Thai long-tail boat should look and behave engine-heavy at the stern. At rest, its stern sits visibly lower and the bow slightly higher; a rapid forward launch adds a brief, bounded bow-up kick that settles naturally. The long-tail propeller remains a shallow, nearly horizontal drive/animation assembly, never a support point that lifts the hull. Each boat has an editable handling file. Full forward engine power should bring this boat toward 110 km/h on calm water, while momentum and wave-slope energy may briefly carry its horizontal speed beyond that number. Vertical velocity alone must not count as racing speed. The engine vibrates during an engaged launch and while working near its top-speed range. Two additional water test maps demonstrate small and tall waves.

The screenshots are visual references for trim and waterline, not measured displacement or speed data. No exact real-boat mass data was supplied; prototype values remain tunable estimates.

## Existing System and Boundaries

- Keep `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn` as the physics authority and `/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat` as the modular visual child.
- Keep `/Game/Maps/M_WaterPhysicsTest` as a flat-water baseline and leave `/Game/boat` untouched.
- The current hull and engine masses are 270 and 180 kg. With hull center X=-20 cm and engine center X=+230 cm, their weighted center is X=+80 cm. The collider volume centroid is X=+75.78 cm, so the present COM nudge is only +4.22 cm. The combined center of gravity is **not** at the engine: it is the mass-weighted average of hull, engine, fuel, driver, and other contents. The prototype currently models only hull and engine masses.
- Hull pontoons alone supply buoyancy. The propeller world position gates immersion, thrust, and spray. Neither the shaft nor the hub applies an upward support force or collision constraint against the water.
- Present `BoatSpeed` is a three-dimensional velocity magnitude. Replace speed used for racing and engine limiting with horizontal ground speed so a drop or jump does not register as forward racing speed.

## Chosen Architecture

Use an Unreal-native Blueprint Data Asset class, `BP_BoatHandlingData`, and one asset `DA_ThaiLongtail_Handling` under `/Game/Boats/ThaiLongtail/Handling/`. The Pawn exposes a `HandlingProfile` reference and loads it once at BeginPlay into validated runtime settings. A future boat gets its own Data Asset without duplicating the entire Pawn. Do not create a second fictional boat asset in this pass. Missing or invalid profile values use documented safe defaults and produce a warning rather than silently disabling physics.

The profile owns mass split and mass-center positions, front/rear buoyancy tuning, forward thrust, lateral and quadratic drag, forward engine target speed, governor onset, launch pitch impulse/decay, and vibration thresholds. Camera settings, input bindings, visual meshes, and wave presets are outside the handling profile. Keep units in names or tooltips: kilograms, centimeters, cm/s, km/h, newton-centimeters/Unreal torque units as appropriate. The Pawn remains responsible for physics forces and water sampling; the data asset is configuration only.

The alternatives considered were child Pawn Blueprints with overridden defaults (simple for one boat but duplicates graph behavior) and external JSON (diff-friendly but needs a loader, packaging rules, and runtime validation). A Data Asset fits the existing Blueprint project and Content Browser workflow with the least new infrastructure.

## Mass, Buoyancy, and Launch Pitch

Compute desired longitudinal COM from the weighted hull and engine centers, then convert it to the collision mesh's required COM offset. Keep the engine center near the visual engine, not at an arbitrary position chosen only to force trim. Tune the estimated mass split and aft pontoon support together until a settled, hands-off flat-water boat shows roughly 2.5-4 degrees bow-up (negative pitch in the current coordinate setup), stern visibly deeper than bow, and neither end unnaturally airborne. Record the final measured PIE values in `Docs/WATER_PHYSICS.md`.

On a rapid increase in **engaged forward drive**, add a short pitch torque to the hull to suggest inertial/planing weight transfer. Drive the envelope from positive drive-force change or longitudinal acceleration, only while the hull is in water; decay it over about 0.3-0.6 seconds. Scale it down as pitch approaches a tested limit, and do not fire for reverse, dry propeller, or Space-held clutch revving. This is an explicit gameplay approximation to distributed hull-water forces. It is not a vertical propeller force, a rigid pitch lock, or a permanent nose-up torque. Validate the sign and magnitude in PIE: rapid W should give a noticeable but small extra bow rise, then return near the static trim without oscillation.

The propeller's 246 cm pivot-to-hub span remains unchanged. Continue sampling the moving water surface and seeking shallow immersion; verify the visible shaft remains near horizontal through launch and wave peaks. If the hub leaves water, thrust and prop spray fall away naturally.

## Speed and Engine Feedback

Define `ForwardSpeedKmh = sqrt(Vx^2 + Vy^2) * 0.036` from the hull's world velocity. Retain vertical velocity separately for water-entry and wave response; do not use it to trigger the engine speed limiter. The handling profile sets `TargetForwardSpeedKmh=110` and a lower `GovernorStartKmh` (initially about 105). Between those speeds, available positive engine thrust progressively falls toward a level that balances calm-water drag near 110; above the target, available drive falls below drag so the boat gradually returns toward the target. Never clamp or overwrite the body's linear velocity. Existing hydrodynamic drag, momentum, wave slope, and gravity can therefore carry the boat briefly above 110 or let it coast. Reverse behavior is independent of this forward target.

Tune thrust and drag on a sufficiently large flat-water test course so sustained full W approaches about 110 km/h without a sharp sawtooth or sudden stop. The preexisting 220,000 force and -0.055 quadratic drag are uncalibrated starting values, not accepted final constants. Record time-to-speed and steady-speed samples; discard any sample after leaving the Water Body.

Keep engine vibration off during stationary Space-held revving and ordinary mid-speed cruising. Allow a brief engaged-launch pulse, then ramp vibration in the high-speed band (initially around 108 km/h), provided the engine is under forward load. If a wave carries the hull to 111 km/h with W held, the same top-speed envelope remains active; coasting with no engine load should not shake the engine as though it were accelerating. Shake only the engine visual group, not the collision body or camera.

## Wave Test Maps

Preserve the flat baseline. Duplicate it into `/Game/Maps/M_WaterSmallWavesTest` and `/Game/Maps/M_WaterHighWavesTest`, each with its own Water Body wave configuration using the installed Gerstner Water Waves generator. Start with small component amplitudes around 5-15 cm and tall component amplitudes around 25-70 cm, then measure actual combined crest/trough heights because overlapping waves do not equal a single component amplitude. Use fixed seeds for repeatable tests. Extend the usable water test area enough for sustained full-throttle runs without driving off its finite collision/physics coverage, while checking the Water Zone mesh and performance cost.

Both maps use the same boat handling profile and spawn. Visually changing only the material normal map is insufficient: the Water Body height queried by buoyancy and the propeller must move with the waves. High-wave testing is for response and stability, not a promise that the boat can race at full speed through every crest. Keep the two wave maps optional tests; do not change the project's startup map until they pass.

## Verification and Failure Handling

1. Save affected assets before and after edits. Compile changed Blueprints with warnings treated as errors; keep PIE stopped when saving.
2. Flat-water idle: measure COM, mass override, bow/stern waterline, pitch, propeller hub depth, and absence of propeller support force.
3. Rapid W and Space-release launch: record speed, pitch peak, settling time, shaft angle, and hub depth. Confirm no persistent stern lift and no pitch kick during dry-prop or disengaged-clutch conditions. Repeat S and A/D to catch regressions.
4. Flat-water full W: record horizontal speed in km/h at timed intervals, target-speed behavior, overshoot/coast, and high-speed engine vibration. Check that vertical falls do not inflate racing speed. Confirm the limiter reduces *drive*, never body velocity.
5. Small/tall wave maps: sample the Water Body height and hull response at multiple positions; test buoyancy, prop immersion, spray, steering, and recovery after crests. Capture side-view evidence at idle, launch, near 110 km/h, and in both wave profiles.
6. Ask Astra for a read-only review after the implementation and after any corrective pass. Record verified results, remaining risks, and exact asset paths in `Docs/STATUS.md`, `Docs/HANDOFF.md`, and `Docs/WATER_PHYSICS.md`.

## Out of Scope and Risks

This pass does not add a driver/fuel mass simulation, damage, cavitation, network replication, or race rules. The present convex collision hull and pontoon layout are approximations; changing collider geometry later requires recomputing its centroid. Water visuals and physics sampling must agree in the wave maps. The Blender master still needs a proper long-shaft reauthoring pass; this handling work does not alter the imported geometry or 4K source textures.

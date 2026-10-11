# BoatlRacing Handoff

## Current Resume Point

- 2026-10-02 (later): exhaust smoke, foam blending and ripple domain changed and saved; impulse forcing was raised then **restored to its original values** because it produced ring-shaped wakes. Read [FX and water evidence](Work/2026-10-02-foam-smoke-ripple.md) first. The fluid simulation's hard rectangular border is the open item.
- The native GPU-ripple-to-buoyancy code exists but has **never been compiled**: no Visual Studio / Windows SDK on this machine. Do not treat it as working. See [GPU ripple buoyancy](Work/2026-10-02-gpu-ripple-buoyancy.md).
- `CaptureViewport` through MCP renders the **editor** world, not PIE. To see a moving boat, start PIE with `PlayMode_InViewPort` and use `CaptureEditorImage`. Setting `bVisible` on a Niagara component does not stop it emitting.


- Use the latest STATUS and water-contact work note. Water foam now blends opacity toward .95, using native tiled foam on real GPU displacement. Idle bow/engine-off prop droplets are hidden; bow threshold is 80 cm/s, rate 130*speedAlpha. Handling support radii are restored to 60/55 cm.
- The active OpacityMask is BoatMeasuredCavity, using T_BoatDryProfile (532x8) and MPC_BoatContactFrame (four vectors), updated in UpdateFXState_0. Controlled flat draft at root Z365/water400 shows dry liner; mask-off comparison shows water across it. This is one unit-scale boat per world, measured open rim, no flooding model. Do not claim high-wave, multiplayer, or spawn/despawn acceptance. Clearing Origin on EndPlay is needed before runtime boat deletion.
- Source scripts prepare_mask_probe.py/capture_mask_probe.py are PIE-only and must not save their freeze/location overrides. Older DF prototype is disconnected; unused replacement geometry still exists. The eight-slot core below is separate and unintegrated.

## Earlier fitted-volume mask checkpoint

- Start at [Docs/README](README.md). [PROJECT_MAP](Guides/PROJECT_MAP.md) locates actual assets/functions/source/tools; [HANDLING_GUIDE](Guides/HANDLING_GUIDE.md) covers all 18 fields, units, weighted COM, per-boat profiles, Q coast steering, soft governor, and safe testing.
- User deferred further document review and requested implementation first, MD updates afterward. Follow [the execution plan](Plans/2026-09-30-moving-hull-water-mask.md); do not ask the same written-spec approval again. The historical eight-slot mask is **not yet installed**; the current single-boat profile mask is described above.
- Completed reference core: `Private/BoatInteriorMaskMath.h`, 121 standalone MSVC checks / 0 failures. Height knots replace an unsafe single width chord, and handles include per-registry identity. No UE runtime adapter exists yet.
- Completed sampled inner-liner survey and parser hardening: 532 X sections / 4,256 height points, 4,279 standalone checks / 0 failures, five GLB rejection fixtures. These are not Unreal Automation results. Read [WATER_MASK_DEVELOPMENT](Guides/WATER_MASK_DEVELOPMENT.md) before using the geometry data; it is not a certified containment oracle or profile asset.
- Next code task: fit/verify the dry profile against wall triangles, visible floor and transom, including between-station interpolation. Then implement per-World slot publishing and project-owned water material integration. Do not activate a guessed box or the single-section fixture.
- MCP briefly lost its client tool catalog, then returned. Fresh discovery, real `IsPIERunning=false`, property calls and saves succeeded. No Editor termination/discard was used. No reconnect request remains pending; inspect current map before integration rather than assuming it.
- Saved inert MPC `/Game/Water/Materials/MPC_BoatInteriorMasks`: 416 vector / 2 scalar parameters, unique IDs/names/defaults verified; all slots/global enable are off. See [readback](Work/2026-09-30-water-mask-mpc-readback.json) and [packing contract](Guides/WATER_MASK_DEVELOPMENT.md). Do not reset/recreate it blindly; native uploader and shader must use these same names/layout.

## Open and test

1. Open `A:\Project\Unreal Engine 5\BoatlRacing\BoatlRacing.uproject` in Unreal Engine 5.8.3. The editor startup map is `/Game/Maps/M_WaterPhysicsTest`.
2. Press Play in the viewport and click it for keyboard focus. Use `W/S` forward/reverse, `A/D` steering, `Q/E` tail trim, hold `Space` to rev with the clutch disengaged, and press `C` to cycle bow, driver, chase, and boat-following Free Orbit cameras. The placed Pawn auto-possesses Player 0.
3. The original `/Game/boat` level was not changed. Do not reimport the GLB without a deduplication plan; all 98 parts are already assembled in `/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat`.

## Key assets and boundaries

- Physics Pawn: `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn`.
- Visual child Actor: `/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat`.
- Simple Chaos collider: `/Game/Boats/ThaiLongtail/Physics/SM_BoatPhysicsHull`.
- Handling data: `/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling` (data class `BP_BoatHandlingData`). For another boat, duplicate and assign this asset on its Pawn/child Blueprint. `ConfigureBoatMass` loads/validates it, applies mass/COM, then uses the native runtime pontoon setter. Keep four hull support points in front/front/rear/rear order. Invalid profiles warn and retain safe defaults.
- Test maps: `/Game/Maps/M_WaterPhysicsTest` (flat baseline), `/Game/Maps/M_WaterSmallWavesTest`, and `/Game/Maps/M_WaterHighWavesTest` (Gerstner stress test). The project startup map remains flat; `/Game/boat` was not changed.
- Niagara: `/Game/Boats/ThaiLongtail/FX/NS_LongtailWake`, `NS_LongtailPropSpray`, and `NS_LongtailExhaust`.
- Placeholder audio: `/Game/Boats/ThaiLongtail/Audio/SW_LongtailEngineTest` and `SW_LongtailStartTest`; source WAVs and generator are under `SourceAssets/Audio` and `Tools/generate_engine_test_audio.py`.
- Formulae, tuning numbers, test observations, and known physics gaps: `Docs/WATER_PHYSICS.md`.
- Mechanical pivot details and Astra's prior visual-assembly findings: `Docs/BOAT_ASSEMBLY.md`.

## Next engineering steps

1. Current handling asset uses 250 kg hull + 200 kg engine, mass-weighted COM X=+108.89 cm aft/Z=-20 cm, and rear pontoon radii 55 cm (front 60 cm). A Simulate body readback gave mass 450 kg and collider-relative COM offset `(33.111,0,-25)` cm. The long-tail pivot-to-hub span remains 246 cm. Propulsion force is horizontal and applied at runtime COM world Z, removing **direct** pitch/roll torque from the propeller; hull pontoons alone supply buoyancy. The small-wave map's stale 48 cm aft pontoon override was fixed by replacing its Pawn while preserving placement/profile/Player 0. Small-wave idle pitch then sampled about -1.4 to -2.2 degrees. High-wave idle is still a stress case, not accepted racing behavior. These are gameplay values, not measured boat data.
2. Migrate keyboard polling to Enhanced Input for ownership, gamepad, and rebinding. Remove or guard test override before shipping.
3. The flat Ocean course was enlarged; a bounded wet full-W sample reached 110.10 km/h with high-speed vibration active. The soft governor reduces positive drive rather than clamping rigid-body velocity, so 111+ km/h remains possible from waves or momentum. Repeat timed acceleration/coast and rough-water drive/steering tests before acceptance. Add a proper torque/RPM curve and planing model. Do not interpret the current mass split or water coefficients as measured specifications.
4. Test collision against obstacles, then add damage and impact feedback. Measure draw calls, LODs, texture memory, and hull-vs-visual alignment before declaring game ready.
5. Refine the visual control rod and shaft-axis alignment noted in `Docs/BOAT_ASSEMBLY.md`.
6. Replace synthetic test audio after listening for clipping and loop seams. Refine Niagara spray appearance and measure particle budget. Engine vibration is now deliberately off during stationary `W+Space` revving and steady mid-speed; it runs only during engaged launch and high-speed operation.
7. Reauthor the long shaft in the Blender master and regenerate UVs before reimporting; the current Blueprint uses X scale 1.5 on the imported inner shaft and outer sleeve. Avoid a blind reimport, which could shorten the assembled shaft or duplicate assets. A PIE side capture confirmed the low-speed silhouette, but bearing seating, full yaw/trim clearance, and fast-water appearance still need inspection.
8. Native bridge is wired and saved: `SampleWaveSurface` at the actual hub, `SetHullPontoonRadii` after initialization, and `CalculateTailWaterForce` for immersed-tail coast steering. Live 59/54 cm testing proved runtime radii; restored 60/55 cm. Current filtering is now built/tested: only enabled River flow is used; Ocean/Lake metadata is ignored. Live rest and left/right/raised-tail coast snapshots verified the new DLL. Finish timed coast tuning, reverse/clutch cases, river/shoreline/exclusion tests, and rough-water acceptance.
9. Run controlled launch/dry-prop/clutch/reentry and bow-pitch measurements after the Astra-reviewed pulse fix. The envelope now cancels when ineligible and torque scales down between -3 and -7 degrees bow-up, but visual magnitude and all edge cases remain unaccepted. Recheck saved test-input overrides and stop PIE before closing.

## Resume Checkpoint: Native Bridge

- User saved/closed the Save Content dialog normally. Plugin build and tests passed; Editor reopened with the flat map, PIE stopped. Do not force-kill or discard packages during future rebuilds.
- Latest native report: `Saved/Automation/WaterCurrentGreen/index.json`, 4 passed / 0 failed. RED report caught PhysicalCurrent and TailInvalidInput failures before fixes. Astra found no remaining blocker in the corrected source. Actual Ocean query read zero current; immersed coast turns both ways and raised-tail coast does not add yaw in the sampled runs.
- Raw batched runtime evidence: `Docs/Work/2026-09-30-water-current-regression.json`. Timestamp is wall time, not fixed simulation time. Do not derive calibrated handling targets from it. Small-wave hub samples varied 361.94-395.95 cm; wave physics/rendering acceptance remains open.
- Backups: `Saved/Backups/2026-09-30-native-bridge/`. Applied source: `Tools/BlueprintDSL/WaterBridge/` water, tail, mass, profile functions. `UpdateDriveState_0.dsl` there is an **unapplied candidate**, rejected by auto-review; do not bulk-import it. World-age QA timing requires fresh Simulate.
- `Tools/inspect_boat_water_runtime.py` is read-only. Check its completion marker: unrelated GameFeatureData configuration can cause exit code 1. `Tools/integrate_boat_water_bridge.py` is editor-only and not yet verified as a complete reproduction of accepted MCP edits.
- Actual water material is SingleLayerWater / Masked. `ClipDynamicBounds` clips an XY rectangle, not a moving tapered hull; no hull mask was implemented. Keep rendering intrusion separate from real sinking. Do not globally hide water or add propeller buoyancy.

## MCP and Skills

- Live MCP endpoint: `http://127.0.0.1:8000/mcp`; `ModelContextProtocol`, `AllToolsets`, `PythonScriptPlugin`, and `EditorScriptingUtilities` are enabled.
- Installed Epic skills: `unreal-mcp`, `unreal-skill`, and `create-toolset` at `C:\Users\LEONIDASxII\.codex\skills`. Read `unreal-mcp/SKILL.md`, list toolsets, then load the relevant Agent Skill before making Editor changes.
- `BlueprintBasicsSkill` was used for this Blueprint pass. Save the map and assets before closing the Editor.

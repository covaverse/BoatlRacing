# Boat Handling and Wave Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the existing Thai long-tail boat stern-heavy trim, a brief forward-launch bow kick, per-boat handling data, a soft 110 km/h engine target, and two physically sampled wave test maps.

**Architecture:** Keep the existing physics Pawn and modular visual Actor. A Blueprint Data Asset supplies per-boat constants; the Pawn validates and caches them at BeginPlay, then applies hull-only buoyancy/torque and speed-dependent drive. Separate Water Waves assets and map copies preserve the flat-water baseline.

**Tech Stack:** Unreal Engine 5.8.3, Blueprint, Water/Buoyancy and Gerstner Water Waves, Chaos, live Unreal MCP, PIE.

**Spec:** `Docs/Specs/2026-09-30-boat-handling-waves-design.md`

## Execution Snapshot (2026-09-30)

- [x] Added Thai [project map](../Guides/PROJECT_MAP.md) and [Handling manual](../Guides/HANDLING_GUIDE.md) documenting actual files and the earlier confirmed tuning checkpoint.
- [x] User approved the moving coordinate-local water-mask approach, then deferred further document review and requested work first / MD afterward. [Mask execution plan](2026-09-30-moving-hull-water-mask.md) tracks the new work; do not repeat the old approval gate.
- [x] Reference mask core passed 121 standalone MSVC checks; sampled inner-liner survey passed 4,279 checks plus five GLB rejection fixtures. Astra reviewed both scopes. These do not complete the water-mask task below: no runtime/shader hookup or in-game acceptance yet.

- [x] Handling Data Asset, 450 kg weighted COM, profile-driven drive/quadratic/lateral drag, horizontal-speed soft governor, and loaded high-speed vibration are implemented. A wet flat-water PIE sample reached 110.10 km/h; the current COM nudge readback is `(33.111,0,-25)` cm.
- [x] Flat course extension and separate Small/High Gerstner maps are saved. A stale Small-map 48 cm aft-pontoon instance override was fixed; its saved actor now reads 60/60/55/55 and Simulate idle no longer sinks uncontrollably.
- [x] Launch-pulse dry/reentry cancellation and bow-up torque taper were graph-reviewed by Astra and compile with warnings as errors.
- [ ] Finish acceptance testing for timed launch pitch/decay, S/Space/dry-prop, coasting, steering, and sustained wet speed.
- [x] Replace the aft-pontoon average with native `IncludeWaves` sampling at the actual hub, including coverage/exclusion guards. Live Blueprint wiring is compiled/saved; rough-wave accuracy acceptance remains open.
- [x] Apply profile pontoon radii at runtime after initialization. Temporary 59/54 profile produced actual 59/59/54/54 component radii in Simulate; restored 60/55 and saved.
- [x] Wire bounded native water-relative tail drag and validate profile fallback for negative coefficients. Blueprint compile/save and 3-test native GREEN report recorded.
- [x] Filter Ocean spline metadata from physical tail current and guard extreme arithmetic. Actual RED: 2 passed / 2 failed; GREEN: 4 passed / 0 failed. Live new-DLL rest, immersed left/right coast and raised-tail comparison sampled correctly. Timed handling acceptance remains open.
- [ ] Implement and visually validate the moving dry-hull water mask. Material inspection alone did not fix water intrusion.
- [ ] Tune the high-wave stress map for controlled racing or document it as deliberately non-raceable, and perform human visual/FX tests.

The detailed task checkboxes below remain open until their full acceptance criteria are proven; this snapshot records implemented substeps without claiming the whole tasks complete.

## Global Constraints

- Preserve `/Game/boat`, the 98-part visual assembly, and the 246 cm pivot-to-hub shaft span.
- Only hull pontoons provide buoyancy. The propeller never applies vertical support force.
- 110 km/h is a calm-water engine target, not a rigid-body velocity clamp; horizontal speed is used for racing and limiting.
- Keep `/Game/Maps/M_WaterPhysicsTest` flat as the baseline. The two wave maps are additional test maps, not startup replacements.
- Save affected Unreal assets before and after each task, compile changed Blueprints with warnings as errors, and stop PIE before saving.
- This directory has no Git repository. Record each completed task and its evidence in `Docs/Work/2026-09-29-execution-ledger.md`; do not claim commits.

## Review Focus

1. A missing or invalid handling asset must fall back to safe documented values with a warning, not remove mass, drag, or thrust. Task 1 tests this.
2. Vertical falling or wave heave must not inflate racing speed or prematurely invoke the governor. Task 4 tests this.
3. Dry propeller and Space-held clutch revving must not trigger launch torque, propulsive thrust, or launch vibration. Task 3 tests this.
4. A wave map must move the queried water height used by buoyancy and the propeller, not only the material surface. Task 2 tests this.
5. A boat crossing 110 km/h on a wave must retain physical momentum and return gradually; no `SetPhysicsLinearVelocity` cap or sawtooth. Task 4 tests this.

---

### Task 1: Per-Boat Handling Profile

**Files:**
- Create: `Content/Boats/ThaiLongtail/Handling/BP_BoatHandlingData.uasset`
- Create: `Content/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling.uasset`
- Modify: `Content/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn.uasset`
- Update evidence: `Docs/Work/2026-09-29-execution-ledger.md`

**Interfaces:**
- Produces `HandlingProfile: BP_BoatHandlingData` on `BP_LongtailPhysicsPawn` and `LoadHandlingProfile(): void`, called before `ConfigureBoatMass()` at BeginPlay.
- The asset defines float fields `HullMassKg`, `EngineMassKg`, `HullCenterXcm`, `EngineCenterXcm`, `CenterZcm`, `FrontPontoonRadiusCm`, `RearPontoonRadiusCm`, `DriveForce`, `LateralDrag`, `QuadraticDrag`, `GovernorStartKmh`, `TargetForwardSpeedKmh`, `CruiseThrustScaleAtTarget`, `OverspeedFadeKmh`, `LaunchPitchTorque`, `LaunchPulseSeconds`, and `VibrationStartKmh`.
- Validated values are cached on the Pawn for Tasks 2-4; no per-frame hard asset load or alternate physics authority.

- [ ] **Step 1: Record the failing baseline.** Via live MCP, confirm `AssetTools.exists` is false for the profile assets and `BlueprintTools.list_variables` has no `HandlingProfile`; save the Pawn/map before mutation.
- [ ] **Step 2: Create the profile class and asset.** Parent the class to `DataAsset`; add the named float fields, compile, then create `DA_ThaiLongtail_Handling`. Start with 250 kg hull, 200 kg engine, hull X=-20 cm, engine X=+230 cm, center Z=-20 cm, front/rear pontoon radii 60/53 cm, DriveForce=220000, LateralDrag=1200, QuadraticDrag=0.055, target/governor/vibration 110/105/108 km/h, cruise scale at target=0.7, overspeed fade=6 km/h, launch torque=4,000,000 Unreal torque units, and launch pulse=0.4 s. Force/drag/torque are prototype seeds to be tuned in Tasks 3-4, not accepted final values. Assign this asset on the Pawn CDO and confirm the placed actor inherits it.
- [ ] **Step 3: Add and wire `LoadHandlingProfile()`.** Add a typed object reference to the Pawn and validate positive mass/radii/force, nonnegative drag, and `0 < GovernorStartKmh < TargetForwardSpeedKmh`. Load before mass configuration. On missing/invalid data, keep the current safe Pawn defaults and log a warning rather than zeroing runtime settings.
- [ ] **Step 4: Verify the profile contract.** Re-read the asset values and graph, compile with warnings as errors, and run a short PIE check: mass override equals the selected profile total (450 kg). On an unsaved test instance, unset the profile, then assign a temporary profile with EngineMassKg=0; each case must warn and retain safe nonzero defaults. Restore the saved valid reference and values before leaving the task.
- [ ] **Step 5: Save and record.** Save both profile assets, the Pawn, and map; note exact values, fallback result, and any inherited-instance override in the execution ledger.

### Task 2: Reliable Water Course and Two Wave Presets

**Files:**
- Create: `Content/Water/Waves/WW_SmallGerstner.uasset`
- Create: `Content/Water/Waves/WW_HighGerstner.uasset`
- Create: `Content/Maps/M_WaterSmallWavesTest.umap`
- Create: `Content/Maps/M_WaterHighWavesTest.umap`
- Modify only as needed for coverage: `Content/Maps/M_WaterPhysicsTest.umap`
- Update evidence: `Docs/Work/2026-09-29-execution-ledger.md`

**Interfaces:**
- Produces three separate maps with the same boat spawn/profile: flat, small waves, high waves.
- Each wave map's WaterBodyOcean uses its own Water Waves asset; buoyancy and propeller sample that actor's moving surface.

- [ ] **Step 1: Establish a failing course/wave check.** In the flat map, measure wet-water coverage from the spawn along the forward (-X) path and record the prior full-W water-exit failure. Confirm the current Ocean has `waterWaves=None` and surface samples are flat.
- [ ] **Step 2: Secure the flat-water speed course.** Extend the Ocean collision/physics coverage and Water Zone only as much as needed to provide at least 1,200 m of continuous wet path along the test heading. Requery multiple points before duplicating the map; check tile/render cost. Keep waves disabled in this baseline.
- [ ] **Step 3: Create reproducible wave assets.** Create Water Waves assets through the Water content workflow. Start each with eight Gerstner components: small seed=17, wavelength 600-2500 cm, amplitude 5-15 cm; high seed=29, wavelength 1800-8000 cm, amplitude 25-70 cm. Tune steepness only if the first PIE pass looks unstable, keep seeds fixed, and document actual sampled combined crest/trough ranges. Epic's Water Waves asset model, rather than shader-only normal animation, must drive the Water Body.
- [ ] **Step 4: Duplicate maps and assign waves.** Copy the saved flat map to the two named test maps; assign one wave asset to each Ocean via its Water Waves asset reference. Preserve the boat spawn, profile, controls, and flat startup map.
- [ ] **Step 5: Verify and save.** At several positions and times in each map, query the Water Body height and visually confirm the hull responds. Small and high profiles must differ measurably; propeller immersion should track the same surface. Save maps/assets and record paths, generator parameters, sampled ranges, and remaining water-mesh cost.

### Task 3: Stern-Heavy Static Trim and Short Launch Torque

**Files:**
- Modify: `Content/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn.uasset`
- Tune: `Content/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling.uasset`
- Update evidence: `Docs/WATER_PHYSICS.md`, `Docs/Work/2026-09-29-execution-ledger.md`

**Interfaces:**
- Consumes Task 1's cached mass centers, pontoon radii, `LaunchPitchTorque`, and `LaunchPulseSeconds`.
- Produces `ApplyLaunchPitch(DeltaSeconds: float): void`, `PreviousDriveThrust: float`, and `LaunchPitchEnvelope: float` on the Pawn.

- [ ] **Step 1: Record the failing baseline.** In PIE on flat water, capture settled pitch (currently about -1.61 degrees), bow/stern waterline, shaft angle, hub depth, and the pitch response to a rapid W press and Space release. Confirm the current propulsion still has zero world-Z force and COM-height application.
- [ ] **Step 2: Make COM and buoyancy profile-driven.** Compute desired X COM from the mass-weighted hull/engine centers, subtract the existing collision-mesh centroid when calling `SetCenterOfMass`, and apply profile front/rear pontoon radii. Retain the runtime COM-height horizontal thrust and hull-only buoyancy.
- [ ] **Step 3: Add bounded launch torque.** On a rising engaged positive `DriveThrust`, build a short envelope, decay over `LaunchPulseSeconds`, and apply torque about the hull transverse axis only while afloat. Suppress it for S, dry prop, and Space-held clutch. Reduce torque as bow-up pitch approaches the tested maximum; never add vertical prop force or persistent nose-up torque.
- [ ] **Step 4: Tune and verify.** Adjust the profile values against side-view PIE evidence until settled pitch is roughly -2.5 to -4 degrees, rapid W adds a small visible bow rise, and the response returns near static trim without repeated oscillation. Verify reverse, both steering directions, dry-prop, and clutch cases; note actual measured values rather than assuming the initial profile numbers pass.
- [ ] **Step 5: Compile, save, and record.** Compile warning-as-error, stop PIE, save Pawn/profile/map, and update the physics documentation and ledger with COM math, torque sign/magnitude, and screenshots or measured positions.

### Task 4: Soft 110 km/h Drive and High-Speed Engine Vibration

**Files:**
- Modify: `Content/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn.uasset`
- Tune: `Content/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling.uasset`
- Update evidence: `Docs/WATER_PHYSICS.md`, `Docs/Work/2026-09-29-execution-ledger.md`

**Interfaces:**
- Consumes Task 1's drive/drag/governor/vibration fields and Task 2's flat-water course.
- Produces `ForwardSpeedKmh: float` from horizontal hull velocity and `GetGovernorDriveScale(SpeedKmh: float): float` used only on positive engine thrust. Existing `BoatSpeed` consumers are switched to the horizontal metric or explicitly kept in cm/s with documented conversion.

- [ ] **Step 1: Record the failing baseline.** In PIE, measure horizontal and 3D speed at idle and full W. Confirm current `BoatSpeed` can include vertical falling speed, the drive force is a fixed 220,000 baseline, and vibration starts above 900 cm/s rather than near 110 km/h.
- [ ] **Step 2: Implement horizontal speed and a soft power curve.** Compute horizontal `ForwardSpeedKmh = sqrt(Vx^2+Vy^2)*0.036`. `GetGovernorDriveScale` returns 1 below `GovernorStartKmh`, blends smoothly toward `CruiseThrustScaleAtTarget` by `TargetForwardSpeedKmh`, and fades toward 0 across `OverspeedFadeKmh` above target; use it only on positive drive and tune the cruise scale to balance drag near 110. Do not call `SetPhysicsLinearVelocity` or otherwise clamp body velocity. Keep reverse thrust and Space clutch behavior intact.
- [ ] **Step 3: Tune calm-water force and drag.** Run bounded timed full-W tests while still inside the Water Body, tuning `DriveForce` and `QuadraticDrag` in the handling asset until sustained speed approaches 110 km/h without a large oscillation. Record acceleration samples and reject samples after water exit.
- [ ] **Step 4: Update engine vibration.** Preserve the short engaged-launch envelope from Task 3 and add a high-speed band starting near 108 km/h only when W is held and the engine/shaft are loaded. The engine visual group shakes; collider and camera do not. No high-speed vibration while coasting with throttle released or revving against Space.
- [ ] **Step 5: Verify edge cases and save.** Test wave or downhill overspeed (111+ km/h may occur), release W to observe physical coast, and verify vertical heave alone does not alter the displayed/governed horizontal speed. Repeat W+Space, S, A/D, and dry-prop checks. Compile, stop PIE, save, and record measured speed/vibration behavior.

### Task 5: Rough-Water Regression, Astra Review, and Handoff

**Files:**
- Modify: `Docs/STATUS.md`
- Modify: `Docs/HANDOFF.md`
- Modify: `Docs/WATER_PHYSICS.md`
- Modify: `Docs/Work/2026-09-29-execution-ledger.md`
- Modify affected Unreal assets only if review identifies a reproducible defect.

**Interfaces:**
- Consumes the maps and Pawn/profile from Tasks 1-4; produces a saved, documented test state with PIE stopped.

- [ ] **Step 1: Test small and high waves.** Run idle, W launch, moderate turns, prop immersion, and recovery after crests in both maps. Log water-height samples, pitch/roll limits, FX behavior, and any capsize or water-exit failure.
- [ ] **Step 2: Review the implementation.** Ask Astra for read-only review of profile loading, COM calculation, propeller non-support, torque gating, speed curve, and wave-map assignments. Fix reproducible blocking defects and repeat the relevant PIE check; request Astra to recheck each corrective pass.
- [ ] **Step 3: Final technical verification.** Compile every changed Blueprint with warnings as errors; verify all assets/maps save, startup map remains flat, test override is disabled on the saved Pawn, and PIE is stopped. Record unresolved realism/performance limitations explicitly.
- [ ] **Step 4: Update handoff.** Document profile path and per-boat workflow, three map paths, control keys, current measured masses/COM/trim/speed/wave values, test procedure, Astra findings, and next engineering steps in STATUS, HANDOFF, WATER_PHYSICS, and ledger.

### Task 6: Small-Wave Hull Contact and Visible Water Intrusion

**Goal:** A small wave changes buoyancy and hull attitude according to mass, speed, and local water height without producing runaway sinking. Water must not visibly draw through the open hull interior merely because the Water Body surface crosses its silhouette. Deliberate swamping/submersion is a separate future gameplay rule, not a rendering fix.

- [ ] **Step 1: Reproduce separately.** Record a fixed-camera idle and moving run in the small-wave map, including hull pitch/roll/Z, four pontoon water heights and immersion, velocity, prop hub height, and a screenshot of the visible water boundary. Classify each failure as real loss of buoyancy, water-surface rendering through the cockpit, or both. Do not edit a running Simulate actor's test-input properties; set them before Simulate.
- [ ] **Step 2: Correct physical contact.** Use wave-inclusive local samples for the four hull support points and the prop hub, validate pontoon radii and saved actor overrides, and tune displacement/damping for 450 kg against flat and small waves. Preserve natural heave and fore-aft trim; do not lock Z/pitch/roll or use the propeller as support. Test idle, low-speed, 30/60/110 km/h, coast, reverse, and wave entry/exit.
- [ ] **Step 3: Correct the visual boundary.** Inspect the actual Water Body material/depth path and choose a moving-boat-compatible mask or boat-interior exclusion method. It must hide water only inside the dry hull volume; water outside the hull, spray, wake, underwater view, and genuine submersion must remain visible. A static WaterBodyExclusionVolume is not sufficient for a moving boat without proven runtime support.
- [ ] **Step 4: Verify and review.** Capture side, bow, and cockpit views on flat/small/high maps, with and without motion. Measure maximum unwanted water intrusion and physical draft, compile/save, and ask Astra to review each corrective pass. If the wave query or moving mask requires C++, add concise Thai comments at the non-obvious physics/rendering logic.

### Task 7: Coast Steering with Q-Immersed Long Tail

**Goal:** With W released, A/D alone should have little or no turning authority when the shaft is clear. While the boat still has forward momentum, holding Q to immerse the tail plus A/D should create a gradually decaying hydrodynamic turn; at zero speed it must not rotate in place.

- [ ] **Step 1: Establish baseline.** At matched starting speeds, compare W+A/D, coast+A/D, and coast+Q+A/D. Record forward and lateral velocity, shaft trim/yaw, hub immersion, yaw rate, and turn radius. Repeat in reverse to establish sign.
- [x] **Step 2: Add water-load steering.** Native bounded horizontal drag opposes the immersed tail's water-relative crossflow; force/point-velocity share hub X/Y and COM Z. Powered steering remains separate. Rest/dry/raised cases have automated coverage; live immersed left/right and raised-tail coast snapshots are recorded. Only enabled River flow supplies physical current. Forward/reverse calibrated authority acceptance is still Step 3.
- [ ] **Step 3: Tune and verify.** Test Q+left/right after releasing W at low and high speed, coast without Q, Space-held clutch, dry prop, reverse, and waves. Avoid instantaneous yaw or a hard velocity clamp. Put per-boat coefficients in the handling profile, document units, and request Astra review. If a C++ helper is necessary for water sampling or force calculation, comment the subtle portions in Thai.

### Task 8: Re-tune Momentum and Handling Acceptance

- [ ] **Step 1: Measure timed flat-water W acceleration to approximately 110 km/h and W-release coast at 110/60/30 km/h.** Log horizontal speed, longitudinal/lateral acceleration, distance, drag, hull trim, and governor scale at fixed simulation-time intervals.
- [ ] **Step 2: Repeat on small waves and a bounded high-wave stress run.** Distinguish vertical heave from horizontal racing speed. Tune profile drag, drive, and rotational damping without disabling natural drift or adding an artificial speed lock.
- [ ] **Step 3: Regress turning and clutch.** Repeat A/D, Q+A/D coasting, S, and W+Space/release after every inertia change; check that the hull does not gain energy at neutral throttle and that 111+ km/h can decay naturally.
- [ ] **Step 4: Compile, save, document measured results, and request Astra review.** Record remaining feel/realism limits rather than marking acceptance from a single screenshot.

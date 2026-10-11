# Longtail Drive and Propeller Implementation Plan

> Status (2026-09-30): Core drive, clutch, shaft inertia, and 4 cm immersion are implemented. The checkboxes below are the original execution plan, not a current completion ledger; see `Docs/Work/2026-09-29-execution-ledger.md` and `Docs/HANDOFF.md` for verified work and remaining regression tests. In particular, full trim, rough-water, dry-prop, and longer timed coast tests remain open.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the boat an owner-controlled engine, a Spacebar clutch, inertial propeller RPM, and thrust only when the lowered propeller reaches water.

**Architecture:** Keep Chaos and Buoyancy on the existing physics Pawn. A focused Blueprint drive component/state block computes engine, shaft, clutch, and immersion signals; the Pawn applies force and the visual child receives shaft rotation and trim. The Water Body component queried by Buoyancy supplies the actual surface height.

**Tech Stack:** Unreal Engine 5.8.3 Blueprints, Water plugin, Chaos, live Unreal MCP, PIE.

**Spec:** `Docs/Specs/2026-09-29-boat-camera-drive-feedback-design.md`

## Global Constraints

- Preserve `/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat` and its 98 replaceable parts.
- Modify only the dedicated physics Pawn and `/Game/Maps/M_WaterPhysicsTest`; leave `/Game/boat` untouched.
- `Spacebar` disengages the clutch, not a brake; boat inertia must remain.
- `W` lowers the propeller to roughly 5-10 cm below sampled water before appreciable thrust.
- Save existing assets before bulk edits, compile with warnings as errors, and save afterward. The project has no Git repository; do not invent commits.

## Review Focus

- Second unpossessed boat receives W: it must not start or thrust (Task 1 test).
- Spacebar held after boat is already moving: it must coast, not stop abruptly (Task 2 test).
- Propeller outside a Water Body: thrust must be zero (Task 3 test).
- Water Body missing or invalid: surface query must fail closed without NaN or crashes (Task 3 test).
- Extreme Q/E trim cannot mechanically separate shaft/propeller or produce thrust from a dry prop (Task 3 test).

---

### Task 1: Owned Input and Drive Signals

**Files:** Modify `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn`; create `/Game/Boats/ThaiLongtail/Blueprints/BPC_LongtailDrive` only if a Blueprint ActorComponent is supported by the live editor toolset. Update `Docs/WATER_PHYSICS.md` with the final signal contract.

**Interfaces:** Consumes the owning `PlayerController` and W/S/Space/Q/E state; produces `EngineRPM: float`, `ShaftRPM: float`, `ClutchEngagement: float`, `Throttle: float`, and `TrimRequest: float` for Tasks 2-3 and the feedback plan. Values are visible in PIE.

- [ ] **Step 1: Establish failing PIE evidence.** Place a second physics Pawn in the test map and confirm the current Player 0 polling also drives the unpossessed copy; record the transform/RPM discrepancy, then remove only that temporary actor.
- [ ] **Step 2: Gate input to the owning local controller.** Keep deterministic QA override separate. Add the five drive-state outputs and update them once per Tick: idle 900 RPM, redline 6500 RPM, clutch 0 while Spacebar is held, otherwise interpolate toward 1 over about 0.3 s. First throttle starts the engine; it stays at idle after release until Pawn shutdown. Engine RPM rises toward redline under W+Space and falls toward idle after release.
- [ ] **Step 3: Run owner test.** In PIE with two boats and W for 3 simulated seconds, verify only the possessed boat's RPM rises and advances at least 200 cm; the unpossessed copy stays within 50 cm of its start and remains at idle. Confirm the saved map has `bUseTestInput=false` and no extra test boat.

### Task 2: Clutch, Shaft Inertia, and Thrust

**Files:** Modify `BP_LongtailPhysicsPawn` and `BP_ThaiLongtailBoat` only where an exposed propeller setter needs the new shaft rate.

**Interfaces:** Consumes `EngineRPM`, `ClutchEngagement`, `Throttle`, and `DeltaSeconds`; produces `ShaftRPM` and the propeller visual angle. Keep the old hull-in-water gate temporarily; Task 3 replaces it with `PropImmersion`. Full forward thrust remains bounded by the current 220,000 Unreal force-unit baseline.

- [ ] **Step 1: Record failing baseline.** PIE with W+Space currently moves and the propeller snaps with throttle. Capture hull transform and propeller angle over a fixed simulation interval.
- [ ] **Step 2: Implement coupling.** Set target shaft RPM to engine RPM scaled by clutch engagement, with approximately 0.35 s spin-up and 0.6 s spin-down; integrate propeller angle from shaft RPM. Scale stern thrust by normalized shaft RPM, throttle sign, and clutch while retaining the temporary hull-in-water gate. Remove the previous direct `throttle * 1800 degrees/second` propeller rule.
- [ ] **Step 3: Verify hold/release/coast.** Starting at rest, W+Space for 3 simulated seconds gives `EngineRPM > 5000`, `ShaftRPM < 200`, and less than 100 cm of powered travel. On Spacebar release, the boat advances at least 200 cm within 3 simulated seconds. Release W and verify propeller angle still changes briefly before slowing. Repeat Spacebar while moving and verify velocity decays only from existing drag, without a new opposite force.

### Task 3: Waterline Deployment and Immersion

**Files:** Modify `BP_LongtailPhysicsPawn`, `BP_ThaiLongtailBoat`, and `Docs/WATER_PHYSICS.md`.

**Interfaces:** Produces `PropImmersion: float` clamped to [0,1] and the actual propeller world position; consumes trim request from Task 1. `BP_ThaiLongtailBoat.SetTrim(Degrees)` remains the visual entry point with a verified expanded range if required.

- [ ] **Step 1: Measure current failure.** In PIE, record world Z of the actual propeller pivot and WaterBody surface Z at idle and W. Confirm whether the present -10 degree limit leaves the propeller dry.
- [ ] **Step 2: Add water query and target trim.** Use `Buoyancy.GetCurrentWaterBodyComponents()` and `WaterBodyComponent.GetWaterSurfaceInfoAtLocation(PropWorldLocation, ...)` (both BlueprintCallable in UE 5.8). Use the actual moved pivot position, not the fixed `(300,0,40)` thrust point. Automatically lower to 5-10 cm immersion under W/S, with bounded Q/E offset and a safe retract pose when off throttle. Multiply Task 2 thrust by clamped immersion. If no valid water result exists, set immersion and thrust to zero.
- [ ] **Step 3: Verify mechanical and physics extremes.** Test W, no throttle, Q/E limits, dry land/outside Water Body, and a missing/invalid surface query. With a valid flat water body, target propeller depth must settle within 5-10 cm below the surface before substantial thrust; without a valid surface, `PropImmersion=0` and thrust is zero. Inspect the model for shaft/linkage separation. If the authored tail cannot physically reach water, adjust the visual linkage/mount and repeat the test; never fake immersion to preserve thrust.
- [ ] **Step 4: Finalize.** Compile both Blueprints with warnings as errors, rerun idle/straight/right/reverse PIE tests, save assets, and record measured results and remaining limits in `Docs/STATUS.md` and `Docs/HANDOFF.md`.

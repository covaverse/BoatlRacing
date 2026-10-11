# Moving Hull Water Mask Implementation Plan

**Goal:** Hide externally rendered water only inside the boat's dry cavity below its rim, following hull motion without changing buoyancy, thrust, COM, or shaft length.

**Architecture:** Independent C++ reference math; fitted dry-hull geometry asset; per-World slot ownership and post-physics component publishing; project-owned Masked / SingleLayerWater material chain preserving all existing attributes except the multiplied OpacityMask.

**Tech Stack:** UE5.8.3, existing BoatlRacingPhysics plugin, Water, MPC, Material Functions, Blueprint, MSVC standalone tests, Unreal Automation, live MCP.

**Workflow:** User requested implementation first / MD afterward on 2026-09-30, deferring further written-document review. This plan records already-executed steps honestly; it was not written before the reference work. Continue without repeating the earlier document approval question. Use executing-plans and Astra review per pass. No Git repository exists; do not claim commits.

**Spec:** [moving-hull-water-mask-design](../Specs/2026-09-30-moving-hull-water-mask-design.md).

## Task 1: Reference Core

Files: `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private/BoatInteriorMaskMath.h`, `Tools/Tests/boat_interior_mask_math_test.cpp`, `Tools/Tests/run_boat_interior_mask_tests.ps1`.

- [x] Test-first containment and eight-slot allocation: initial 90 checks / 50 failures, then 90 / 0.
- [x] Reject stale cross-registry handles: 94 / 2 RED, then 94 / 0 GREEN.
- [x] Add measured curved-wall knots: 115 / 13 RED, then 115 / 0 GREEN.
- [x] Add combined transforms/numeric rejection coverage: latest 121 / 0.
- [x] Astra review found no remaining blocker for the reference scope.
- [ ] Include/use this core in native UE runtime and verify UE adapter scale/lifecycle behavior. Current results are standalone, not plugin build/gameplay evidence.

## Task 2: Geometry and Profile

Files: `Tools/Tests/measure_boat_mask_section.ps1`, `boat_mask_geometry_test.ps1`, `BoatMaskMesh.h`, `boat_mask_mesh_test.cpp`, `run_boat_mask_mesh_tests.ps1`; reports in `Saved/Automation/WaterMaskMath/`.

- [x] Inspect source geometry at X=30 cm; single linear chord overcut is 3.5367 cm, so add height curves.
- [x] Reject transformed ancestors, invalid references and negative individual offsets. Five rejection fixtures pass.
- [x] Survey actual centered liner with triangle intersections: 532 X sections, 4,256 height samples, 1,110 vertices and 2,216 triangles. Initial empty-helper RED: 14 / 9; latest GREEN: 4,279 / 0.
- [x] Fix Astra findings with coplanar shelf/asymmetric-rim regressions (18 / 2 RED), lower rim selection, conservative ambiguity rejection, and paired-edge/vertex-connectivity checks.
- [ ] Measure actual visible floor/transom and dry opening boundaries, including forward deck coverage. The current survey uses only the named inner liner.
- [ ] Fit eight longitudinal stations and up to eight height knots per station to a conservative dry volume. Check full triangle clearance and interpolation between stations, not just the survey grid. If capacity cannot meet clearance, revise representation with Astra before activation.
- [ ] Create `DA_ThaiLongtail_DryHull` only from a validated fit; no current Data Asset exists.

## Task 3: Runtime Ownership and Publishing

Planned files: public dry-profile Data Asset/component headers and private component/subsystem implementation in the existing plugin. Planned asset: `/Game/Water/Materials/MPC_BoatInteriorMasks`.

- [x] Create/save the inert MPC layout (416 vector / 2 scalar parameters). Verify names/defaults and 418 unique valid IDs; enable/active remain zero. This does not implement runtime publishing.
- [ ] Test per-World ownership, weak UObject lifetime, disable/re-enable, invalid->repaired data, slot saturation/reuse, world teardown, and origin shifts. Do not equate the pure slot reference test with these UE tests.
- [ ] Publish profile once on registration/change; publish inverse frame rows after physics. Reject non-finite/zero/negative per-axis scale. Clear active before uploads; enable only after all writes succeed.
- [ ] Release immediately on disable/EndPlay and support explicit re-registration without relying on a disabled tick. Ninth boat fails visible without overwriting another owner.
- [ ] Build/reload safely and run native UE Automation tests; save/normal shutdown if reflected changes require it. No forced Editor termination.

## Task 4: Project-Owned Water Shader

Planned assets: `/Game/Water/Materials/MF_BoatInteriorMask`, project-owned copies under `/Game/Water/Materials/BoatInterior/`.

- [x] Tool catalog returned; fresh discovery/live `IsPIERunning=false` and asset saves succeeded without terminating Editor or discarding work.
- [ ] Inspect current map/material references and save a recovery copy before changing any active water path.
- [ ] Back up exact WaterBody material references and duplicate/reparent necessary base + instance chain without modifying `/Water` assets. Preserve all instance overrides/static switches.
- [ ] Confirm displaced world-position convention on the actual wave graph. Compose existing OpacityMask with keep-water factor through Material Attributes, preserving all other attributes.
- [ ] Compile, read back graph/material references, and verify active near/far/underwater water paths. No fake flat-plane clipping fallback.

## Task 5: Acceptance and Handoff

- [ ] Capture matched mask-off/on flat/small/high-wave views: cockpit, side, bow, underwater. Water outside/below hull and over-rim crests must remain visible.
- [ ] Test W/S/Q/A/D/Space, coasting, turning, trim, two distinct boats, eight slots plus overflow, deletion/reuse, disable/repair, repeated PIE, map/origin changes.
- [ ] Compare physics settings/telemetry at controlled simulation times. Mask code never applies forces or locks Z/pitch.
- [ ] Measure actual hardware/settings CPU/GPU A/B cost; specification budgets are goals, not results.
- [ ] Astra review shader/lifecycle/evidence; update STATUS/HANDOFF/Thai guides after real outcomes.

Current remaining physics/racing work is still tracked in [boat-handling-waves](2026-09-30-boat-handling-waves.md). Do not mark the overall mask or game production-ready based on reference tests.

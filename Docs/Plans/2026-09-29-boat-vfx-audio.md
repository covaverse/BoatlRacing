# Longtail VFX, Audio, and Vibration Implementation Plan

> Status (2026-09-30): Prototype Niagara, synthetic test SoundWaves, and gated vibration are implemented. The checkboxes below are the original execution plan, not a current completion ledger; see `Docs/Work/2026-09-29-execution-ledger.md`. Audio listening/clipping checks, spray art and particle-budget review, dry-prop/coast captures, and high-speed FX validation remain open.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add speed-responsive water spray, RPM-responsive smoke and placeholder engine sound, and bounded engine visual vibration.

**Architecture:** Niagara and Audio components attach to the visual boat and read `EngineRPM`, `ShaftRPM`, `BoatSpeed`, `Throttle`, and `PropImmersion` from the drive plan. The physics body never inherits cosmetic vibration. Use inexpensive sprite emitters and a locally generated temporary engine sound, not audio from the reference footage.

**Tech Stack:** Unreal Engine 5.8.3 Niagara, Blueprint, AudioComponent/SoundWave, live Unreal MCP, PIE capture.

**Spec:** `Docs/Specs/2026-09-29-boat-camera-drive-feedback-design.md`

## Global Constraints

- Implement after the drive plan establishes the signal contract; do not infer effects directly from W alone.
- Keep effects game-ready: conservative CPU/GPU particle count, finite bounds, and no persistent high-rate emission at rest.
- Preserve imported 2K runtime textures and all 98 mesh parts. The project has no Git repository; save assets and record evidence in Docs.
- The engine sound is a clearly labeled test placeholder, with no copyrighted footage sample.

## Review Focus

- W+Space at rest: smoke/audio respond to RPM, while shaft/thrust and engine visual vibration remain off; high-speed wake remains absent (Tasks 1-2 tests).
- Coasting after W release: wake follows actual hull speed and decays naturally (Task 1 test).
- Dry propeller at speed: no propeller-contact spray despite hull motion (Task 1 test).
- Audio startup repeated rapidly: no stacked loud loops or clipping (Task 2 test).
- Vibration while engine stops: engine visuals return to neutral without shaking the hull or camera (Task 2 test).

---

### Task 1: Niagara Water and Exhaust Systems

**Files:** Create `/Game/Boats/ThaiLongtail/FX/NS_LongtailWake`, `/Game/Boats/ThaiLongtail/FX/NS_LongtailPropSpray`, and `/Game/Boats/ThaiLongtail/FX/NS_LongtailExhaust`; modify `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn` to host/drive components.

**Interfaces:** Consumes `BoatSpeed: float`, `PropImmersion: float`, `EngineRPM: float`, and `Throttle: float`; exposes Niagara user spawn/intensity parameters. Attach water effects at the actual propeller/wake point and smoke at the modeled exhaust outlet.

- [ ] **Step 1: Establish visual baseline.** Capture PIE at idle and moving: the current map has no project Niagara spray/smoke assets. Note propeller and exhaust world positions.
- [ ] **Step 2: Create efficient Niagara systems.** Use Niagara fundamentals, renderer, Blueprint interop, and optimization Agent Skills. Build white foam wake and fine spray that increase with actual speed, plus subdued grey exhaust whose density follows RPM/throttle. Expose one clamped user intensity per system; use sprite renderers, finite bounds, and reasonable scalability.
- [ ] **Step 3: Bind runtime parameters.** Add Niagara components to the Pawn or visual child. Drive wake from hull speed; drive prop spray from speed * immersion; drive exhaust from engine RPM/throttle, including Spacebar revving. Stop or reduce emitters at idle and outside water.
- [ ] **Step 4: Verify.** Capture idle, W+Space, moderate speed, high speed, coast, and dry-prop cases. Confirm no excessive particle count or obviously broken bounds. Save Niagara systems and Blueprint.

### Task 2: Placeholder Audio and Engine Vibration

**Files:** Create `SourceAssets/Audio/longtail_engine_test.wav` and `SourceAssets/Audio/longtail_start_test.wav`; import `/Game/Boats/ThaiLongtail/Audio/SW_LongtailEngineTest` and `/Game/Boats/ThaiLongtail/Audio/SW_LongtailStartTest`; modify `BP_LongtailPhysicsPawn` and the existing `BP_ThaiLongtailBoat.EngineAssembly` visual group.

**Interfaces:** Consumes `EngineRPM` and RPM acceleration; produces spatial engine loop pitch/volume, one-shot startup cue, and engine-only visual vibration. Audio and vibration are cosmetic and cannot alter Chaos force or collision.

- [ ] **Step 1: Record failing baseline.** PIE startup, idle, held rev, and coast currently have no engine sound and no engine-only vibration.
- [ ] **Step 2: Author test audio.** Generate a deterministic low-volume looping mechanical rumble and short start cue as WAV sources, import as SoundWaves, and configure one spatialized looping AudioComponent. Clamp pitch/volume against normalized RPM; guard startup so rapid W presses do not stack engine loops.
- [x] **Step 3: Add visual vibration.** Apply a small smoothed oscillation only to EngineAssembly during engaged launch or near maximum speed, with neutral transform restored otherwise. Keep collider, camera, tail pivots, and linkage stable; stationary `W+Space` revving is intentionally quiet visually.
- [ ] **Step 4: Verify and document.** Listen to startup, idle, held W+Space, launch, and throttle release; inspect for clipping/stacking. Capture engine motion in PIE and verify hull transform is unaffected. Compile Blueprints with warnings as errors, save all assets, update `Docs/STATUS.md`/`Docs/HANDOFF.md`, and request the user-required Astra read-only review.

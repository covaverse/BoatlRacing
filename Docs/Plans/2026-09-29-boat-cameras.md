# Longtail Camera Modes Implementation Plan

> Status (2026-09-30): Four views and boat-following Free Orbit are implemented. The checkboxes below are the original execution plan, not a current completion ledger; see `Docs/Work/2026-09-29-execution-ledger.md`. Human input, camera blending, all-angle framing, and obstacle-near clipping tests remain open.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add bow, bow-visible driver, chase, and boat-following Free Orbit views with reliable switching and framing.

**Architecture:** Keep the PlayerController possessing the boat in all modes. A camera controller block in the existing Pawn owns mode and desired view transform. Free Orbit rotates a spring arm around the boat with mouse input but remains position-tethered; it is not a separate spectator Pawn.

**Tech Stack:** Unreal Engine 5.8.3 Blueprints, CameraComponent, SpringArmComponent, live Unreal MCP, PIE screenshots.

**Spec:** `Docs/Specs/2026-09-29-boat-camera-drive-feedback-design.md`

## Global Constraints

- Preserve the 98-part visual boat and physical collision hull; camera motion cannot alter either transform.
- Use `C` to cycle four modes; chase is the saved default. Mouse-wheel zoom applies only to chase/orbit.
- Free Orbit always follows the boat's position and keeps W/A/S/D boat control active.
- Use a saved test map separate from `/Game/boat`. The project has no Git repository; save and verify assets instead of committing.

## Review Focus

- C held down: only one mode transition per key press (Task 1 test).
- Camera switched while hull rolls: no camera teleport into the hull (Task 1 test).
- Free Orbit while boat travels/turns: camera follows translation without snapping to heading (Task 2 test).
- Mouse input outside Free Orbit: chase/driver/bow views must not drift (Task 2 test).
- Camera near shoreline/obstacle: spring-arm collision prevents geometry clipping (Task 2 test).

---

### Task 1: Four Framed Camera Modes

**Files:** Modify `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn`; update `Docs/HANDOFF.md` with controls.

**Interfaces:** Produces `CameraMode` enum/int in order Bow, Driver, Chase, FreeOrbit; consumes a rising-edge C input event from the owning local controller.

- [ ] **Step 1: Capture failing baseline.** PIE screenshot current chase view and confirm only one camera mode exists; record hull bounds for bow-tip framing.
- [ ] **Step 2: Add mode anchors and switching.** Add BowCamera near the forward tip facing local -X; DriverCamera behind it with tip visible; retain ChaseBoom/ChaseCamera as default. Add one active-view selector with short transform blending and rising-edge C handling. Do not cycle repeatedly while C stays down.
- [ ] **Step 3: Verify screenshots.** Capture each mode at 16:9 desktop and while turning. Bow points forward; Driver shows the actual bow tip; Chase frames the entire boat and tail without clipping. Repeated C presses reach all four modes and wrap back to Bow.

### Task 2: Tethered Free Orbit and Zoom

**Files:** Modify `BP_LongtailPhysicsPawn` only.

**Interfaces:** Consumes `CameraMode`, mouse delta, mouse-wheel input, boat root location, and current spring-arm collision result; produces orbit yaw/pitch/distance while preserving boat possession.

- [ ] **Step 1: Record failing behavior.** In the fourth mode before implementation, mouse motion cannot orbit and/or camera heading remains rigidly attached to the boat; record the failure in PIE.
- [ ] **Step 2: Implement orbit.** Initialize orbit from the outgoing camera transform; update yaw/pitch from mouse only in FreeOrbit, clamp pitch to a useful elevated range, and keep the orbit arm attached to the boat. Clamp wheel distance to a range that sees both hull and shaft. Maintain spring-arm collision testing.
- [ ] **Step 3: Verify motion.** Drive the boat while rotating the Free Orbit camera: it follows translation but preserves the chosen world-facing direction during a turn. W/A/S/D still drive. Switch back to Chase and verify mouse movement no longer alters its heading. Check near an obstacle for clipping.
- [ ] **Step 4: Finalize.** Compile with warnings as errors, save Blueprint, verify PIE stopped, and update `Docs/STATUS.md` with view screenshots or measured framing notes.

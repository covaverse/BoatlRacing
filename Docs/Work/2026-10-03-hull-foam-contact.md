Hull contact and wake correction (2026-10-03)

Foam birth now samples the exterior black shell instead of the interior dry-cavity profile. `build_outer_hull_profile.py` creates a separate 640 x 128 atlas and checks four waterline intersections against independent triangle rays. The water opacity mask retains its interior profile.

`M_BoatFoamComposite` births foam only at the measured hull waterline; existing render-target history supplies the trail. World-space transport replaces the fixed straight V. `SurfaceFlowCmPerSec` controls world-space current/wind drift; default is (12,0). It is a material parameter, not an automatic connection to a changing wind actor.

The Blueprint publishes BoatVisual's frame, including visual trim. `ApplyVisualTrim` adds -3 degrees to the existing visual pitch target so the stern (+X) sits below the bow (-X), including idle. Physics mass, center of mass, pontoons and force values were not changed.

The live fluid-simulation foam also receives a soft forward cutoff at local X -330..-270, preventing its waves from drawing white tracks in front of the boat.

Follow-up: runtime measurement found SideSpray and SprayMist born at hull Z 380.69 while water Z was 400. `UpdateSideSpray` now places both origins at water Z + 2 with visual yaw and zero pitch/roll. The water material adds immediate contact from the exterior profile evaluated at the rendered water position, so fast movement does not rely on several frames of RT accumulation before the hull edge becomes visible. Contact birth is speed gated; transported history retains its fade.

Run `Tools/verify_hull_foam.py` in Editor Python during PIE. It checks visual-frame alignment, moving and stopped particle rates, both bow-contact pixels, retained trail through a turn, controlled lateral flow, gradual fade, and stern height. Results: `Saved/Automation/BoatContact/hull-foam-check.json`. The older `verify_v_foam.py` tests the superseded straight-V pattern.

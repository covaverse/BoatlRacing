# Dynamic hull water interaction ? 2026-10-03

The rendered water previously used WorldPositionOffset and Normal from the pre-fluid attribute branch. Foam could sample fluid activity while the visible surface still bypassed SampleFluidSimulation.

M_WaterBoatContact now routes both WorldPositionOffset and Normal from SampleFluidSimulation through DynamicWaterSurface to the final MakeMaterialAttributes. Existing water shading, dry mask and foam remain connected.

M_BoatHullFluidForce now samples T_BoatOuterProfile at the waterline in the BoatVisual frame. It depresses the wetted footprint and raises shoulders immediately outside the actual hull. Bow shoulders receive additional pressure. The existing Blueprint force supplies horizontal speed, vertical water entry velocity and delta-time scaling, and gates forcing when the boat is out of water or stationary. The native ripple solver propagates the stamped pressure through the moving simulation grid.

This is dynamic surface displacement using the existing height-field solver, not volumetric CFD. Physical mass and buoyancy tuning were not changed. The earlier visual stern trim remains.

Validation: Tools/verify_dynamic_water.py passes GPU checks for negative hull pressure, positive exterior pressure, fourfold response between the tested speeds, rotation with yaw, zero dry/stopped forcing and direct simulated surface output wiring. Results: Saved/Automation/BoatContact/dynamic-water-check.json.

Assets backed up before edits under Saved/Backups/20261003-211641-dynamic-water and Saved/Backups/20261003-211739-dynamic-surface.

PIE validation: Tools/verify_dynamic_runtime.py passed on the active M_WaterPhysicsTest map. The actual NormalRT height field contained negative and positive displacement. After stopping the hull source for three seconds, nonflat pixels outside the source increased from 6,635 to 19,216 while mean squared height dropped from 0.0011166 to 0.00065165 (about 42%). Results saved in Saved/Automation/BoatContact/dynamic-runtime-check.json. PIE stopped afterward to reset all temporary test controls.

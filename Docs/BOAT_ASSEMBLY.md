# Thai Long-Tail Boat Assembly

## Asset

- Blueprint: `/Game/Boats/ThaiLongtail/Blueprints/BP_ThaiLongtailBoat`
- Source import: `/Game/Boats/ThaiLongtail/thai_racing_longtail_runtime_2k/`
- 98 imported mesh components: 77 Static Mesh + 21 Skeletal Mesh. All references were checked against the imported asset list.
- 15 non-mesh components provide the root, assembly groups, pivots, and linkage anchors. The mesh parts remain individually replaceable.

## Hierarchy and Coordinates

`BoatRoot` groups `HullAssembly`, `InteriorAssembly`, `CockpitAssembly`, `EngineAssembly`, `DrivelineAssembly`, and `DetailsAssembly`. Most mesh geometry is baked in shared boat-space coordinates, so fixed mesh components sit at relative zero beneath their group. Pivoted meshes are offset by the inverse of their parent pivot's neutral global position.

| Pivot or anchor | Parent | Neutral position in boat space (cm) | Purpose |
| --- | --- | --- | --- |
| `SteeringPivot` | `CockpitAssembly` | `(53, 0, 67)` | Cockpit steering handle |
| `TrimLeverPivot` | `CockpitAssembly` | `(67, 30, 55)` | Trim lever |
| `TailYawPivot` | `DrivelineAssembly` | `(300, 0, 73)` | Tail shaft left/right swing |
| `TailPitchPivot` | `TailYawPivot` | `(300, 0, 73)` | Tail shaft up/down swing |
| `PropellerPivot` | `TailPitchPivot` | `(546, 0, 70)` | Propeller spin; 246 cm aft of tail pivot |
| `HelmRodAnchor` | `SteeringPivot` | `(69, 35, 53)` | Front control-rod end |
| `SternRodAnchor` | `TailYawPivot` | `(302, 34, 67)` | Rear control-rod end |
| `ControlRodPivot` | `BoatRoot` | `(185.5, 34.5, 60)` | Linkage midpoint/orientation/length |

## Callable Blueprint Functions

- `SetSteering(Degrees)`: clamps to `[-18, 18]`, rotates `TailYawPivot`, rotates `SteeringPivot` by 0.85 of the angle, then calls `UpdateControlRod`.
- `SetTrim(Degrees)`: rotates `TailPitchPivot` and the cockpit trim lever (0.75 of the angle). With the current stern-weight tuning, gameplay deployment runs about -7.4 to -8.1 degrees on flat water; inspect the live Blueprint for its clamp limits and test full Q/E clearance.
- `SetPropellerAngle(Degrees)`: rotates the propeller about the authored local X axis, which is close to but not perfectly aligned with the slightly sloped shaft. A game loop can feed this a cumulative angle from RPM.
- `UpdateControlRod()`: positions the rod at the midpoint of its anchors, aims it approximately between them, and adjusts its length as the linkage moves. The current neutral-angle subtraction and X-only scaling can leave a small endpoint mismatch at steering extremes.
- Construction Script calls the three setters with zero degrees for a neutral starting pose.

These functions are now called by `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn`, which supplies keyboard input, basic propulsion, buoyancy, collision, and four camera modes. The visual assembly remains independent and reusable. Propeller spin now integrates ShaftRPM, including spin-down inertia, and stops when the clutch is disengaged.

## Verification

- All mesh references and component count were audited through live Unreal MCP.
- Blueprint compile passed with warnings-as-errors; asset saved; no Blueprint-specific Editor log errors/warnings.
- Blueprint preview showed the assembled boat. A temporary maximum-angle pose was compiled, then the Construction Script was returned to neutral and the asset saved.
- The visual assembly now runs as a non-colliding child Actor of the physics Pawn in `/Game/Maps/M_WaterPhysicsTest`. PIE verified floating, straight motion, and turning; obstacle collision, imported animation playback, materials, and performance have **not** been validated. The user's `/Game/boat` level was not changed.
- Astra review found no critical hierarchy or graph defect. Before treating the linkage as a production mechanism, measure both rod endpoint gaps at steering limits and replace the approximate neutral-angle correction with exact local-axis alignment; align the propeller pivot to the actual shaft axis if strict mechanical accuracy is required.
- The long-tail inner shaft and outer sleeve are scaled 1.5x along X around the original tail root; bearings were moved along them, and `PropellerPivot` was moved from X=164 to X=246 relative to `TailPitchPivot`. Root X=300 stays fixed, so the hub reaches boat-space X=546 instead of X=464. The shaft and propeller remain children of the yaw/pitch pivots and can still swing left/right and up/down. This is a Blueprint-level runtime extension; reauthor the Blender source geometry and UVs before a production reimport.

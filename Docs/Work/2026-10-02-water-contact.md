# Water contact pass — 2026-10-02, Asia/Bangkok

Changed `M_WaterPhysicsTest`, `M_WaterSmallWavesTest`, and `M_WaterHighWavesTest`.
Latest revision: all three now contain native Water Ripple Solver actors. See
"Native surface-wave revision" below; the earlier sprite wake passes are historical.
The existing Ocean island spline is now a regular loop around world X=60000,
Y=18000 cm, outside the starting course. The native spline API accounts for
actor scaling; direct `SplineCurves` property readback alone was insufficient.

Project-owned assets under `/Game/Water/Materials/BoatContact` duplicate and
reparent the original Water material chain. Signed DistanceToNearestSurface
multiplies the existing opacity mask through a break/make attributes path;
all other attributes, wave displacement and instance overrides are retained.
The existing closed collision hull generates the distance field. BeginPlay
disables its main/depth/ray-tracing rendering while keeping it unhidden so the
distance field remains available. Collision and buoyancy remain enabled.
The 2 cm inset avoids clipping right up to the hull boundary. This masks solid
mesh interiors, including other distance-field meshes; it is not a fitted dry
cavity or a fluid simulation. The earlier MPC/profile system remains inert.

`UpdateFXState_0` measures horizontal hull speed, samples waves separately at
the stern and bow, places those effects above the surface, and gates bow spray
by contact. Prop spray uses the actual propeller XY and sampled water height.
The handling asset's front/rear pontoon radii increased from 60/55 to 70/65 cm;
live high-wave readback confirms 70/70/65/65. Only hull pontoons support the boat.
No mass, COM, propeller support, native force code or wave amplitude was changed.

Validation: Blueprint compiled with warnings treated as errors. PIE images and
bounded high-wave samples are in `Saved/Automation/BoatContact`. These are
wall-time snapshots, not matched simulation-time performance measurements.
The final flat moving check records hull Z=400.28 cm at water Z=400 cm, speed
727.88 cm/s, and positive wake/bow/prop spawn rates. `verify_boat_contact.py`
passes saved assertions on all three maps in a fresh commandlet. The commandlet
still exits 1 because of pre-existing missing GameFeatureData Asset Manager
rules; the log contains `BOAT_CONTACT_SAVED_ASSETS_PASS` and no assertion failure.

The initial attempt to set material attribute GUID arrays crashed Editor;
the final material uses ordinary break/make attributes nodes instead.
Backups are in `Saved/Backups/2026-10-02-water-contact`.
Editor is left on the flat test map, PIE stopped, test input false/zero on all maps.

Realism follow-up: mask inset is now 2 cm (`If.ConstB=-2`), reduced from 4 cm.
This is an inward signed-distance margin, not an outward fluid displacement radius.
Wake no longer uses Fountain's 500–850 cm/s cone velocity: AddVelocity is disabled,
spawn radius is zero, sprites face world +Z, size is 12–24 cm and life 1.2–2 seconds.
World-space particles leave a surface foam trail instead of airborne fountain blobs.
`realism-game.png` records the moving trail; Niagara compiled UpToDate without
errors or warnings. Foam retains its spawn height, so it does not follow subsequent
wave crests; the current effect remains approximate, not a fluid solver.

Visible wake follow-up: `M_LongtailWakeSurface` replaces the default soft disk
with procedural V-shaped foam bands, a central tail and rippled normals.
Sprites align to `Engine.Owner.SystemXAxis` and face world +Z; 160–240 cm patches
last 3–4 seconds. The shared speed-driven rate is reduced from `6+75*alpha`
to `6+18*alpha` to prevent a solid white strip from excessive overlap.
`wake-v-final.png` records moving PIE. Blueprint and material compile succeeded;
`python Tools/verify_wake_realism.py` checks live material, orientation, size,
lifetime and Niagara compilation. This produces visible surface shading;
Refraction is held at 1 to avoid rectangular distortion artifacts; it does not deform the Water mesh or feed waves back into buoyancy. Existing foam
particles retain their spawn height, so high waves can obscure portions of the trail.

Propeller reference follow-up: added `PropWashFX`, `NS_LongtailPropWash` and
`M_LongtailPropWash`, reusing the existing surface Niagara system/material.
Animated radial normals and mottled foam are centered at the sampled propeller
XY/water height. Rate is immersion times `(4+24*clamped(abs(ShaftRPM)/1400))`,
only above 20 RPM and .02 immersion; hull velocity is not part of this gate.
BeginPlay assigns the asset in the shared Blueprint because existing placed actors
retained an empty Niagara asset despite the updated component template.
Live low-throttle check: 401.25 shaft RPM, immersion 1, rate 10.87857 particles/s,
runtime asset verified. Fresh commandlet executes the actual FX Blueprint on
transient probes at zero hull velocity: stopped, dry, barely touching, half/full
immersion and above-rated RPM all pass (`BOAT_PROP_WASH_BRANCHES_PASS`).
All three saved map assertions pass; the known GameFeatureData startup errors
still cause commandlet exit 1. No fluid feedback or propeller buoyancy was added.

## Native surface-wave revision

User rejected sprite-only wakes. Added the installed Water plugin's
`BP_FluidSim_01` to all three maps, using its Ripple Solver and the existing
`SampleFluidSimulation` path in the project water material. The simulation's
`NormalAndHeight` texture displaces the Water mesh, not a separate foam card.
Three native impulses are submitted by the shared FX function: bow port/starboard
when moving and contacting water, and the propeller when rotating while immersed.
The time factor is bounded at 1/30 second to avoid a large impulse after a hitch.
The four earlier water sprite components are deactivated in BeginPlay.

Settings: 4096 cm square following the player, 512 resolution, fixed 60 Hz solver,
travel coefficient .35, damping .005, 600 frames before idling. Water tessellation
factor is 8; maximum fluid displacement is 40 cm. The stock .95 travel coefficient
and oversized initial forcing produced unstable/oversized heights during tuning;
those settings were replaced before saving the final maps.

GPU readback measured actual height values, not particle counts. With forcing
then disabled and the boat frozen, pass 486 measured -8.484/+4.969 cm, with 7,628
nonflat samples more than 1 m from the source points. At pass 608, still with
forcing disabled, the field evolved to -2.580/+2.570 cm and 23,449 outside-source
samples. Different hashes, advancing passes and expanding support demonstrate
wave propagation and damping after the boat's impulses stop.
Files: `ripple-released_before.json`, `ripple-released_after.json`,
`ripple-final-moving.png`, `ripple-after-passage.png` under Saved/Automation/BoatContact.
`Tools/inspect_ripple_runtime.py` runs in Editor Python during PIE to obtain the
GPU field; `Tools/verify_boat_contact.py` validates saved maps and propagation evidence.

This is a local 2D surface-wave solver, not volumetric CFD. Existing Water buoyancy
and prop immersion still query the base Gerstner water surface; the additional GPU
ripple heights are not read back into the buoyancy/immersion forces. The square
simulation follows one local player, as provided by the installed native example.

Photo references downloaded for inspection, not imported as game textures:
[longtail propeller operation](https://discoverasia.com.pl/blog/jak-wygladaja-tajskie-lodzie-i-dlaczego-sa-tak-znane)
and [boat wake photograph](https://www.irishtimes.com/news/science/the-science-behind-the-ripples-and-wakes-in-water-1.1394676).
Local copies are in Saved/References/WaterWake. The visual targets are the disturbed
propeller patch and the propagating wave crests outside the central foam trail.

## Bow spray and finer water

Increased the existing Ripple Solver resolution from 512 to 1024 in all three
maps, keeping the 4096 cm domain and conservative travel/damping settings.
Cell spacing is now 4 cm instead of 8 cm; Water tessellation is 9 instead of 8.
This quadruples simulation texels; a full performance budget has not been measured.
GPU readback of a moving run measured -9.680/+7.316 cm and 119,993 disturbed
samples outside the source radius. The final readback still contains 1,048,576
height samples and a bounded propagating field.

Created `NS_LongtailBowSplash` by duplicating the existing spray and reusing
Niagara's installed Fountain emitter for a second side. Both emitters have
2-7 cm droplets, .22-.65 second lifetimes, and world gravity -980 cm/s².
The component is positioned at hull local X=-280 and sampled water height+2;
emitter offsets are local Y=+32/-32 cm. Cone axes point outward on opposite
sides, upward, and slightly aft. They use world-space particles and local-space
spawn offsets/launch directions, so emitted droplets do not follow the boat.

The shared Blueprint activates the new bow asset on BeginPlay, ensuring existing
placed Pawns receive it. The three earlier water-card components remain off.
Bow spray and native bow ripples start when contact is true and horizontal speed
exceeds 15 cm/s. Per-side rate is 10+120*alpha, launch speed 60+380*alpha cm/s,
cone angle 25+45*alpha degrees, with alpha clamped at speed/1600. Dry or stopped
boats emit zero droplets. The new droplets supplement the simulated water surface;
they do not replace it or introduce GPU-height buoyancy coupling.

`Tools/verify_bow_water_runtime.py` executes the actual Blueprint in PIE at
0, 10, 30, 100, 800, 1600 and 2400 cm/s, plus an 800 cm/s dry case. All eight
assertions pass; at 30 cm/s each side emits 12.25 droplets/s, at 1600 cm/s
130/s, and above that rate/launch/spread stay bounded. Evidence:
`Saved/Automation/BoatContact/bow-branches.json`, `ripple-detail1024.json`.
`bow-spread-review.png` shows both outward streams with the boat temporarily
frozen for inspection; it is not a moving-wake capture. Native Blueprint compilation
and both Niagara emitters compile without errors or warnings.

Tried the native `Simulate Wave Foam` option, but its stock Blueprint unconditionally
calls `SetLandscapeMaterialTextureParameterValue` on a null Landscape in these
maps. Reverted that option to false in all saved maps; no Landscape or plugin
asset was fabricated/modified. Foam-generation work remains separate from these
tested bow droplets and real ripple displacement.

Fresh commandlet validation (`bow-saved-check.log`) passed all three saved maps,
prop-wash branches, ripple propagation, the new bow/detail evidence and the final
saved-asset assertion. Exit code remains 1 from the pre-existing GameFeatureData
Asset Manager configuration errors; this is not a clean project build claim.
Editor is left on the flat test map with PIE stopped and saved test inputs off.

Bow asset assignment correction: the component template still referenced
`NS_LongtailPropSpray`, while BeginPlay substituted the dedicated bow system.
Changed the saved Blueprint template and all three placed boat components to
`NS_LongtailBowSplash` directly. `PropSprayFX` keeps `NS_LongtailPropSpray`.
Saved-asset validation now checks both assignments and rejects a shared system.
The template must be modified and the Blueprint explicitly saved; changing its
component property alone did not dirty/save the package. Fresh commandlet reload
now passes the template and all three placed-boat asset-separation assertions
(`bow-asset-separation-check.log`). The known GameFeatureData exit-1 remains.

## Rear propeller jet and fluid foam

Activated the distinct `NS_LongtailPropSpray` rear effect. Its launch cone now
points aft/upward (local +X), rather than the earlier forward-facing axis.
Immersed shaft rotation drives emission at seven times the existing prop-wash
rate: 0 when stopped/dry, up to 196 droplets/s when fully immersed at rated RPM.
Jet speed is 120+500*clamped(abs(RPM)/1400) cm/s; spread is 15+20*alpha degrees.
Droplets are 3-8 cm, live .2-.65 seconds and fall under world gravity.
Bow and rear systems use distinct launch inputs, sources and directions.

Added white foam shading to the project-owned SingleLayerWater material.
It subtracts the WorldPositionOffset entering `SampleFluidSimulation` from the
offset leaving it, isolating the actual fluid disturbance from background waves.
That disturbance drives a mottled/bubbled BaseColor blend and roughness blend.
Foam intensity ramps between 1 and 5 cm of fluid displacement. Original WPO,
normal wiring and the distance-field hull mask remain connected.
This is amplitude-based aeration shading, not persistent foam transport;
add a transported foam render target if lingering bubbles need independent decay.
Stock `Simulate Wave Foam` remains false, avoiding its null-Landscape error.

PIE rear view `prop-foam-rear.png` shows the aft jet and disturbed white water.
At 812.5 shaft RPM and full immersion, measured rate was 125.5 droplets/s,
launch speed 410.18 cm/s and spread 26.61 degrees (`prop-jet-runtime.json`).
The rear emitter compiles without errors/warnings. Saved verification now tests
rear emission at zero hull velocity for stopped, dry, partial/full immersion and
over-rated RPM, and checks foam shading inputs while preserving mask and WPO.
Evidence lives in `Saved/Automation/BoatContact`.
Fresh commandlet `prop-foam-saved-check.log` passes all three saved maps, rear jet
branches, foam graph connections and the final saved-asset assertion. Exit remains
1 for the pre-existing GameFeatureData configuration errors. PIE is stopped and
saved test inputs remain off.

## Textured wake refinement

Inspected the native Water plugin's foam textures by exporting preview TGAs.
`T_WaterFlow_03_Foam_Tiled` is 2048x2048 and contains detailed turbulent white
foam; `T_BoatForceFoam` is only a 64x64 directional force mask, not a foam photo.
Used the former directly through a new `Boat Foam Texture` object parameter in
the project-owned material. No plugin asset was edited and no video image was
used as a game texture. The precise texture names in the supplied videos cannot
be verified from their low-resolution storyboard previews.

The foam custom node now samples the texture at two world-space scales instead
of the earlier grid/hash grain and circular dots. Coverage still depends on the
actual fluid-only height difference, ramping from .12 to 1.8 cm so weaker disturbed
water can show foam. Undisturbed water has zero added coverage. Main scale is
160 cm per tile; the secondary scale breaks repetition. The existing material
roughness blend, Water mesh displacement and hull opacity mask are preserved.

Prop disturbance radius increased from 35 to 70 cm; pressure increased from
`-(.01+.04*power)` to `-(.02+.06*power)`, still multiplied by immersion and bounded
frame time. This addresses the weak/narrow disturbance as well as its texture.
Moving readback at pass 727 measured -6.0039/+3.4902 cm, 35,324 nonflat samples,
and 32,758 beyond the source-radius exclusion. It remains bounded below the
40 cm displacement limit. Evidence: `ripple-textured-wake-steady.json` and
`textured-wake-steady.png` in Saved/Automation/BoatContact.

Limit remains: foam has no independent transport/lifetime after its supporting
fluid wave decays; this is not volumetric aeration or a complete Kelvin-wake model.
`Tools/refine_wake_texture.py` updates the existing foam node without replacing
the original water material chain. Saved verification checks the texture source,
all three foam inputs, mask/WPO connections, and new GPU evidence.
Fresh `textured-wake-saved-check.log` passes those checks and all three saved
maps. The commandlet still exits 1 for the unrelated GameFeatureData errors.
Editor is on the flat test map with PIE stopped; saved test overrides are off.

## User-supplied tutorial references

- [Make Waves With Your Game - FluidSim Tutorial Unreal Engine 5.4](https://www.youtube.com/watch?v=UkcvGdS0wU8), Peanut Games. YouTube oEmbed confirms the title/author. Relevant to the existing native FluidSim work; compare setup, foam and water clipping when playback is available.
- [UE4: Ship water trails](https://www.youtube.com/watch?v=3tQ_PvBtIU4), Zartris. YouTube oEmbed confirms the title/author; keep as a wake reference. Its implementation technique has not been verified.
- [WaterlinePRO Masterclass 2 Large Ship Simulation](https://www.youtube.com/watch?v=ISXB8wzSfZQ), Dumpster Fire Productions. This project currently has no WaterlinePRO installation.

### Follow-up: contents inspected directly from YouTube

Retrieved the watch pages' player metadata, full descriptions and storyboard
preview sheets for all three videos. The storyboard interval is 5 seconds;
FluidSim and WaterlinePRO tiles are 320x180, Ship water trails tiles are 160x90.
These are actual preview frames from the videos, not photographs of another
implementation. They allow checking the demonstrated workflow and visual result,
but most node names and numerical properties are too small to read reliably.
Full playback/audio was not available. English auto-caption tracks are advertised,
but their content could not be retrieved: timed-text requests returned empty data
and the transcript endpoint returned a precondition error. No spoken instructions
or exact property values are claimed as verified.

FluidSim video:
- The author's description provides chapter starts: 0:00 basic setup, 2:36 foam,
  5:55 water level, 7:02 outro.
- 0:00-0:05 preview frames show a boat on turquoise water, then a broad white
  disturbance behind it. Later frames show setup in the level editor.
- 3:00-3:40 frames show material/material-function editing during the foam chapter.
- 5:55-6:40 frames show the boat and water surface from above and below during
  the water-level chapter. This is useful when checking immersion and clipping;
  it does not establish a particular distance-field threshold.
- Project comparison: native FluidSim is already connected to the water material,
  while `Simulate Wave Foam` is currently false. This is a concrete existing
  setting to investigate for clearer surface foam, not proof that the video uses
  the same setting. GPU ripple displacement still does not feed CPU buoyancy.

Ship water trails video:
- The author's description identifies this as a demonstration and creation
  walkthrough for a large ship's trail, and links the UE4 Ocean Project:
  https://github.com/UE4-OceanProject/Environment-Project
- 0:05-1:55 frames show the rendered ship with a long, expanding turbulent trail.
- 4:10-6:10 frames show ship Blueprint and material graph editing.
- 12:30-12:45 frames show a flat rectangular asset in an editor, followed by
  12:50-13:20 rendered ship/trail views. The preview resolution does not establish
  the precise shader or how that asset is used. Do not label it a fluid solver
  or claim two-way buoyancy coupling from these frames.
- Useful visual target: the trail occupies an expanding area behind the hull,
  with a textured turbulent center rather than a single uniform white strip.

WaterlinePRO video:
- The author's description explicitly points to a separate invisible-wake-mesh
  tutorial: https://youtu.be/ZMVe28GsLiA
- 3:45-4:25 preview frames show ship setup in the editor; 7:30-8:10 show a bright,
  broad wake and material/parameter editing around the stern.
- These are reference observations from a different water asset. No WaterlinePRO
  asset was installed or substituted into this project.

Evidence is stored under Saved/References/WaterWake as each video's
`.metadata.json`, `.storyboards.json`, `-storyboard-N.jpg`, and watch-page HTML.
Current native-solver tuning was not changed solely from these low-resolution
previews. A future foam change needs a moving-boat visual check and must preserve
the already verified propagating height field.

## 2026-10-02 idle/draft follow-up (incomplete live validation)

- Measured visible HullMain bounds: keel Z=-0.052 cm, rim Z=67 cm in actor space; collision proxy bottom Z=-25 was not the visual keel. The previous 70/65 cm runtime pontoons held the actor at Z=401.343 on flat water Z=400, leaving the visible keel effectively above water.
- Restored handling profile front/rear radii to 60/55 cm. Fresh PIE measured actor Z=376.808 (about 24.5 cm lower), still settling; no final settled draft evidence yet. Mass remains 450 kg, COM and forces unchanged.
- Saved UpdateFXState_0 now requires wet bow and horizontal speed >80 cm/s for bow spray/impulses; spawn rate is 130*speedAlpha per side without the old constant 10 particles/s floor. Prop spray remains tied to immersed prop RPM.
- Side capture still showed transient bow droplets despite SpawnRate=0; startup activation before zeroing User.SpawnRate is a hypothesis, not a verified root cause. ConfigureBoatMass.dsl now has zero-rate initialization prepared in source ONLY; NOT applied/saved to the Blueprint yet.
- Tools/verify_bow_water_runtime.py and verify_boat_contact.py expectations updated, but the new PIE branch run remains outstanding.
- Recovery incident: focus was in the viewport when Ctrl+A/BackSpace was sent, temporarily deleting scene actors. No map save occurred. Editor is blocked mid-deletion (last log 03:32:57 UTC); a Ctrl+Z request was sent but completion is unverified. User asked to cancel any deletion modal, then verify/undo before saving. Computer Use could not connect its native pipe. Do NOT save current map until actor restoration is confirmed.
- Separate read-only commandlet Tools/verify_saved_draft.py confirmed all THREE saved maps intact (13 actors each, boat, lighting, WaterBodyOcean, WaterZone and fluid sim present), profile60/55 and saved speed80/rate130 graph persisted. Evidence: Saved/Automation/BoatContact/draft-saved-check.log BOAT_SAVED_DRAFT_PASS. Commandlet exit1 remains pre-existing GameFeatureData AssetManager configuration errors.
- Resume: recover live Editor, verify 13 saved-map actors restored; apply startup zero-rate DSL and disable spray auto-activation templates if evidence supports it; rerun stationary/slow/moving bow and prop branches; capture settled side/interior views and validate the existing distance-field mask at the lowered draft before claiming the interior is dry. Current crude solid proxy does not constitute a fitted cavity or an over-rim flooding simulation.
- Native Slate FillForm DOES NOT replace textbox contents: source delegates to Type. Always focus the console explicitly, verify text focus, then select-all and Type submit=true. Never send BackSpace unless console focus was verified. Avoid repeated broad graph rewrites until Editor recovery is complete.


## Additional references and idle/draft checkpoint

- [Waterline PRO: Dynamic Water Simulation Part 3 Ship Sim](https://www.youtube.com/watch?v=X9SKZoP7ssU), Dumpster Fire Productions, 22:01. Watch-page metadata and storyboard sheets at 0/750/1250 seconds were retrieved; the last sheet visibly shows surface wave ridges and white foamy wake. This is a Waterline PRO workflow, not proof the stock Water plugin reproduces its result. Full playback/audio/transcript was unavailable; no numerical tutorial settings are asserted.
- [UE4 Perfectly Floating Boat](https://www.youtube.com/watch?v=3N-FWe3knLU), UE4 Mentor, 5:38, explicitly targets UE 4.26.1 Water/Ocean. Storyboards show editing boat support locations then testing the boat at the waterline. Values are illegible; the reference does not establish an arbitrary half-hull draft. Metadata and downloaded sheets are in `Saved/References/WaterWake`.
- Saved handling radii restored to 60 cm front / 55 cm rear. Idle spray is visibility-gated off at horizontal speed <=80 cm/s; immersed spinning prop can still churn water while stationary. Saved foam blends opacity toward .95 and roughness toward .65, with native tiled foam texture, so whiteness is visible beyond specular glare.
- Measured-profile shader prototype uses the existing 532x8 survey atlas and four boat frame vectors. Controlled tests have not yet passed; do not claim dry interior or multiplayer acceptance. Historical distance-field replacement also failed the forced-submersion probe.


## Measured profile acceptance and recovery resolution

- Live editor deletion was undone: the flat editor map has 13 actors and all three saved maps were independently verified intact. No deletion or test-input overrides were saved. Startup zero-rate initialization and definitive visibility gates were subsequently applied and saved; eight actual bow Blueprint speed/contact cases passed.
- Active water OpacityMask uses the measured liner atlas and four Pawn frame vectors, not the unused DF prototype. HLSL uses branchless containment with inactive default Origin alpha; no shader wall-clock comparison remains. The prototype is explicitly one unit-scale boat per world and needs an EndPlay frame clear before actor deletion is supported. World shutdown resets collection state.
- Flat controlled probe root Z365, water Z400 (local35) is inside the measured open rim: `profile-draft35-on.png` shows exposed dry wood and continuous outside water; `profile-draft35-off.png` shows water across the same liner at the same pose. Earlier rootZ350/local50 tests exceeded the surveyed midship rim (~47.9), so those captures do not demonstrate below-rim containment failure. They do expose the absence of an over-rim flooding model. No high-wave acceptance is claimed.
- A fresh commandlet exposed that the four frame setter calls had not reached the saved Blueprint. Compiled and force-saved the live Blueprint; readback confirms four setter calls and save=True. Fresh saved-asset check follows this correction.

- Final saved check `profile-final-saved-check.log`: all three MAP_PASS plus prop/rear-jet/foam/ripple/texture/bow evidence and CONTACT_SAVED_ASSETS_PASS. Process exit1 remains unrelated pre-existing GameFeatureData AssetManager configuration errors; this is not a clean build claim.
- Fresh real PIE settled idle: root Z379.239630, pitch -1.601756?, velocity (0,0,.000041) cm/s, mass450kg, engine/shaftRPM0, both bow/prop spawn rates0 and visibilityfalse. Water plane400 => midship visual draft about20.8cm. `draft-profile-final-idle.json` / `profile-final-idle.png` show dry wood with continuous outside water.
- Actual runtime bow/contact eight-case check rerun on the force-saved Blueprint and passed. Editor left on M_WaterPhysicsTest with PIE stopped. High-wave over-rim behavior remains outside this acceptance.

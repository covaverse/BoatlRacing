# Reference series: Ghislain Girardot, Advanced Boat Simulation — 2026-10-02

Three-part series by **Ghislain Girardot**. The videos would not play in the
automated browser tab, but the **transcripts were readable** through YouTube's
own transcript panel, so this is taken from his own words plus the chapter
lists, not from guessing.

| part | id | length | topic |
|---|---|---|---|
| 1 | `hbrBCOxeLqw` | 30:25 | Buoyancy system driven by Niagara |
| 2 | `buboAqQfj1k` | 22:52 | **Diffusing foam system via scene capture** |
| 3 | `aNLzUoGWMhc` | 26:30 | **Niagara splash system** |

He states up front that the project is three separate systems: a Niagara-driven
buoyancy system, a scene-capture-driven foam system, and a Niagara-driven splash
system.

## Part 2 — the foam system, in full

This is the "transported foam render target" this project's own notes have
listed as missing since the first water pass. His version:

1. **SceneCapture2D** attached to the boat, looking down at the water. It
   captures a **1000 cm area into a 1024 texture**, deliberately chosen so the
   ratio is **1 cm per pixel**.
2. **The capture actor's position is snapped to a 1 cm grid** — one texel.
   Without this the capture jitters as geometry moves between pixels. In his
   words: *"ensuring the scene capture component cannot move in world space by
   smaller increments than what one pixel in the render target accounts for in
   cm is quite important."*
3. What it captures is an **intersection map**: a vertical gradient showing how
   far geometry sits below the water surface, not a hard silhouette. A global
   flag is set to 1 for the capture and **back to 0 within the same frame**, so
   that gradient material is only used during the capture pass.
4. The capture location is published to a **Material Parameter Collection** for
   later use by the water material.
5. **Persistence needs a buffer.** A render target cannot be sampled and written
   in the same pass, so each tick the foam RT is copied into a buffer through a
   trivial one-texture-parameter material, and the buffer is what gets sampled.
6. A **composite material** with two texture parameters — the new intersection
   map and the foam buffer — produces the next foam state and writes it back
   into the foam RT:
   - the intersection map is **added** (new foam)
   - the buffer is **blurred with a cheap cubic blur** — this is the diffusion,
     and because it repeats every tick the foam keeps spreading
   - a small value is **subtracted** every update — decay, so it fades out
   - the UVs are **distorted by a cheap noise texture**, so each tick's
     distortion compounds and the foam swirls
   - a **box mask** fades the edge of the capture region
7. **Local to world.** The intersection map is local to the boat because the
   capture follows it, but the persistent foam must stay in world space — a
   static object must stay put in the texture. The composite material therefore
   offsets the buffer lookup by how far the capture moved, which is exactly why
   step 2's texel snapping matters.
8. The boat uses a translucent material during the capture pass.

## Part 3 — the splash system, from its chapter list

Not transcribed in detail; the structure is clear from the chapters.

- **Boat Hull Map** and **Boat Hull Proxy** — the hull is baked into a texture,
  built by a **Blueprint scan tool**.
- **Uniform distribution** — probe particles spread evenly over that hull.
- **First emitter**: the probes themselves, with their own spawn and update
  stacks.
- **Second emitter**: the visible splashes. It uses an **Attribute Reader** to
  sample the first emitter's particle attributes, so splashes spawn where the
  hull actually meets water and with the right intensity, rather than from a
  global speed value. Then SubUV, initialize, update, and a splash material.

## How this maps onto BoatlRacing

- `T_BoatDryProfile` is already the equivalent of his **boat hull map** — 532
  stations of measured hull half-width — and `M_BoatHullFluidForce` already
  reads it to stamp hull-shaped force into the fluid sim. The hull data for a
  probe distribution exists.
- Buoyancy is already handled by the Water plugin's `UBuoyancyComponent`, so
  part 1 is not needed.
- The foam is still **amplitude-driven shading** off `FluidDelta`, with no
  memory of its own. Part 2's system is the missing piece and is the one worth
  building.
- The splash currently keys off `clamp(speed/90)` plus a hull-wide
  `clamp(-velocityZ/380)^2` slam term. Part 3 replaces that with per-probe hull
  contact.

Build order by value: **part 2 foam first** (it is the look being asked for and
the project already has the hull profile and an MPC pattern), then the per-probe
splash.

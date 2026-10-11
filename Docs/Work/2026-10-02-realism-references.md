# Realism references and what they changed — 2026-10-02, Asia/Bangkok

Sources consulted and the numbers taken from them, so later passes can argue
with the reference rather than with somebody's taste.

## Real longtail boats

- Tourist and river longtails run **15-30 km/h** on 25-40 HP outboards; a
  typical unit is 627 cc / 23 HP weighing 34.9 kg.
  ([northofknown](https://www.northofknown.com/thai-longtail-boats/),
  [Alibaba speed guide](https://carinterior.alibaba.com/buyingguides/how-fast-are-thailand's-longtail-boats-),
  [grboat](https://www.grboat.com/hondalongtailboat.html))
- Thai **racing** longtails are a different machine: turbo diesel or four-cylinder
  automotive conversions over 400 HP, drag-racing above **200 km/h**.
  ([Diesel Army](https://www.dieselarmy.com/news/boat-racing-diesel-powered-thai-long-tail/),
  [THAILAND LONG-TAIL BOAT CHAMPIONSHIP](https://chanthaburi.prd.go.th/th/content/category/detail/id/33/iid/337988))

The project's 110 km/h target therefore sits sensibly between a fast tourist
boat and a drag racer, and the 200 kg engine mass is reasonable for a
four-cylinder "K" conversion plus shaft and mount. **No change needed.**

## Planing trim — this was the one real error

Planing-hull resistance is minimum at **3-4 degrees bow up**, rising again
either side of that, and running bow-high past it just drags the transom and
burns fuel. During the transition onto plane the bow rears up well past that
before settling.
([boote-magazin](https://www.boote-magazin.de/en/boat-knowledge/beginner/boat-trim-the-3-most-important-motorboat-types-and-their-trim-angle/),
[ScienceDirect, high-speed planing hull design](https://www.sciencedirect.com/science/article/pii/S2092678216303764),
[Yamaha Outboards](https://yamahaoutboards.com/blog/boating/keep-your-boat-in-fighting-trim))

`ApplyVisualTrim` had this backwards: maximum bow-up at **zero** speed, decaying
to flat by 60 km/h. It now targets a world-space pitch of

```
target = -( 3.5 * clamp(speed/40) + 8 * clamp(1 - |speed-28|/26) ) * throttle
visual = target - hullPitch
```

so the visual mesh compensates for whatever the hull is doing and the total is
exactly the target. Measured in PIE:

| speed km/h | hull | visual | **total** |
|---|---|---|---|
| 3 | -4.88 | +4.87 | **-0.01** level at rest |
| 21 | -3.59 | -2.86 | **-6.45** |
| 29 | -2.45 | -7.29 | **-9.74** planing hump |
| 45 | -1.74 | -4.95 | **-6.69** |
| 62 | -2.43 | -1.08 | **-3.52** |
| 99 | -3.43 | -0.07 | **-3.50** |
| 110 | -2.19 | -1.30 | **-3.49** on the 3-4 degree optimum |

## Wake angle

Deep-water wakes hold Kelvin's **19.47 degrees** half-angle only below
Fr ≈ 0.5; above that the wake narrows roughly as 1/Fr, Mach-cone style, and
planing boats show **10 degrees or less**.
([Rabaud & Moisy, PRL 110 214503](https://link.aps.org/doi/10.1103/PhysRevLett.110.214503),
[arXiv 1309.6751](https://arxiv.org/pdf/1309.6751),
[Physics World](https://physicsworld.com/a/physicists-rethink-celebrated-kelvin-wake-pattern-for-ships/),
[Wikipedia](https://en.wikipedia.org/wiki/Kelvin_wake_pattern))

For this hull (collision length **6.20 m**, so Fr = U/sqrt(g*6.2)):

| km/h | Fr | expected half-angle |
|---|---|---|
| 10 | 0.36 | 19.5 Kelvin |
| **14** | **0.50** | **transition** |
| 28 | 1.00 | 9.8 |
| 60 | 2.14 | 4.6 |
| 110 | 3.92 | 2.5 |

This says the narrow foam band hugging the hull at racing speed is **correct**,
not a bug — a 19.5 degree V at 110 km/h would be wrong. It also means a wide V
should only ever appear below about 14 km/h. Nothing was changed for this; it is
recorded so the wake is not "fixed" in the wrong direction later.

## Still unverified against references

- Turning circle. 109 m at 38 degrees of tail angle has no reference behind it;
  no published figures for longtail turning radius were found.
- Spray droplet size and fall rate are tuned by eye. Gravity is deliberately
  **-1900** rather than the real -980, because small droplets in reality are
  slowed by air drag and the visual target was water that falls fast.


## Spray built as two layers, from engine assets only

Real spray at speed is discrete droplets near the source plus a haze further
out, so it is modelled as two systems rather than one. **No asset was
downloaded** — the engine already ships what was needed:

| asset | role |
|---|---|
| `/Engine/Tutorial/SubEditors/TutorialAssets/T_SmokeSubUV_8X8` | 8x8 smoke flipbook, used for the haze |
| `/Engine/EngineVolumetrics/Fogsheet/Materials/T_EV_FogSheet_CloudTex_01/02` | fog sheet textures (not used, kept as the alternative) |
| `/Water/Textures/Foam/T_WaterFlow_03_Foam_Tiled` | already used by the water foam and the exhaust |

- **Droplets** — `NS_LongtailSideSpray`: 1.5-5 cm sprites, `300 + 1400a` per
  second, gravity -1900, drag 0.08, life 0.30-0.85 s. Falls fast like water.
- **Haze** — `NS_LongtailSprayMist` with a new `M_LongtailSprayMist`: unlit,
  translucent, opacity from the flipbook's **alpha** channel times particle
  alpha. Sprites 70-185 cm at `9 + 38a` per second, alpha 0.14, life 1.2-2.8 s,
  gravity -260, drag 2.2 — it hangs and rolls instead of falling.

Taking opacity from the flipbook's **R** channel instead of **A** was the first
attempt and rendered the sprites as visible hard-edged quads; the alpha channel
is the mask. Density went through three passes: too thin, then thick enough to
hide the boat entirely, then settled at alpha 0.14.

Both are spawned by `SetupSideSpray` and driven by `UpdateSideSpray` from
`clamp(speed/90)`.


## CS2-style volumetric smoke — what it would actually take

The reference asked for is Counter-Strike 2's smoke, which is genuinely
volumetric: a 3D density volume, lit by the scene and carved by gunfire, not
camera-facing billboards. UE 5.8 can do that, and everything needed is already
on disk:

| capability | state |
|---|---|
| `NiagaraFluids` plugin, Grid3D gas simulation (`Fluids_Gas_Manager`, `Grid3D_Advect*`, `MI_3DGas_Base`) | installed, **not enabled** in `BoatlRacing.uproject` |
| `HeterogeneousVolumeComponent`, `SparseVolumeTexture` | in the engine runtime |
| `Volumetrics` plugin — RayMarching, VolumeTextures, SubUVMaker | installed |

It was **not** enabled, because the shape of the problem differs from CS2's:

- CS2 renders a handful of smokes that sit still and persist for seconds. This
  boat emits continuously along a 6 m hull at 110 km/h with the camera on top of
  it, so the volume has to translate with the boat every frame.
- Cost scales with resolution cubed. The water ripple solver already running is
  1024² = ~1M cells in **2D**. A 128³ gas grid is ~2M cells in **3D** with
  advection and a pressure solve each frame, and 128³ across a 10 m domain is
  only 8 cm voxels — coarse for close-up spray.
- The editor had already raised a memory-pressure warning during this session.

Enabling it is a `.uproject` change plus an editor restart plus a real
performance experiment, so it is left as a decision rather than done quietly.

What was done instead is the cheap part of the same look: a `SubUVAnimation`
module (`/Niagara/Modules/Update/SubUV/V2/SubUVAnimation`) on both mist
emitters, with **Random Start Frame** on. Each puff now plays through all 64
frames of the flipbook over its own lifetime and starts on a different frame, so
the smoke rolls and evolves instead of every sprite showing the same static
image. That is what reads as volume at this distance; it is not volumetric
rendering.

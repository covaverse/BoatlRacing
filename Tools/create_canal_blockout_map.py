"""Thai khlong blockout: 1.85 km canal (~1 min at 110 km/h), gentle bends, turning basins.

Re-runnable: rebuilds everything in the "Blockout" outliner folder, keeps other edits.
Water is the duplicated M_WaterPhysicsTest Ocean (z=400, current water look); land boxes cover it.
"""
import math
import random
import unreal

SOURCE = "/Game/Maps/M_WaterPhysicsTest"   # latest water/foam setup lives here
MAP = "/Game/Maps/M_CanalBlockout"
MAT_DIR = "/Game/Blockout/Materials"

WATER_Z = 400.0
BANK_TOP = 480.0          # concrete embankment 80 cm above water
HALF_W = 1500.0           # canal is 30 m wide
BANK_D = 10000.0          # bank strip depth, 100 m inland
# (length, lateral shift) in cm; cosine-eased bends are R 360-450 m, full lock is ~R 110 m.
# The middle four are the original 1 km layout; the rest extends it to ~1 minute of driving.
SEGS = [(10000, 0), (25000, -3500), (10000, 0),
        (25000, 0), (30000, 4000), (15000, 0), (30000, -4000),
        (10000, 0), (25000, 3500), (5000, 0)]
X0 = -sum(L for L, _ in SEGS) / 2   # canal mouths at X0 / X1
X1 = -X0
BASIN = 27000.0           # open turning water beyond each mouth
OCEAN_X = 300000.0        # rendered Ocean length; matches the WaterZone and +-1500 m collision
BRIDGES = (X0 + 40000, X0 + 107500)
START = unreal.Vector(X0 - 4000, 0, 390)

cube = unreal.load_asset("/Engine/BasicShapes/Cube")
cylinder = unreal.load_asset("/Engine/BasicShapes/Cylinder")
grid = unreal.load_asset("/Engine/EngineMaterials/WorldGridMaterial")
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
spawned = []


def center_y(x):
    u, y = x - X0, 0.0
    for length, shift in SEGS:
        t = min(max(u / length, 0.0), 1.0)
        y += shift * (1 - math.cos(math.pi * t)) / 2
        u -= length
    return y


def frame(x):
    """Canal centre, unit normal (toward +Y) and yaw in degrees at x."""
    slope = (center_y(x + 50) - center_y(x - 50)) / 100
    yaw = math.atan(slope)
    return center_y(x), (-math.sin(yaw), math.cos(yaw)), math.degrees(yaw)


def color_mat(name, rgb):
    path = f"{MAT_DIR}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(path):
        mi = unreal.load_asset(path)
    else:
        mi = unreal.AssetToolsHelpers.get_asset_tools().create_asset(
            name, MAT_DIR, unreal.MaterialInstanceConstant,
            unreal.MaterialInstanceConstantFactoryNew())
        unreal.MaterialEditingLibrary.set_material_instance_parent(
            mi, unreal.load_asset("/Engine/BasicShapes/BasicShapeMaterial"))
    unreal.MaterialEditingLibrary.set_material_instance_vector_parameter_value(
        mi, "Color", unreal.LinearColor(*rgb, 1.0))
    unreal.EditorAssetLibrary.save_loaded_asset(mi)
    return mi


def box(folder, label, x, y, z, size, mat, yaw=0.0, roll=0.0, mesh=None):
    """size = full (X, Y, Z) extent in cm; Basic shapes are 100 cm, centred."""
    a = actors.spawn_actor_from_class(unreal.StaticMeshActor, unreal.Vector(x, y, z),
                                      unreal.Rotator(roll=roll, pitch=0.0, yaw=yaw))
    smc = a.static_mesh_component
    smc.set_static_mesh(mesh or cube)
    smc.set_material(0, mat)
    a.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
    a.set_folder_path(f"Blockout/{folder}")
    a.set_actor_label(label)
    spawned.append(a)
    return a


def slab(folder, label, x_min, x_max, y_min, y_max, top, mat):
    box(folder, label, (x_min + x_max) / 2, (y_min + y_max) / 2, top / 2,
        (x_max - x_min, y_max - y_min, top), mat)


# --- map ---------------------------------------------------------------------------
# Run inside the open editor (Cmd: py <this file>), never headless: a -nullrhi duplicate
# saved a map whose Ocean never renders. Duplicate is saved before loading, and an
# already-open MAP is reused, because reloading an in-memory world is a fatal GC error.
world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
if world.get_outermost().get_name() != MAP:
    if not unreal.EditorAssetLibrary.does_asset_exist(MAP):
        assert unreal.EditorAssetLibrary.duplicate_asset(SOURCE, MAP)
        assert unreal.EditorAssetLibrary.save_asset(MAP, only_if_is_dirty=False)
    assert unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(MAP)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
assert world.get_outermost().get_name() == MAP

for a in actors.get_all_level_actors():
    if str(a.get_folder_path()).startswith("Blockout"):
        a.destroy_actor()

concrete = grid
land = color_mat("MI_Blockout_Land", (0.12, 0.28, 0.08))
walls = [color_mat("MI_Blockout_HouseWood", (0.40, 0.25, 0.13)),
         color_mat("MI_Blockout_HouseWhite", (0.75, 0.72, 0.65))]
roof = color_mat("MI_Blockout_Roof", (0.55, 0.16, 0.08))
signal = color_mat("MI_Blockout_Signal", (0.95, 0.75, 0.05))

for a in actors.get_all_level_actors():
    if isinstance(a, unreal.WaterBodyOcean):   # default 1600 m only reached +-800 m
        comp = a.get_editor_property("water_body_component")
        comp.set_editor_property("ocean_extents", unreal.Vector2D(OCEAN_X, 51200))
    elif a.get_class().get_name() == "BP_LongtailPhysicsPawn_C":
        a.set_actor_location(START, False, True)
        a.set_actor_rotation(unreal.Rotator(roll=0, pitch=0, yaw=180), True)  # bow is local -X
    elif a.get_class().get_name() == "BP_FluidSim_01_C":
        a.set_actor_location(unreal.Vector(START.x, START.y, WATER_Z), False, True)

# --- banks: 10 m strips, 4 m overlap so the outside of a bend has no gaps -------------
STEP = 1000.0
x = X0
while x < X1 - 1:
    xm = x + STEP / 2
    y, (nx, ny), yaw = frame(xm)
    length = STEP / math.cos(math.radians(yaw)) + 400
    for side in (1, -1):
        off = side * (HALF_W + BANK_D / 2)
        box("Banks", f"Bank_{'L' if side > 0 else 'R'}_{int(x - X0) // 100:04d}",
            xm + nx * off, y + ny * off, BANK_TOP / 2, (length, BANK_D, BANK_TOP), concrete, yaw)
    x += STEP

# land fill between the bank strips and the water edge (Y +-25000), and outside it.
# Fill starts 5 m inside the nearest bank strip edge so no gap opens over the bends.
ys = [center_y(X0 + i * 500) for i in range(int((X1 - X0) / 500) + 1)]
slab("Land", "Fill_L", X0, X1, min(ys) + HALF_W + BANK_D - 500, 25100, BANK_TOP - 5, land)
slab("Land", "Fill_R", X0, X1, -25100, max(ys) - HALF_W - BANK_D + 500, BANK_TOP - 5, land)
slab("Land", "Outer_L", -250000, 250000, 25000, 200000, BANK_TOP, land)
slab("Land", "Outer_R", -250000, 250000, -200000, -25000, BANK_TOP, land)
slab("Land", "Outer_E", X1 + BASIN, 250000, -25000, 25000, BANK_TOP, land)
slab("Land", "Outer_W", -250000, X0 - BASIN, -25000, 25000, BANK_TOP, land)

# --- houses: gable-roofed boxes 3-8 m back from the water ---------------------------
rng = random.Random(7)
houses = 0
for side in (1, -1):
    x = X0 + 1500
    while x < X1 - 1500:
        if min(abs(x - b) for b in BRIDGES) > 2500 and rng.random() > 0.2:
            length, depth = rng.uniform(700, 1200), rng.uniform(600, 900)
            height = (depth + 60) / 2 + rng.uniform(40, 150)
            off = side * (HALF_W + rng.uniform(300, 800) + depth / 2)
            y, (nx, ny), yaw = frame(x)
            hx, hy = x + nx * off, y + ny * off
            box("Houses", f"House_{houses:03d}", hx, hy, BANK_TOP + height / 2,
                (length, depth, height), walls[houses % 2], yaw)
            r = (depth + 60) / math.sqrt(2)
            box("Houses", f"Roof_{houses:03d}", hx, hy, BANK_TOP + height,
                (length + 60, r, r), roof, yaw, roll=45)
            houses += 1
        x += rng.uniform(1800, 3200)

# --- bridges (6 m clearance) on straights -------------------------------------------
span = 2 * HALF_W + 2000
for i, bx in enumerate(BRIDGES):
    y, (nx, ny), yaw = frame(bx)
    box("Bridge", f"Bridge{i}_Deck", bx, y, WATER_Z + 640, (600, span, 80), concrete, yaw)
    for side in (1, -1):
        off = side * (HALF_W + 500)
        box("Bridge", f"Bridge{i}_Abutment_{side:+d}", bx + nx * off, y + ny * off,
            (BANK_TOP + WATER_Z + 600) / 2, (600, 800, WATER_Z + 600 - BANK_TOP), concrete, yaw)
        off = side * 280
        box("Bridge", f"Bridge{i}_Rail_{side:+d}", bx - ny * off, y + nx * off,
            WATER_Z + 730, (20, span, 100), signal, yaw)

# --- start / finish gates and 100 m markers ----------------------------------------
for name, gx in (("Start", X0), ("Finish", X1)):
    y, (nx, ny), yaw = frame(gx)
    for side in (1, -1):
        off = side * (HALF_W + 200)
        box("Gates", f"{name}_Pole_{side:+d}", gx + nx * off, y + ny * off, BANK_TOP + 400,
            (40, 40, 800), signal, yaw, mesh=cylinder)
    box("Gates", f"{name}_Banner", gx, y, BANK_TOP + 780, (30, 2 * HALF_W + 440, 120), signal, yaw)

for metres in range(100, int((X1 - X0) / 100), 100):
    mx = X0 + metres * 100
    y, (nx, ny), yaw = frame(mx)
    off = HALF_W + 150
    box("Markers", f"Marker_{metres}m_Pole", mx + nx * off, y + ny * off, BANK_TOP + 200,
        (30, 30, 400), signal, yaw, mesh=cylinder)
    t = actors.spawn_actor_from_class(unreal.TextRenderActor,
                                      unreal.Vector(mx + nx * off, y + ny * off, BANK_TOP + 420),
                                      unreal.Rotator(roll=0, pitch=0, yaw=yaw + 180))
    text = t.text_render
    text.set_text(unreal.Text(f"{metres} m"))
    text.set_editor_property("world_size", 220)
    text.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    text.set_editor_property("text_render_color", unreal.Color(r=255, g=220, b=0, a=255))
    t.set_folder_path("Blockout/Markers")
    t.set_actor_label(f"Marker_{metres}m_Text")

# --- check: canal water is clear down the middle and at the edges, banks block just outside.
# Exact point-in-box (basic shapes span +-50 local); editor-world traces hit nothing headless.
def solid(x, y, z):
    p = unreal.Vector(x, y, z)
    for a in spawned:
        local = a.get_actor_transform().inverse_transform_location(p)
        if abs(local.x) <= 50 and abs(local.y) <= 50 and abs(local.z) <= 50:
            return True
    return False


for x in range(int(X0) + 500, int(X1), 2500):
    y, (nx, ny), _ = frame(x)
    for off in (0.0, HALF_W - 100, -(HALF_W - 100)):
        for z in (420, 900):
            assert not solid(x + nx * off, y + ny * off, z), ("canal blocked", x, off, z)
    for off in (HALF_W + 100, -(HALF_W + 100)):
        assert solid(x + nx * off, y + ny * off, 450), ("bank missing", x, off)

assert unreal.EditorLoadingAndSavingUtils.save_map(world, MAP)
print("BOAT_CANAL_BLOCKOUT_SAVED", MAP, "length_m", (X1 - X0) / 100, "houses", houses,
      "bridges", BRIDGES, "start", START)

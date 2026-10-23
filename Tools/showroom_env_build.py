"""Showroom set for M_Garage, styled to match the menu theme (dark graphite, gold light strips, warm spots).

Replaces the orange blockout set with: glossy dark floor, turntable plinth with a glowing gold rim, dark walls
and ceiling, an LED screen showing the canal race scene from UI_REF2, the game logo, Thai flags and gold
LED strips, plus key/rim/fill/top spot lights and a post-process volume.
Run from a live editor (PIE stopped) after SourceAssets/UI/Showroom/make_showroom_art.ps1 and
Tools/mainmenu_build.py (for the logo texture):
  python Tools/run_editor_script.py Tools/showroom_env_build.py
Everything it creates is labelled SR_* in the Showroom/Set and Showroom/Lighting folders and is rebuilt on
every run. The old blockout set is deleted (backup the map first; Tools/create_frontend_scenes.py rebuilds it).
"""
import importlib
import sys
from pathlib import Path

import unreal

sys.path.insert(0, str(Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / "Tools"))
import ui_theme
importlib.reload(ui_theme)

GARAGE = "/Game/Maps/M_Garage"
MATERIALS = "/Game/Showroom/Materials"
TEXTURES = "/Game/Showroom/Textures"
ART = ui_theme.ROOT / "SourceAssets/UI/Showroom/Textures"
CUBE = "/Engine/BasicShapes/Cube"
CYLINDER = "/Engine/BasicShapes/Cylinder"
CENTER = unreal.Vector(80, 0, 0)       # turntable centre (BP_ShowroomStage sits here at z=96)
PLINTH_TOP = 96.0
EXPOSURE_EV = 6.5
# Blockout pieces from create_frontend_scenes.py / install_boat_frontend.py that this set replaces.
OLD_FOLDERS = ("Frontend/Set",)
OLD_LABELS = ("Garage_", "Frontend_DisplayPlatform", "DirectionalLight", "PointLight")

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"
tools = unreal.AssetToolsHelpers.get_asset_tools()
mel = unreal.MaterialEditingLibrary
actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

# ---------------------------------------------------------------- textures and materials
art = ui_theme.import_textures(sorted(ART.glob("*.png")), TEXTURES)
art["T_MM_CropLogo"] = unreal.load_asset("/Game/UI/MainMenu/Textures/T_MM_CropLogo")
assert art["T_MM_CropLogo"], "run Tools/mainmenu_build.py first"
for texture in art.values():
    # These are seen in 3D at a distance; give them mips back so they do not shimmer.
    texture.set_editor_property("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_FROM_TEXTURE_GROUP)
    texture.set_editor_property("lod_group", unreal.TextureGroup.TEXTUREGROUP_WORLD)
    texture.set_editor_property("compression_settings", unreal.TextureCompressionSettings.TC_DEFAULT)
    unreal.EditorAssetLibrary.save_loaded_asset(texture, only_if_is_dirty=False)


def master(name, build):
    path = f"{MATERIALS}/{name}"
    material = unreal.load_asset(path)
    if not material:
        material = tools.create_asset(name, MATERIALS, unreal.Material, unreal.MaterialFactoryNew())
    mel.delete_all_material_expressions(material)
    build(material)
    mel.recompile_material(material)
    unreal.EditorAssetLibrary.save_loaded_asset(material, only_if_is_dirty=False)
    return material


def vector(material, name, value, y):
    node = mel.create_material_expression(material, unreal.MaterialExpressionVectorParameter, -500, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", value)
    return node


def scalar(material, name, value, y):
    node = mel.create_material_expression(material, unreal.MaterialExpressionScalarParameter, -500, y)
    node.set_editor_property("parameter_name", name)
    node.set_editor_property("default_value", value)
    return node


def build_surface(material):
    """Lit surface: colour, metallic, roughness and an optional emissive glow."""
    mel.connect_material_property(vector(material, "BaseColor", unreal.LinearColor(0.02, 0.02, 0.025, 1), 0), "", unreal.MaterialProperty.MP_BASE_COLOR)
    mel.connect_material_property(scalar(material, "Metallic", 0.0, 150), "", unreal.MaterialProperty.MP_METALLIC)
    mel.connect_material_property(scalar(material, "Roughness", 0.5, 250), "", unreal.MaterialProperty.MP_ROUGHNESS)
    glow = mel.create_material_expression(material, unreal.MaterialExpressionMultiply, -250, 400)
    mel.connect_material_expressions(vector(material, "Emissive", unreal.LinearColor(0, 0, 0, 1), 350), "", glow, "A")
    mel.connect_material_expressions(scalar(material, "EmissiveStrength", 0.0, 500), "", glow, "B")
    mel.connect_material_property(glow, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)


def build_image(material):
    """Unlit picture for the LED screen, logo panel and flags."""
    material.set_editor_property("shading_model", unreal.MaterialShadingModel.MSM_UNLIT)
    sample = mel.create_material_expression(material, unreal.MaterialExpressionTextureSampleParameter2D, -600, 0)
    sample.set_editor_property("parameter_name", "Image")
    sample.set_editor_property("texture", art["T_SR_Screen"])
    bright = mel.create_material_expression(material, unreal.MaterialExpressionMultiply, -250, 0)
    mel.connect_material_expressions(sample, "RGB", bright, "A")
    mel.connect_material_expressions(scalar(material, "Brightness", 1.0, 200), "", bright, "B")
    mel.connect_material_property(bright, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)


surface = master("M_SR_Surface", build_surface)
image = master("M_SR_Image", build_image)


def instance(name, parent, vectors=None, scalars=None, textures=None):
    path = f"{MATERIALS}/{name}"
    mi = unreal.load_asset(path)
    if not mi:
        mi = tools.create_asset(name, MATERIALS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi.set_editor_property("parent", parent)
    for key, value in (vectors or {}).items():
        mel.set_material_instance_vector_parameter_value(mi, key, value)
    for key, value in (scalars or {}).items():
        mel.set_material_instance_scalar_parameter_value(mi, key, value)
    for key, value in (textures or {}).items():
        mel.set_material_instance_texture_parameter_value(mi, key, value)
    mel.update_material_instance(mi)
    unreal.EditorAssetLibrary.save_loaded_asset(mi, only_if_is_dirty=False)
    return mi


GOLD = unreal.LinearColor(1.0, 0.55, 0.08, 1)
mats = {
    "floor": instance("MI_SR_Floor", surface, {"BaseColor": unreal.LinearColor(0.010, 0.011, 0.014, 1)}, {"Roughness": 0.16, "Metallic": 0.0}),
    "wall": instance("MI_SR_Wall", surface, {"BaseColor": unreal.LinearColor(0.022, 0.024, 0.03, 1)}, {"Roughness": 0.65}),
    "plinth": instance("MI_SR_Plinth", surface, {"BaseColor": unreal.LinearColor(0.035, 0.036, 0.042, 1)}, {"Roughness": 0.3, "Metallic": 0.7}),
    "gold": instance("MI_SR_GoldLight", surface, {"BaseColor": unreal.LinearColor(0.2, 0.12, 0.02, 1), "Emissive": GOLD}, {"EmissiveStrength": 18.0, "Roughness": 0.4}),
    "rim": instance("MI_SR_GoldRim", surface, {"BaseColor": unreal.LinearColor(0.2, 0.12, 0.02, 1), "Emissive": GOLD}, {"EmissiveStrength": 9.0}),
    "frame": instance("MI_SR_ScreenFrame", surface, {"BaseColor": unreal.LinearColor(0.01, 0.01, 0.012, 1), "Emissive": GOLD}, {"EmissiveStrength": 2.0, "Metallic": 0.8, "Roughness": 0.3}),
    "screen": instance("MI_SR_Screen", image, scalars={"Brightness": 1.6}, textures={"Image": art["T_SR_Screen"]}),
    "logo": instance("MI_SR_Logo", image, scalars={"Brightness": 1.4}, textures={"Image": art["T_MM_CropLogo"]}),
    "flag": instance("MI_SR_FlagThai", image, scalars={"Brightness": 0.55}, textures={"Image": art["T_SR_FlagThai"]}),
}
print("SHOWROOM_ENV_MATERIALS", len(mats))

# ---------------------------------------------------------------- level: remove blockout, rebuild set
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
assert levels.load_level(GARAGE)
removed = 0
for actor in actors.get_all_level_actors():
    label, folder = actor.get_actor_label(), str(actor.get_folder_path())
    if label.startswith("SR_") or folder.startswith(OLD_FOLDERS) or label.startswith(OLD_LABELS):
        actors.destroy_actor(actor)
        removed += 1


def block(label, mesh, location, size, material, rotation=unreal.Rotator(0, 0, 0), folder="Showroom/Set"):
    """Static mesh sized in centimetres (basic shapes are 100 cm)."""
    actor = actors.spawn_actor_from_class(unreal.StaticMeshActor, location, rotation)
    actor.set_actor_label(label)
    actor.set_folder_path(folder)
    component = actor.static_mesh_component
    component.set_static_mesh(unreal.load_asset(mesh))
    component.set_material(0, material)
    actor.set_actor_scale3d(unreal.Vector(size[0] / 100, size[1] / 100, size[2] / 100))
    return actor


wall_y = 1100.0
face_y = wall_y - 20  # front face of the back wall
block("SR_Floor", CUBE, unreal.Vector(80, 0, -5), (6000, 6000, 10), mats["floor"])
block("SR_Ceiling", CUBE, unreal.Vector(80, 0, 1705), (6000, 6000, 10), mats["wall"])
block("SR_BackWall", CUBE, unreal.Vector(80, wall_y, 850), (5000, 40, 1700), mats["wall"])
block("SR_RightWall", CUBE, unreal.Vector(2400, -900, 850), (40, 4000, 1700), mats["wall"])
block("SR_LeftWall", CUBE, unreal.Vector(-2300, -900, 850), (40, 4000, 1700), mats["wall"])
block("SR_FrontWall", CUBE, unreal.Vector(80, -2900, 850), (5000, 40, 1700), mats["wall"])

# Turntable plinth with a glowing gold rim just under its top edge.
block("SR_Plinth", CYLINDER, unreal.Vector(CENTER.x, CENTER.y, PLINTH_TOP / 2), (990, 990, PLINTH_TOP), mats["plinth"])
block("SR_PlinthRim", CYLINDER, unreal.Vector(CENTER.x, CENTER.y, PLINTH_TOP - 9), (1020, 1020, 6), mats["rim"])
block("SR_FloorRing", CYLINDER, unreal.Vector(CENTER.x, CENTER.y, 1), (1140, 1140, 2), mats["rim"])
block("SR_FloorRingInner", CYLINDER, unreal.Vector(CENTER.x, CENTER.y, 1.5), (1110, 1110, 2), mats["floor"])

# LED screen (aspect of T_SR_Screen) in a thin gold-lit frame, logo above it.
screen_w, screen_h, screen_z = 1700, 1700 * 323 / 1342, 560
block("SR_ScreenFrame", CUBE, unreal.Vector(CENTER.x, face_y - 3, screen_z), (screen_w + 40, 6, screen_h + 40), mats["frame"])
block("SR_Screen", CUBE, unreal.Vector(CENTER.x, face_y - 7, screen_z), (screen_w, 4, screen_h), mats["screen"])
block("SR_Logo", CUBE, unreal.Vector(CENTER.x, face_y - 4, screen_z + screen_h / 2 + 190), (520, 4, 520 * 178 / 528), mats["logo"])

# Gold LED strips framing the screen, a base line along the wall, and Thai flags between the strips.
for index, x in enumerate((-1500, -950, 1110, 1660)):
    block(f"SR_Strip{index}", CUBE, unreal.Vector(x, face_y - 4, 820), (14, 6, 1500), mats["gold"])
block("SR_BaseLine", CUBE, unreal.Vector(80, face_y - 4, 10), (5000, 6, 8), mats["gold"])
for index, x in enumerate((-1225, 1385)):
    block(f"SR_Flag{index}", CUBE, unreal.Vector(x, face_y - 4, 700), (330, 3, 220), mats["flag"])
    block(f"SR_FlagPole{index}", CUBE, unreal.Vector(x, face_y - 6, 820), (360, 8, 6), mats["frame"])

# ---------------------------------------------------------------- lighting
def spot(label, location, target, color, lumens, outer_cone):
    rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
    light = actors.spawn_actor_from_class(unreal.SpotLight, location, rotation)
    light.set_actor_label(label)
    light.set_folder_path("Showroom/Lighting")
    component = light.spot_light_component
    component.set_editor_property("intensity_units", unreal.LightUnits.LUMENS)
    component.set_editor_property("intensity", lumens)
    component.set_editor_property("light_color", color)
    component.set_editor_property("attenuation_radius", 5000.0)
    component.set_editor_property("outer_cone_angle", outer_cone)
    component.set_editor_property("inner_cone_angle", outer_cone * 0.55)
    component.set_editor_property("source_radius", 30.0)
    return light


boat = unreal.Vector(CENTER.x, CENTER.y, 150)
spot("SR_KeyLight", unreal.Vector(-700, -1200, 1250), boat, unreal.Color(255, 214, 170), 90000, 30)
spot("SR_FillLight", unreal.Vector(1300, -1100, 700), boat, unreal.Color(190, 210, 255), 25000, 34)
spot("SR_RimLight", unreal.Vector(450, 900, 1300), boat, unreal.Color(255, 170, 70), 70000, 28)
spot("SR_TopLight", unreal.Vector(CENTER.x, CENTER.y, 1650), unreal.Vector(CENTER.x, CENTER.y, 0), unreal.Color(255, 236, 214), 60000, 36)

for actor in actors.get_all_level_actors():
    if isinstance(actor, unreal.SkyLight):
        actor.light_component.set_editor_property("intensity", 0.06)  # just enough to lift pure-black shadows

post = actors.spawn_actor_from_class(unreal.PostProcessVolume, unreal.Vector(CENTER.x, CENTER.y, 300))
post.set_actor_label("SR_Post")
post.set_folder_path("Showroom/Lighting")
post.set_editor_property("unbound", True)
settings = post.get_editor_property("settings")
# Pin exposure: auto exposure lifts this mostly-dark room until it looks washed out.
for key, value in (("override_auto_exposure_min_brightness", True), ("auto_exposure_min_brightness", EXPOSURE_EV),
                   ("override_auto_exposure_max_brightness", True), ("auto_exposure_max_brightness", EXPOSURE_EV),
                   ("override_bloom_intensity", True), ("bloom_intensity", 0.9),
                   ("override_vignette_intensity", True), ("vignette_intensity", 0.55)):
    settings.set_editor_property(key, value)
post.set_editor_property("settings", settings)

# Idle scene capture used to render the part-card thumbnails from PIE (Python cannot spawn into PIE).
capture = actors.spawn_actor_from_class(unreal.SceneCapture2D, unreal.Vector(CENTER.x, -1500, 400))
capture.set_actor_label("SR_ThumbCapture")
capture.set_folder_path("Showroom/Tools")
capture.capture_component2d.set_editor_property("capture_every_frame", False)
capture.capture_component2d.set_editor_property("capture_on_movement", False)

assert levels.save_current_level()
print(f"SHOWROOM_ENV_READY removed={removed}")

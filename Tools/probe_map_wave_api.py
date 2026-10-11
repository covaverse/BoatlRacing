import json
import unreal


for cls_name in (
    "EditorLoadingAndSavingUtils",
    "EditorLevelLibrary",
    "WaterBodyOcean",
    "WaterWavesAssetReference",
):
    cls = getattr(unreal, cls_name, None)
    print("BOAT_MAP_API_CLASS", cls_name, cls)

for cls_name, method_name in (
    ("EditorLoadingAndSavingUtils", "load_map"),
    ("EditorLoadingAndSavingUtils", "save_map"),
    ("EditorLoadingAndSavingUtils", "save_dirty_packages"),
    ("EditorLevelLibrary", "get_all_level_actors"),
    ("EditorAssetLibrary", "duplicate_asset"),
    ("ToolsetLibrary", "set_object_properties"),
):
    method = getattr(getattr(unreal, cls_name, None), method_name, None)
    print("BOAT_MAP_API_METHOD", cls_name, method_name,
          (method.__doc__ or "")[:800] if method else "MISSING")

print("BOAT_MAP_NEW_OBJECT", (unreal.new_object.__doc__ or "")[:800])

reference_class = unreal.load_class(None, "/Script/Water.WaterWavesAssetReference")
print("BOAT_WAVE_REF_CLASS", reference_class)
if reference_class:
    reference = unreal.new_object(reference_class)
    print("BOAT_WAVE_REF_FIELDS", unreal.ToolsetLibrary.list_struct_properties(reference_class))
    path = "/Game/Water/Waves/WW_SmallGerstner.WW_SmallGerstner"
    print("BOAT_WAVE_REF_SET", unreal.ToolsetLibrary.set_object_properties(
        reference, json.dumps({"waterWavesAsset": path})))
    print("BOAT_WAVE_REF_READ", unreal.ToolsetLibrary.get_object_properties(reference, ["waterWavesAsset"]))

world = unreal.EditorLoadingAndSavingUtils.load_map("/Game/Maps/M_WaterPhysicsTest")
print("BOAT_MAP_LOADED", world)
ocean = next(actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()
             if actor.get_class() == unreal.WaterBodyOcean.static_class())
print("BOAT_MAP_OCEAN", ocean.get_path_name(),
      unreal.ToolsetLibrary.get_object_properties(ocean, ["waterWaves"]))
reference = unreal.new_object(reference_class, outer=ocean, name="ProbeWaveReference")
unreal.ToolsetLibrary.set_object_properties(reference, json.dumps({
    "waterWavesAsset": "/Game/Water/Waves/WW_SmallGerstner.WW_SmallGerstner"
}))
try:
    ocean.set_editor_property("water_waves", reference)
    print("BOAT_MAP_SET_NATIVE", True)
except Exception as error:
    print("BOAT_MAP_SET_NATIVE", error)
print("BOAT_MAP_SET_REFLECTION", unreal.ToolsetLibrary.set_object_properties(
    ocean, json.dumps({"waterWaves": {"refPath": reference.get_path_name()}})))
print("BOAT_MAP_WAVES_AFTER", unreal.ToolsetLibrary.get_object_properties(ocean, ["waterWaves"]))

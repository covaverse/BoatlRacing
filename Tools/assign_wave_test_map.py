import json
import re
import unreal


match = re.search(r"-BoatWavePreset=(Small|High)\b", unreal.SystemLibrary.get_command_line())
assert match, "Pass -BoatWavePreset=Small or -BoatWavePreset=High"
preset = match.group(1)
map_path = f"/Game/Maps/M_Water{preset}WavesTest"
wave_name = f"WW_{preset}Gerstner"
wave_path = f"/Game/Water/Waves/{wave_name}.{wave_name}"

assert unreal.EditorAssetLibrary.does_asset_exist(map_path)
assert unreal.EditorAssetLibrary.does_asset_exist(wave_path)
world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
assert world is not None
oceans = [actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()
          if actor.get_class() == unreal.WaterBodyOcean.static_class()]
assert len(oceans) == 1, (map_path, len(oceans))
ocean = oceans[0]
reference_class = unreal.load_class(None, "/Script/Water.WaterWavesAssetReference")
reference = unreal.new_object(reference_class, outer=ocean, name="AssignedWaves")
assert unreal.ToolsetLibrary.set_object_properties(
    reference, json.dumps({"waterWavesAsset": wave_path}))
ocean.set_editor_property("water_waves", reference)
selected = json.loads(unreal.ToolsetLibrary.get_object_properties(ocean, ["waterWaves"]))
assert selected["waterWaves"]["refPath"] == reference.get_path_name()
assert unreal.EditorLoadingAndSavingUtils.save_map(world, map_path)
print("BOAT_WAVE_MAP_SAVED", map_path, reference.get_path_name(), wave_path)

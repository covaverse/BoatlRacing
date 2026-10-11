import json
import re
import unreal


match = re.search(r"-BoatWavePreset=(Small|High)\b", unreal.SystemLibrary.get_command_line())
assert match, "Pass -BoatWavePreset=Small or -BoatWavePreset=High"
preset = match.group(1)
map_path = f"/Game/Maps/M_Water{preset}WavesTest"
wave_name = f"WW_{preset}Gerstner"
expected_asset = f"/Game/Water/Waves/{wave_name}.{wave_name}"

world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
assert world is not None
oceans = [actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()
          if actor.get_class() == unreal.WaterBodyOcean.static_class()]
assert len(oceans) == 1
ocean = oceans[0]
wave_state = json.loads(unreal.ToolsetLibrary.get_object_properties(ocean, ["waterWaves"]))
reference_path = wave_state["waterWaves"]["refPath"]
reference = unreal.load_object(None, reference_path)
assert reference is not None
asset_state = json.loads(unreal.ToolsetLibrary.get_object_properties(reference, ["waterWavesAsset"]))
actual_asset = asset_state["waterWavesAsset"]["refPath"]
assert actual_asset == expected_asset, (actual_asset, expected_asset)
source = unreal.load_object(None, f"{expected_asset}:WaterWaves")
assert source is not None
print("BOAT_WAVE_MAP_VERIFIED", preset, map_path, actual_asset,
      source.get_editor_property("max_wave_height"))

component = ocean.get_editor_property("water_body_component")
print("BOAT_COMPONENT_MAX_WAVE_HEIGHT", preset,
      component.get_max_wave_height())
for x in (6000.0, 5400.0, 4800.0, 4200.0):
    sample = component.get_water_surface_info_at_location(
        unreal.Vector(x, 1500.0, 0.0))
    assert sample is not None, (preset, x)
    print("BOAT_WATER_HEIGHT_SAMPLE", preset, x,
          sample[0].z, sample[1].x, sample[1].y, sample[1].z)
for name in dir(component):
    if "surface" in name or "water_info" in name or "wave_height" in name:
        print("BOAT_WATER_QUERY_METHOD", name, (getattr(component, name).__doc__ or "")[:350])

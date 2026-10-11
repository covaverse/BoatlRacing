import unreal


factory = unreal.WaterWavesAssetFactory()
for name in ("supported_class", "water_waves_class", "waves_source", "bCreateNew"):
    try:
        value = factory.get_editor_property(name)
    except Exception as error:
        value = f"UNAVAILABLE: {error}"
    print("BOAT_WAVE_FACTORY", name, value)

for name in ("WaterWaves", "WaterWavesAsset", "WaterWavesAssetReference"):
    cls = getattr(unreal, name, None)
    print("BOAT_WAVE_CLASS", name, cls)

for path in (
    "/Game/Boats/ThaiLongtail/Handling/BP_BoatHandlingData",
    "/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling",
):
    asset = unreal.EditorAssetLibrary.load_asset(path)
    print("BOAT_HANDLING_RELOAD", path, bool(asset), asset.get_class() if asset else "None")

wave = unreal.EditorAssetLibrary.load_asset("/Game/Water/Waves/WW_SmallGerstner")
print("BOAT_WAVE_REFLECTION", unreal.ToolsetLibrary.list_struct_properties(wave.get_class()))
for name in ("waterWaves", "WaterWaves", "water_waves"):
    try:
        print("BOAT_WAVE_REF_VALUE", name, unreal.ToolsetLibrary.get_object_properties(wave, [name]))
    except Exception as error:
        print("BOAT_WAVE_REF_ERROR", name, error)

source = unreal.load_object(None, "/Game/Water/Waves/WW_SmallGerstner.WW_SmallGerstner:WaterWaves")
print("BOAT_WAVE_SOURCE", source, source.get_class() if source else "None")
if source:
    print("BOAT_WAVE_SOURCE_FIELDS", unreal.ToolsetLibrary.list_struct_properties(source.get_class()))
    print("BOAT_WAVE_SOURCE_VALUES", unreal.ToolsetLibrary.get_object_properties(source, ["gerstnerWaveGenerator", "maxWaveHeight"]))

for wave_name in ("WW_SmallGerstner", "WW_HighGerstner"):
    wave_path = f"/Game/Water/Waves/{wave_name}.{wave_name}:WaterWaves"
    wave_source = unreal.load_object(None, wave_path)
    wave_generator = unreal.load_object(None, f"{wave_path}.WaterWaves")
    print("BOAT_WAVE_RELOAD", wave_name, wave_source.get_editor_property("max_wave_height"),
          wave_generator.get_editor_property("seed"), wave_generator.get_editor_property("max_amplitude"))

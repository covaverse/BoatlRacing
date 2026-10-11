import unreal


FOLDER = "/Game/Water/Waves"
NAMES = ("WW_SmallGerstner", "WW_HighGerstner")
asset_tools = unreal.AssetToolsHelpers.get_asset_tools()

for name in NAMES:
    path = f"{FOLDER}/{name}"
    asset = unreal.EditorAssetLibrary.load_asset(path)
    if asset is None:
        factory = unreal.WaterWavesAssetFactory()
        asset = asset_tools.create_asset(
            name, FOLDER, factory.get_editor_property("supported_class"), factory
        )
    assert asset is not None, path
    print("BOAT_WAVE_CREATED", asset.get_path_name(), asset.get_class())
    for property_name in ("water_waves", "waves_source", "gerstner_wave_generator"):
        try:
            value = asset.get_editor_property(property_name)
        except Exception as error:
            value = f"UNAVAILABLE: {error}"
        print("BOAT_WAVE_PROPERTY", name, property_name, value)
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)

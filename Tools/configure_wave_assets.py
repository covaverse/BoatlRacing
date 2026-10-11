import unreal


PRESETS = {
    "WW_SmallGerstner": {
        "num_waves": 8,
        "seed": 17,
        "min_wavelength": 1200.0,
        "max_wavelength": 4500.0,
        "min_amplitude": 12.0,
        "max_amplitude": 30.0,
    },
    "WW_HighGerstner": {
        "num_waves": 8,
        "seed": 29,
        "min_wavelength": 1800.0,
        "max_wavelength": 8000.0,
        "min_amplitude": 25.0,
        "max_amplitude": 70.0,
    },
}

heights = {}
for name, values in PRESETS.items():
    path = f"/Game/Water/Waves/{name}"
    asset = unreal.EditorAssetLibrary.load_asset(path)
    source = unreal.load_object(None, f"{path}.{name}:WaterWaves")
    generator = unreal.load_object(None, f"{path}.{name}:WaterWaves.WaterWaves")
    assert asset is not None and source is not None and generator is not None, path
    for property_name, value in values.items():
        generator.set_editor_property(property_name, value)
        assert abs(generator.get_editor_property(property_name) - value) < 0.001
    source.set_editor_property("gerstner_wave_generator", None)
    source.set_editor_property("gerstner_wave_generator", generator)
    heights[name] = source.get_editor_property("max_wave_height")
    assert heights[name] > 0
    assert unreal.EditorAssetLibrary.save_loaded_asset(asset)
    print("BOAT_WAVE_CONFIGURED", name, heights[name])

assert heights["WW_HighGerstner"] > heights["WW_SmallGerstner"]

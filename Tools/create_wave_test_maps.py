import unreal


SOURCE = "/Game/Maps/M_WaterPhysicsTest"
NAMES = ("M_WaterSmallWavesTest", "M_WaterHighWavesTest")

assert unreal.EditorAssetLibrary.does_asset_exist(SOURCE)
for map_name in NAMES:
    destination = f"/Game/Maps/{map_name}"
    if not unreal.EditorAssetLibrary.does_asset_exist(destination):
        duplicate = unreal.EditorAssetLibrary.duplicate_asset(SOURCE, destination)
        assert duplicate is not None
        assert unreal.EditorAssetLibrary.save_loaded_asset(duplicate)
    print("BOAT_WAVE_MAP_DUPLICATED", destination)

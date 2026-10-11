import unreal


for name in (
    "BlueprintFactory",
    "DataAssetFactory",
    "DataAssetFactoryFactory",
    "WaterWavesAsset",
    "WaterWavesAssetFactory",
    "GerstnerWaterWaves",
    "GerstnerWaterWaveGeneratorSimple",
    "AssetToolsHelpers",
    "EditorAssetLibrary",
):
    cls = getattr(unreal, name, None)
    print("BOAT_API_CLASS", name, bool(cls))

for name in ("create_asset", "duplicate_asset"):
    method = getattr(unreal.AssetTools, name, None)
    print("BOAT_API_METHOD", name, (method.__doc__ or "")[:700] if method else "MISSING")

for name in ("set_editor_property", "get_editor_property"):
    method = getattr(unreal.Object, name, None)
    print("BOAT_API_OBJECT", name, bool(method))

print("BOAT_API_EXISTS", unreal.EditorAssetLibrary.does_asset_exist(
    "/Game/Boats/ThaiLongtail/Handling/BP_BoatHandlingData"))

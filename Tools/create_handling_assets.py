import unreal


FOLDER = "/Game/Boats/ThaiLongtail/Handling"
CLASS_PATH = f"{FOLDER}/BP_BoatHandlingData"
PROFILE_PATH = f"{FOLDER}/DA_ThaiLongtail_Handling"
VALUES = {
    "HullMassKg": 250.0,
    "EngineMassKg": 200.0,
    "HullCenterXcm": -20.0,
    "EngineCenterXcm": 230.0,
    "CenterZcm": -20.0,
    "FrontPontoonRadiusCm": 60.0,
    "RearPontoonRadiusCm": 53.0,
    "DriveForce": 220000.0,
    "LateralDrag": 1200.0,
    "QuadraticDrag": 0.055,
    "GovernorStartKmh": 105.0,
    "TargetForwardSpeedKmh": 110.0,
    "CruiseThrustScaleAtTarget": 0.7,
    "OverspeedFadeKmh": 6.0,
    "LaunchPitchTorque": 4000000.0,
    "LaunchPulseSeconds": 0.4,
    "VibrationStartKmh": 108.0,
}

assert not unreal.EditorAssetLibrary.does_asset_exist(CLASS_PATH), CLASS_PATH
assert not unreal.EditorAssetLibrary.does_asset_exist(PROFILE_PATH), PROFILE_PATH

assets = unreal.AssetToolsHelpers.get_asset_tools()
factory = unreal.BlueprintFactory()
factory.set_editor_property("parent_class", unreal.PrimaryDataAsset.static_class())
blueprint = assets.create_asset("BP_BoatHandlingData", FOLDER, unreal.Blueprint, factory)
assert blueprint is not None

real_type = unreal.BlueprintEditorLibrary.get_basic_type_by_name("real")
for name in VALUES:
    assert unreal.BlueprintEditorLibrary.add_member_variable(blueprint, name, real_type), name

unreal.BlueprintEditorLibrary.compile_blueprint(blueprint)
generated_class = blueprint.generated_class()
assert generated_class is not None
defaults = unreal.get_default_object(generated_class)
for name, value in VALUES.items():
    defaults.set_editor_property(name, value)
assert unreal.EditorAssetLibrary.save_loaded_asset(blueprint)

profile = assets.create_asset(
    "DA_ThaiLongtail_Handling", FOLDER, generated_class, unreal.DataAssetFactory()
)
assert profile is not None
for name, value in VALUES.items():
    profile.set_editor_property(name, value)
    assert abs(profile.get_editor_property(name) - value) < 0.001, name
assert unreal.EditorAssetLibrary.save_loaded_asset(profile)

print("BOAT_HANDLING_CREATED", blueprint.get_path_name(), profile.get_path_name())
for name in VALUES:
    print("BOAT_HANDLING_VALUE", name, profile.get_editor_property(name))

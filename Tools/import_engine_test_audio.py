"""Import the generated test-only WAVs as Unreal SoundWaves (skips ones already imported).

Run inside the editor: Cmd -> py <this file>. To swap in a real sound later, right-click the
SoundWave in the Content Browser -> Reimport With New File; every reference keeps working.
"""

from pathlib import Path
import unreal


SOURCE = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / "SourceAssets" / "Audio"
DESTINATION = "/Game/Boats/ThaiLongtail/Audio"
SOUNDS = (
    ("longtail_engine_test.wav", "SW_LongtailEngineTest", True),
    ("longtail_start_test.wav", "SW_LongtailStartTest", False),
    ("longtail_water_test.wav", "SW_LongtailWaterTest", True),
    ("longtail_hit_test.wav", "SW_LongtailHitTest", False),
    ("canal_ambience_test.wav", "SW_CanalAmbienceTest", True),
    ("longtail_exhaust_test.wav", "SW_LongtailExhaustTest", True),
    ("longtail_exhaust_pop_test.wav", "SW_LongtailExhaustPopTest", False),
    ("longtail_engine_idle_test.wav", "SW_LongtailEngineIdleTest", True),
    ("longtail_engine_low_test.wav", "SW_LongtailEngineLowTest", True),
    ("longtail_engine_mid_test.wav", "SW_LongtailEngineMidTest", True),
    ("longtail_engine_high_test.wav", "SW_LongtailEngineHighTest", True),
)


def main() -> None:
    tasks, fresh = [], []
    for filename, asset_name, looping in SOUNDS:
        if unreal.EditorAssetLibrary.does_asset_exist(f"{DESTINATION}/{asset_name}"):
            continue  # never overwrite: it may already be a real recording
        fresh.append((asset_name, looping))
        source_file = SOURCE / filename
        if not source_file.is_file():
            raise FileNotFoundError(source_file)
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(source_file))
        task.set_editor_property("destination_path", DESTINATION)
        task.set_editor_property("destination_name", asset_name)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        factory = unreal.SoundFactory()
        factory.set_editor_property("auto_create_cue", False)
        task.set_editor_property("factory", factory)
        tasks.append(task)

    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for asset_name, looping in fresh:
        asset_path = f"{DESTINATION}/{asset_name}"
        sound = unreal.load_asset(asset_path)
        if not isinstance(sound, unreal.SoundWave):
            raise RuntimeError(f"SoundWave import failed: {asset_path}")
        sound.set_editor_property("looping", looping)
        if not unreal.EditorAssetLibrary.save_loaded_asset(sound):
            raise RuntimeError(f"Could not save: {asset_path}")
        unreal.log(f"BOATLRACING_AUDIO_IMPORTED {asset_path} looping={looping}")


main()

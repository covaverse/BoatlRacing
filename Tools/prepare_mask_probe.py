"""Start SIE and capture the controlled probe once its world is ready."""
from pathlib import Path
import unreal

def capture_when_ready(delta):
    world = unreal.EditorLevelLibrary.get_game_world()
    if not world or 'UEDPIE' not in world.get_path_name():
        return
    boats = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Actor)
             if a.get_class().get_name() == 'BP_LongtailPhysicsPawn_C']
    if not boats:
        return
    unreal.unregister_slate_post_tick_callback(mask_probe_callback)
    exec((Path(unreal.Paths.project_dir()) / 'Tools/capture_mask_probe.py').read_text(), globals())

mask_probe_callback = unreal.register_slate_post_tick_callback(capture_when_ready)
unreal.EditorLevelLibrary.editor_play_simulate()

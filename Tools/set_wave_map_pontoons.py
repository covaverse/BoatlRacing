import re
import unreal


match = re.search(r"-BoatWavePreset=(Small|High)\b",
                  unreal.SystemLibrary.get_command_line())
assert match, "Pass -BoatWavePreset=Small or -BoatWavePreset=High"
preset = match.group(1)
map_path = f"/Game/Maps/M_Water{preset}WavesTest"

world = unreal.EditorLoadingAndSavingUtils.load_map(map_path)
assert world is not None
pawns = [actor for actor in unreal.EditorLevelLibrary.get_all_level_actors()
         if actor.get_class().get_name() == "BP_LongtailPhysicsPawn_C"]
assert len(pawns) == 1, (map_path, len(pawns))
pawn = pawns[0]
buoyancy = pawn.get_component_by_class(unreal.BuoyancyComponent)
assert buoyancy is not None
data = buoyancy.get_editor_property("buoyancy_data")
pontoons = list(data.get_editor_property("pontoons"))
assert len(pontoons) == 4
print("BOAT_PONTOONS_BEFORE", preset,
      [(p.relative_location.x, p.radius) for p in pontoons])
original_label = pawn.get_actor_label()
original_transform = pawn.get_actor_transform()
original_possession = pawn.get_editor_property("auto_possess_player")
assert original_possession == unreal.AutoReceiveInput.PLAYER0
replacement = unreal.EditorLevelLibrary.spawn_actor_from_class(
    pawn.get_class(), original_transform.translation,
    original_transform.rotation.rotator())
assert replacement is not None
replacement.set_actor_scale3d(original_transform.scale3d)
replacement.set_editor_property("auto_possess_player", original_possession)
new_buoyancy = replacement.get_component_by_class(unreal.BuoyancyComponent)
assert new_buoyancy is not None
actual = new_buoyancy.get_editor_property("buoyancy_data").get_editor_property("pontoons")
print("BOAT_PONTOONS_REPLACEMENT", preset,
      [(p.relative_location.x, p.radius) for p in actual])
assert [round(p.radius) for p in actual] == [60, 60, 55, 55]
assert replacement.get_actor_transform().translation == original_transform.translation
assert replacement.get_editor_property("auto_possess_player") == original_possession
if "-BoatApply=1" not in unreal.SystemLibrary.get_command_line():
    assert unreal.EditorLevelLibrary.destroy_actor(replacement)
    print("BOAT_PONTOONS_DRY_RUN", preset)
else:
    assert unreal.EditorLevelLibrary.destroy_actor(pawn)
    replacement.set_actor_label(original_label)
    assert unreal.EditorLoadingAndSavingUtils.save_map(world, map_path)
    print("BOAT_PONTOONS_SAVED", map_path)

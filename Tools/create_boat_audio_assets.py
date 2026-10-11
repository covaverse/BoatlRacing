"""Build the boat's engine MetaSounds and Sound Cues. Run inside the open editor (Python remote
execution). Existing assets are kept (the Pawn references them); delete one first to rebuild it.

Each engine MetaSound (a "sound profile") has six looping layers: 4 engine RPM bands, exhaust, water.
The Pawn sends per-layer <Layer>Gain (0-1) and <Layer>Pitch (semitones) every frame, assuming the band
loops are pitched to 1500 / 2400 / 3600 / 5600 RPM and the exhaust to 4300 RPM. Mix levels and the
wave per layer are MetaSound inputs, so loudness and sound choice are tuned in the MetaSound.
Swap profile = set the Pawn's EngineAudio component Sound to another MS_*.
"""
import unreal

DIR = "/Game/Boats/ThaiLongtail/Audio"
SRC = unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir()) + "SourceAssets/Audio/Real/"
PROFILES = {
    "MS_LongtailEngine": (("Idle", "SW_LongtailEngineIdleTest"), ("Low", "SW_LongtailEngineLowTest"),
                          ("Mid", "SW_LongtailEngineMidTest"), ("High", "SW_LongtailEngineHighTest"),
                          ("Exhaust", "SW_LongtailExhaustTest"), ("Water", "SW_LongtailWaterTest")),
    "MS_SportCarEngine": (("Idle", "SW_SportCarIdle"), ("Low", "SW_SportCarLow"),
                          ("Mid", "SW_SportCarMid"), ("High", "SW_SportCarHigh"),
                          ("Exhaust", "SW_SportCarExhaust"), ("Water", "SW_LongtailWaterTest")),
}
LAYER_LEVEL = {"Idle": "EngineLevel", "Low": "EngineLevel", "Mid": "EngineLevel", "High": "EngineLevel",
               "Exhaust": "ExhaustLevel", "Water": "WaterLevel"}
LEVELS = (("Master", 0.4), ("EngineLevel", 0.9), ("ExhaustLevel", 0.7), ("WaterLevel", 0.45))
# Loops imported from SourceAssets/Audio/Real when missing (pitched to the reference RPMs above).
IMPORTS = (("sport_maserati_idle_1500.wav", "SW_SportCarIdle"), ("sport_maserati_low_2400.wav", "SW_SportCarLow"),
           ("sport_maserati_mid_3600.wav", "SW_SportCarMid"), ("sport_maserati_high_5600.wav", "SW_SportCarHigh"),
           ("sport_ferrari_exhaust_4300.wav", "SW_SportCarExhaust"))
CUES = (("SC_LongtailStart", "SW_LongtailStartTest", 0.6),
        ("SC_LongtailExhaustPop", "SW_LongtailExhaustPopTest", 0.5),
        ("SC_LongtailHit", "SW_LongtailHitTest", 0.6),
        ("SC_CanalAmbience", "SW_CanalAmbienceTest", 1.0))

bs = unreal.get_engine_subsystem(unreal.MetaSoundBuilderSubsystem)
lib = unreal.EditorAssetLibrary


def ok(result, what):
    assert "SUCCEEDED" in str(result), f"{what}: {result}"


def first(r):
    return r[0] if isinstance(r, tuple) else r


def import_loops():
    tasks, fresh = [], []
    for src, name in IMPORTS:
        if lib.does_asset_exist(f"{DIR}/{name}"):
            continue
        t = unreal.AssetImportTask()
        t.set_editor_property("filename", SRC + src)
        t.set_editor_property("destination_path", DIR)
        t.set_editor_property("destination_name", name)
        t.set_editor_property("automated", True)
        f = unreal.SoundFactory()
        f.set_editor_property("auto_create_cue", False)
        t.set_editor_property("factory", f)
        tasks.append(t)
        fresh.append(name)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks(tasks)
    for name in fresh:
        s = unreal.load_asset(f"{DIR}/{name}")
        s.set_editor_property("looping", True)
        s.set_editor_property("virtualization_mode", unreal.VirtualizationMode.PLAY_WHEN_SILENT)
        assert lib.save_asset(f"{DIR}/{name}", only_if_is_dirty=False)
        print("BOAT_AUDIO_IMPORTED", name, round(s.get_editor_property("duration"), 2))


def build_engine(asset_name, layers):
    path = f"{DIR}/{asset_name}"
    if lib.does_asset_exist(path):
        print("BOAT_AUDIO_KEPT", path)
        return
    created = bs.create_source_builder(asset_name + "Builder", unreal.MetaSoundOutputAudioFormat.STEREO, False)
    builder, on_play, audio_outs = created[0], created[1], created[3]

    def node(name, variant):
        cn = unreal.MetasoundFrontendClassName()
        cn.namespace, cn.name, cn.variant = "UE", name, variant
        handle, result = builder.add_node_by_class_name(cn)
        ok(result, f"add {name}")
        return handle

    def pin_in(n, name):
        handle, result = builder.find_node_input_by_name(n, name)
        ok(result, f"input {name}")
        return handle

    def pin_out(n, name):
        handle, result = builder.find_node_output_by_name(n, name)
        ok(result, f"output {name}")
        return handle

    def link(o, i, what):
        ok(builder.connect_nodes(o, i), f"connect {what}")

    def graph_input(name, data_type, literal):
        handle, result = builder.add_graph_input_node(name, data_type, literal, False)
        ok(result, f"graph input {name}")
        return handle

    def multiply_float(a, b, what):
        m = node("Multiply", "Float")
        link(a, pin_in(m, "PrimaryOperand"), what)
        link(b, pin_in(m, "AdditionalOperands"), what)
        return pin_out(m, "Out")

    levels = {n: graph_input(n, "Float", first(bs.create_float_meta_sound_literal(v))) for n, v in LEVELS}
    level_gain = {lvl: multiply_float(levels[lvl], levels["Master"], f"{lvl}*Master")
                  for lvl in ("EngineLevel", "ExhaustLevel", "WaterLevel")}
    true_lit = first(bs.create_bool_meta_sound_literal(True))
    sums = {"Left": None, "Right": None}
    for layer, wave_name in layers:
        wave = unreal.load_asset(f"{DIR}/{wave_name}")
        assert wave, wave_name
        wave_in = graph_input(f"{layer}Wave", "WaveAsset", first(bs.create_object_meta_sound_literal(wave)))
        gain_in = graph_input(f"{layer}Gain", "Float", first(bs.create_float_meta_sound_literal(0.0)))
        pitch_in = graph_input(f"{layer}Pitch", "Float", first(bs.create_float_meta_sound_literal(0.0)))
        player = node("Wave Player", "Stereo")
        link(on_play, pin_in(player, "Play"), f"{layer} play")
        link(wave_in, pin_in(player, "Wave Asset"), f"{layer} wave")
        link(pitch_in, pin_in(player, "Pitch Shift"), f"{layer} pitch")
        ok(builder.set_node_input_default(pin_in(player, "Loop"), true_lit), f"{layer} loop")
        gain = multiply_float(gain_in, level_gain[LAYER_LEVEL[layer]], f"{layer} gain")
        for side in ("Left", "Right"):
            scaled = node("Multiply", "Audio by Float")
            link(pin_out(player, f"Out {side}"), pin_in(scaled, "PrimaryOperand"), f"{layer} {side}")
            link(gain, pin_in(scaled, "AdditionalOperands"), f"{layer} {side} gain")
            out = pin_out(scaled, "Out")
            if sums[side] is None:
                sums[side] = out
            else:
                add = node("Add", "Audio")
                link(sums[side], pin_in(add, "PrimaryOperand"), f"sum {side}")
                link(out, pin_in(add, "AdditionalOperands"), f"sum {side}")
                sums[side] = pin_out(add, "Out")
    link(sums["Left"], audio_outs[0], "out left")
    link(sums["Right"], audio_outs[1], "out right")
    ed = unreal.get_editor_subsystem(unreal.MetaSoundEditorSubsystem)
    asset = first(ed.build_to_asset(builder, "BoatlRacing", asset_name, DIR))
    assert asset, asset_name
    assert lib.save_asset(path, only_if_is_dirty=False)
    print("BOAT_AUDIO_METASOUND", path)


def build_cues():
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    for cue_name, wave_name, volume in CUES:
        cue_path = f"{DIR}/{cue_name}"
        if lib.does_asset_exist(cue_path):
            print("BOAT_AUDIO_KEPT", cue_path)
            continue
        factory = unreal.SoundCueFactoryNew()
        factory.set_editor_property("initial_sound_waves", [unreal.load_asset(f"{DIR}/{wave_name}")])
        cue = tools.create_asset(cue_name, DIR, unreal.SoundCue, factory)
        cue.set_editor_property("volume_multiplier", volume)
        assert lib.save_asset(cue_path, only_if_is_dirty=False)
        print("BOAT_AUDIO_CUE", cue_path, volume)


import_loops()
for name, layers in PROFILES.items():
    build_engine(name, layers)
build_cues()

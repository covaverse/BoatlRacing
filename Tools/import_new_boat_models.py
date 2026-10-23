import hashlib
import json
import struct
from pathlib import Path

import unreal


project = Path(unreal.Paths.project_dir())
source = project.parent / "Model" / "Blender"
entries = [
    ("ThaiLongtailRefine03", "ThaiLongtailBoat_Refine03_20261011/exports/VH_ThaiLongtailBoat_LOD0.glb", "/Game/Boats/Modular/ThaiLongtailRefine03"),
    ("Racing150cc", "RacingEngine150cc_20261004_GameOptimized/exports/PR_RacingEngine150cc_Static_LOD0.glb", "/Game/Engines/Racing150cc"),
    ("Thai150cc", "Thai150cc_GameOptimized/exports/SM_Thai150_Game_Runtime.glb", "/Game/Engines/Thai150cc"),
    ("River125cc", "ThaiRiverRacer125cc_20261003/exports/PR_ThaiRiverRacer125cc_Game_LOD0.glb", "/Game/Engines/River125cc"),
]
editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
assert not editor.get_game_world(), "Stop PIE before importing models"
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
records = []
for label, relative, destination in entries:
    filename = source / relative
    assert filename.is_file(), filename
    raw = filename.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", raw)
    assert magic == b"glTF" and version == 2 and length == len(raw), filename
    json_length, chunk_type = struct.unpack_from("<II", raw, 12)
    assert chunk_type == 0x4E4F534A
    gltf = json.loads(raw[20:20 + json_length])
    assert "KHR_draco_mesh_compression" not in gltf.get("extensionsRequired", []), "Draco requires a separate importer"
    record = {"label": label, "source": str(filename), "sha256": hashlib.sha256(raw).hexdigest(),
              "destination": destination, "source_meshes": len(gltf.get("meshes", [])), "source_nodes": gltf.get("nodes", [])}
    previous = unreal.EditorAssetLibrary.list_assets(destination, recursive=True) if unreal.EditorAssetLibrary.does_directory_exist(destination) else []
    if not previous:
        task = unreal.AssetImportTask()
        task.set_editor_property("filename", str(filename))
        task.set_editor_property("destination_path", destination)
        task.set_editor_property("automated", True)
        task.set_editor_property("replace_existing", False)
        task.set_editor_property("save", True)
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    paths = unreal.EditorAssetLibrary.list_assets(destination, recursive=True)
    meshes = []
    materials = []
    textures = []
    for path in paths:
        asset = unreal.load_asset(path)
        if isinstance(asset, unreal.StaticMesh):
            bounds = asset.get_bounds()
            extent = [bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z]
            assert any(value > 0 for value in extent), path
            try:
                material_slots = [slot.get_editor_property("material_interface").get_path_name()
                                  for slot in asset.get_editor_property("static_materials")
                                  if slot.get_editor_property("material_interface")]
            except Exception:
                material_slots = []
            meshes.append({"path": path, "extent_cm": extent, "materials": material_slots})
        elif isinstance(asset, unreal.MaterialInterface):
            materials.append(path)
        elif isinstance(asset, unreal.Texture):
            textures.append(path)
    assert meshes, "No imported meshes at " + destination
    record.update({"meshes": meshes, "materials": materials, "textures": textures, "status": "existing" if previous else "imported"})
    records.append(record)
    print("NEW_MODEL_IMPORTED", label, "meshes", len(meshes), "materials", len(materials), "textures", len(textures))
report = project / "Docs" / "Work" / "new-model-imports-2026-10-15.json"
report.parent.mkdir(parents=True, exist_ok=True)
report.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
print("NEW_MODELS_READY", str(report))

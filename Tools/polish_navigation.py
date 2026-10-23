import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint


assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
folder = "/Game/UI/Prototype/Fonts"
factory = unreal.FontFileImportFactory()
factory.set_editor_property("batch_create_font_asset", unreal.BatchCreateFontAsset.CREATE_IF_NO_FONT_EXISTS)
task = unreal.AssetImportTask()
task.set_editor_property("filename", unreal.Paths.engine_content_dir() + "Slate/Fonts/NotoSansThai-Regular.ttf")
task.set_editor_property("destination_path", folder)
task.set_editor_property("destination_name", "NotoSansThai")
task.set_editor_property("factory", factory)
task.set_editor_property("automated", True)
task.set_editor_property("save", True)
task.set_editor_property("replace_existing", False)
if not unreal.EditorAssetLibrary.does_asset_exist(folder + "/NotoSansThai"):
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
fonts = [unreal.load_asset(path) for path in unreal.EditorAssetLibrary.list_assets(folder)]
font = next((asset for asset in fonts if isinstance(asset, unreal.Font)), None)
assert font, [str(asset) for asset in fonts]
latin = unreal.load_asset("/Engine/EngineFonts/Roboto")
assert latin
labels = {
    "BuildLabel": "ทดสอบเมนู",
    "BtnHomeText": "เมนูหลัก",
    "BtnGarageText": "โรงรถ",
    "BtnMapsText": "เลือกสนาม",
    "BtnSettingsText": "ตั้งค่า",
    "BtnStartText": "เริ่มขับในคลอง",
    "BtnCanalText": "คลอง",
    "BtnCalmText": "น้ำนิ่ง",
    "BtnSmallText": "คลื่นเล็ก",
    "BtnHighText": "คลื่นสูง",
    "BtnBackText": "กลับ",
    "Heading0": "พร้อมทดสอบ",
    "Heading1": "เลือกสนาม",
    "Heading2": "ตั้งค่า (ตัวอย่าง)",
    "Welcome": "กดโรงรถเพื่อดูเรือ หรือเลือกสนามเพื่อเริ่มขับ\nปุ่มชุดนี้ใช้ทดสอบการเปลี่ยนหน้า ยังไม่ใช่ระบบแต่งเครื่องขั้นสุดท้าย",
    "SettingsHelp": "หน้าตั้งค่าสำหรับตรวจรูปแบบ\nการปรับเสียงและขนาดมาตรวัดจะเชื่อมในขั้นถัดไป",
    "DriveHelp": "W/S DRIVE  A/D STEER\nQ/E TRIM  SPACE CLUTCH\nSHIFT+F1 RELEASE MOUSE",
}
for name in ("WBP_TestMenu", "WBP_TestDriveNavigation"):
    path = "/Game/UI/Prototype/" + name
    widget = unreal.load_asset(path)
    canvas = unreal.load_object(None, path + "." + name + ":WidgetTree.RootCanvas")
    queue = [canvas]
    while queue:
        current = queue.pop()
        if isinstance(current, unreal.TextBlock):
            if current.get_name() in labels:
                current.set_text(labels[current.get_name()])
            info = current.get_editor_property("font")
            info.set_editor_property("font_object", latin if current.get_name() in ("Logo", "DriveHelp") else font)
            current.set_editor_property("font", info)
            current.set_auto_wrap_text(True)
        if isinstance(current, unreal.PanelWidget):
            queue.extend(current.get_all_children())
    if name == "WBP_TestMenu":
        switcher = unreal.load_object(None, path + "." + name + ":WidgetTree.PageSwitcher")
        switcher.slot.set_size(unreal.Vector2D(680, 460))
    Blueprint.compile_blueprint(widget, warnings_as_errors=True)
    unreal.EditorAssetLibrary.save_loaded_asset(widget, only_if_is_dirty=False)
print("NAVIGATION_THAI_FONT_READY", font.get_path_name())

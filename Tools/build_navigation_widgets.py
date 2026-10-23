import json

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint
from editor_toolset.toolsets.object import ObjectTools


assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
BASE = "/Game/UI/Prototype"


def edit(widget, values):
    schema = json.loads(ObjectTools.list_properties(widget))
    assert all(name in schema for name in values), (widget.get_name(), list(values), list(schema))
    ObjectTools.get_properties(widget, list(values))
    assert ObjectTools.set_properties(widget, json.dumps(values)), widget.get_name()


def make(tree, widget_class, name):
    return unreal.new_object(widget_class, outer=tree, name=name)


def position(canvas, widget, x, y, width, height, right=False, bottom=False):
    slot = canvas.add_child_to_canvas(widget)
    anchor = unreal.Vector2D(1 if right else 0, 1 if bottom else 0)
    slot.set_anchors(unreal.Anchors(minimum=anchor, maximum=anchor))
    slot.set_alignment(unreal.Vector2D(1 if right else 0, 1 if bottom else 0))
    slot.set_position(unreal.Vector2D(x, y))
    slot.set_size(unreal.Vector2D(width, height))


def text(tree, name, label, size=20, yellow=False):
    widget = make(tree, unreal.TextBlock, name)
    edit(widget, {"text": label})
    font = widget.get_editor_property("font")
    font.set_editor_property("size", size)
    widget.set_editor_property("font", font)
    widget.set_color_and_opacity(unreal.SlateColor(specified_color=unreal.LinearColor(1, 0.65, 0.05, 1) if yellow else unreal.LinearColor(1, 1, 1, 1)))
    return widget


def button(tree, parent, name, label):
    widget = make(tree, unreal.Button, name)
    widget.set_background_color(unreal.LinearColor(0.05, 0.065, 0.08, 0.95))
    box = make(tree, unreal.SizeBox, name + "Size")
    box.set_height_override(52)
    caption = text(tree, name + "Text", label, 19)
    box.add_child(caption)
    widget.add_child(box)
    slot = parent.add_child_to_vertical_box(widget)
    slot.set_padding(unreal.Margin(0, 4, 0, 4))
    return widget


def create(name):
    existing = unreal.load_asset(BASE + "/" + name)
    if existing:
        return existing
    factory = unreal.WidgetBlueprintFactory()
    factory.set_editor_property("parent_class", unreal.UserWidget)
    return unreal.AssetToolsHelpers.get_asset_tools().create_asset(name, BASE, unreal.WidgetBlueprint, factory)


def build(name, driving=False):
    widget = create(name)
    canvas = unreal.load_object(None, BASE + "/" + name + "." + name + ":WidgetTree.RootCanvas")
    assert canvas, "Create RootCanvas with UMGToolSet.AddWidget before running"
    canvas.clear_children()
    tree = canvas.get_outer()
    panel = make(tree, unreal.Border, "SidebarBackground")
    panel.set_brush_color(unreal.LinearColor(0.012, 0.018, 0.03, 0.92))
    panel.set_padding(unreal.Margin(22))
    sidebar = make(tree, unreal.VerticalBox, "Sidebar")
    panel.add_child(sidebar)
    sidebar.add_child(text(tree, "Logo", "THAI SPEED BOAT", 26, True))
    sidebar.add_child(text(tree, "BuildLabel", "NAVIGATION TEST / ทดสอบเมนู", 14))
    button(tree, sidebar, "BtnHome", "HOME / เมนูหลัก")
    button(tree, sidebar, "BtnGarage", "GARAGE / โรงรถ")
    if not driving:
        button(tree, sidebar, "BtnMaps", "FREE DRIVE / เลือกสนาม")
        button(tree, sidebar, "BtnSettings", "SETTINGS / ตั้งค่า")
        button(tree, sidebar, "BtnStart", "START / ขับในคลอง")
    else:
        sidebar.add_child(text(tree, "DriveHelp", "W/S ขับ  A/D เลี้ยว\nQ/E trim  Space คลัตช์\nShift+F1 ปล่อยเมาส์", 14))
    position(canvas, panel, 30, 30, 330, 470 if not driving else 260)
    if not driving:
        switcher = make(tree, unreal.WidgetSwitcher, "PageSwitcher")
        position(canvas, switcher, -35, -35, 680, 250, True, True)
        for page_index, heading in enumerate(("READY TO DRIVE / พร้อมทดสอบ", "SELECT WATER / เลือกสนาม", "SETTINGS PREVIEW / หน้าตั้งค่า")):
            background = make(tree, unreal.Border, "PageBackground" + str(page_index))
            background.set_brush_color(unreal.LinearColor(0.012, 0.018, 0.03, 0.92))
            background.set_padding(unreal.Margin(22))
            body = make(tree, unreal.VerticalBox, "PageBody" + str(page_index))
            background.add_child(body)
            body.add_child(text(tree, "Heading" + str(page_index), heading, 24, True))
            if page_index == 0:
                body.add_child(text(tree, "Welcome", "กด GARAGE เพื่อดูเรือ หรือ FREE DRIVE เพื่อเลือกสนาม\nปุ่มชุดนี้ใช้ทดสอบการเปลี่ยนหน้า ยังไม่ใช่ระบบแต่งเครื่องขั้นสุดท้าย", 18))
            elif page_index == 1:
                for suffix, label in (("Canal", "CANAL / คลอง"), ("Calm", "CALM / น้ำนิ่ง"), ("Small", "SMALL WAVES / คลื่นเล็ก"), ("High", "HIGH WAVES / คลื่นสูง")):
                    button(tree, body, "Btn" + suffix, label)
            else:
                body.add_child(text(tree, "SettingsHelp", "หน้าตั้งค่าสำหรับตรวจ layout\nการปรับเสียงและขนาด HUD จะเชื่อมระบบเต็มในขั้นถัดไป", 18))
                button(tree, body, "BtnBack", "BACK / กลับหน้าแรก")
            switcher.add_child(background)
    Blueprint.compile_blueprint(widget)
    assert unreal.EditorAssetLibrary.save_loaded_asset(widget, only_if_is_dirty=False)
    print("NAV_WIDGET_LAYOUT_READY", name)


build("WBP_TestMenu")
build("WBP_TestDriveNavigation", True)

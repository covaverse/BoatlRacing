"""Main menu built from Content/Boats/UI_REF.png.

The reference image is the full-screen background; every interactive element is a crop of that image
placed back at the same pixel rect, with hover/pressed variants made by
SourceAssets/UI/MainMenu/make_buttons.ps1. Pop-up panels (race picker, profile, wallet, notifications,
mail, settings) use the shared theme in Tools/ui_theme.py (textures from SourceAssets/UI/Theme/make_theme.ps1).

Run from a live editor (PIE stopped), after both PowerShell scripts:
  python Tools/run_editor_script.py Tools/mainmenu_build.py
"""
import importlib
import json
import sys
from pathlib import Path

import unreal
from editor_toolset.toolsets.blueprint import BlueprintTools as Blueprint

sys.path.insert(0, str(Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_dir())) / "Tools"))
import ui_theme
importlib.reload(ui_theme)
from ui_theme import GOLD, MUTED, WHITE, DIM, add

SOURCE = ui_theme.ROOT / "SourceAssets/UI/MainMenu"
TEXTURES = "/Game/UI/MainMenu/Textures"
WIDGET = "/Game/UI/MainMenu/WBP_MainMenu"
TEMPLATE = "/Game/UI/Prototype/WBP_TestMenu"
GARAGE_MAP = "/Game/Maps/M_Garage"
MAPS = [("BtnMapCanal", "คลอง  CANAL", "/Game/Maps/M_CanalBlockout"),
        ("BtnMapCalm", "น้ำนิ่ง  CALM WATER", "/Game/Maps/M_WaterPhysicsTest"),
        ("BtnMapSmall", "คลื่นเล็ก  SMALL WAVES", "/Game/Maps/M_WaterSmallWavesTest"),
        ("BtnMapHigh", "คลื่นสูง  HIGH WAVES", "/Game/Maps/M_WaterHighWavesTest")]
PANELS = ["RaceOverlay", "ProfileOverlay", "WalletOverlay", "NoticeOverlay", "MailOverlay", "SettingsOverlay"]
# What each cropped button does: ("open", map) | ("panel", overlay) | ("profile",) | ("close",) | ("soon", feature)
ACTIONS = {
    "NavHome": ("close",), "NavGarage": ("open", GARAGE_MAP), "NavRace": ("panel", "RaceOverlay"), "NavCareer": ("soon", "CAREER"),
    "NavMultiplayer": ("soon", "MULTIPLAYER"), "NavCustomize": ("open", GARAGE_MAP), "NavShop": ("soon", "SHOP"),
    "NavSettings": ("panel", "SettingsOverlay"), "CardRace": ("panel", "RaceOverlay"), "CardGarage": ("open", GARAGE_MAP),
    "CardCareer": ("soon", "CAREER"), "CardMultiplayer": ("soon", "MULTIPLAYER"), "BarEvent": ("soon", "EVENT"),
    "BarLeaderboard": ("soon", "LEADERBOARD"), "BarChallenge": ("soon", "CHALLENGE"), "BarStore": ("soon", "STORE"),
    "News": ("soon", "NEWS"), "SeasonEvent": ("panel", "RaceOverlay"),
    "TopProfile": ("profile",), "TopCoins": ("panel", "WalletOverlay"), "TopGems": ("panel", "WalletOverlay"),
    "TopBell": ("panel", "NoticeOverlay"), "TopMail": ("panel", "MailOverlay"), "TopSettings": ("panel", "SettingsOverlay"),
}
# The account bar is mock data baked into the reference image; the panels repeat the same values.
PLAYER = {"name": "BoatRacerTH", "level": "Lv. 32  ·  นักแข่งคลอง", "xp": 0.62, "xp_text": "XP 6,200 / 10,000",
          "coins": "256,420", "gems": "3,680"}
NOTICES = [("ฤดูกาลใหม่ King of the Canals เปิดแล้ว", "ลงแข่งในคลองเพื่อชิงตำแหน่งเจ้าคลอง", "วันนี้"),
           ("เครื่อง Racing 150cc พร้อมใช้งาน", "เปลี่ยนเครื่องได้ที่โชว์รูมเรือ", "เมื่อวาน"),
           ("สนามคลองทดสอบอัปเดต", "คลองยาว 1.85 กม. มีสะพาน 2 แห่ง", "2 วันก่อน")]
MAILS = [("รางวัลต้อนรับนักแข่งใหม่", "5,000 เหรียญ + 50 เพชร", "ทีมงาน"),
         ("ขอบคุณที่ร่วมทดสอบ", "ส่งความเห็นได้ทุกเมื่อ", "ทีมพัฒนา")]
QUALITY = [("BtnQualityLow", "ต่ำ", 0), ("BtnQualityMid", "กลาง", 1), ("BtnQualityHigh", "สูง", 2), ("BtnQualityEpic", "สูงสุด", 3)]

assert not unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world(), "Stop PIE first"
layout = json.loads((SOURCE / "layout.json").read_text(encoding="utf-8"))

# ---------------------------------------------------------------- textures
files = sorted((SOURCE / "Textures").glob("*.png"))
assert len(files) == 1 + 3 * len(layout["buttons"]) + len(layout["crops"]), "Run SourceAssets/UI/MainMenu/make_buttons.ps1 first"
textures = ui_theme.import_textures(files, TEXTURES)
textures.update(ui_theme.theme_textures())
print("MAINMENU_TEXTURES", len(textures))

# ---------------------------------------------------------------- layout
if not unreal.EditorAssetLibrary.does_asset_exist(WIDGET):
    assert unreal.EditorAssetLibrary.duplicate_asset(TEMPLATE, WIDGET)
widget_bp = unreal.load_asset(WIDGET)
ui = ui_theme.Builder(widget_bp, textures)
canvas = ui.root_canvas(WIDGET)
width_px, height_px = layout["size"]


def place(parent, child, x, y, w, h):
    slot = parent.add_child_to_canvas(child)
    slot.set_position(unreal.Vector2D(x, y))
    slot.set_size(unreal.Vector2D(w, h))
    return slot


def crop_button(name, rect):
    x, y, w, h = rect
    button = ui.make(unreal.Button, "Btn" + name)
    style = button.get_editor_property("widget_style")
    for key, suffix in (("normal", ""), ("hovered", "_Hover"), ("pressed", "_Pressed")):
        style.set_editor_property(key, ui_theme.image_brush(textures[f"T_MM_{name}{suffix}"], (w, h)))
    for key in ("normal_padding", "pressed_padding"):
        style.set_editor_property(key, unreal.Margin(0, 0, 0, 0))
    button.set_style(style)
    place(stage, button, x, y, w, h)


def overlay(name, width, tag, title, body_builder, buttons):
    """Full-screen layer: a dim button that closes the panel when clicked outside the card, and the centred
    themed card on top (tag, title, custom body, then a row of buttons)."""
    layer = ui.variable(ui.make(unreal.Overlay, name))
    layer.set_visibility(unreal.SlateVisibility.COLLAPSED)
    dim = ui.make(unreal.Button, "Btn" + name + "Dim")
    style = dim.get_editor_property("widget_style")
    for key in ("normal", "hovered", "pressed"):
        brush = unreal.SlateBrush()
        brush.set_editor_property("tint_color", unreal.SlateColor(specified_color=DIM))
        style.set_editor_property(key, brush)
    dim.set_style(style)
    slot = layer.add_child_to_overlay(dim)
    slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_FILL)
    slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_FILL)
    size = ui.make(unreal.SizeBox, name + "Width")
    size.set_width_override(width)
    card = ui.panel(name + "Card")
    column = ui.make(unreal.VerticalBox, name + "Column")
    tag_row = ui.make(unreal.HorizontalBox, name + "TagRow")
    add(tag_row, ui.tag(name + "Tag", tag), 0, 0)
    add(column, tag_row, 0, 6)
    add(column, ui.text(name + "Title", title, 30, WHITE), 2, 4)
    add(column, ui.divider(name + "Line"), 4, 12)
    body_builder(column)
    row = ui.make(unreal.HorizontalBox, name + "Buttons")
    for index, (button, label) in enumerate(buttons):
        add(row, ui.button(button, label, size=18), 0 if index == 0 else 10, 0, fill=True)
    add(column, row, 18, 0)
    card.add_child(column)
    size.add_child(card)
    slot = layer.add_child_to_overlay(size)
    slot.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
    slot.set_vertical_alignment(unreal.VerticalAlignment.V_ALIGN_CENTER)
    place(stage, layer, 0, 0, width_px, height_px)


def info_row(column, name, title, detail, note=""):
    row = ui.make(unreal.HorizontalBox, name)
    left = ui.make(unreal.VerticalBox, name + "Left")
    add(left, ui.text(name + "Title", title, 19, WHITE), 0, 0)
    add(left, ui.text(name + "Detail", detail, 15, MUTED), 0, 0)
    add(row, left, 0, 0, fill=True)
    if note:
        add(row, ui.text(name + "Note", note, 14, GOLD, wrap=False), 12, 0)
    add(column, row, 6, 6)


fit = ui.make(unreal.ScaleBox, "Fit")
# Fit, not fill: on non-16:9 screens the menu letterboxes instead of cutting off edge buttons.
fit.set_editor_property("stretch", unreal.Stretch.SCALE_TO_FIT)
slot = canvas.add_child_to_canvas(fit)
slot.set_anchors(unreal.Anchors(minimum=unreal.Vector2D(0, 0), maximum=unreal.Vector2D(1, 1)))
slot.set_offsets(unreal.Margin(0, 0, 0, 0))
frame = ui.make(unreal.SizeBox, "Frame")
frame.set_width_override(width_px)
frame.set_height_override(height_px)
fit.add_child(frame)
stage = ui.make(unreal.CanvasPanel, "Stage")
frame.add_child(stage)
place(stage, ui.image("Background", textures["T_MainMenu_BG"], (width_px, height_px)), 0, 0, width_px, height_px)
for button_name, rect in layout["buttons"].items():
    crop_button(button_name, rect)


def race_body(column):
    add(column, ui.text("TxtRaceHint", "เลือกน้ำที่จะลงแข่ง  ·  ใช้เรือและเครื่องยนต์ตามที่ตั้งไว้ในโชว์รูม", 15, MUTED), 0, 8)
    for name, label, _ in MAPS:
        add(column, ui.button(name, label, height=52, size=20), 5, 5)


def profile_body(column):
    head = ui.make(unreal.HorizontalBox, "ProfileHead")
    avatar = ui.make(unreal.SizeBox, "ProfileAvatarSize")
    avatar.set_width_override(92)
    avatar.set_height_override(92)
    avatar.add_child(ui.image("ProfileAvatar", textures["T_MM_CropAvatar"], (92, 92)))
    add(head, avatar, 0, 18)
    who = ui.make(unreal.VerticalBox, "ProfileWho")
    add(who, ui.text("TxtProfileName", PLAYER["name"], 28, WHITE, wrap=False), 0, 0)
    add(who, ui.text("TxtProfileLevel", PLAYER["level"], 16, GOLD, wrap=False), 0, 6)
    add(who, ui.bar("ProfileXP", PLAYER["xp"]), 2, 2)
    add(who, ui.text("TxtProfileXP", PLAYER["xp_text"], 13, MUTED, wrap=False), 0, 0)
    add(head, who, 0, 0, fill=True)
    add(column, head, 0, 10)
    for name, title in (("ProfileBoat", "เรือที่ใช้"), ("ProfileEngine", "เครื่องยนต์")):
        row = ui.make(unreal.HorizontalBox, name + "Row")
        add(row, ui.text(name + "Label", title, 16, MUTED, wrap=False), 0, 0, fill=True)
        add(row, ui.variable(ui.text("Txt" + name, "-", 19, WHITE, wrap=False)), 12, 0)
        add(column, row, 5, 5)
    info_row(column, "ProfileFavourite", "สนามโปรด", "คลองทดสอบ 1.85 กม.", "CANAL")


def wallet_body(column):
    for name, icon, amount, unit, note in (("WalletCoins", "T_MM_CropIconCoin", PLAYER["coins"], "เหรียญ", "ใช้ซื้อชิ้นส่วนและเครื่องยนต์"),
                                           ("WalletGems", "T_MM_CropIconGem", PLAYER["gems"], "เพชร", "ใช้ปลดล็อกลายเรือพิเศษ")):
        row = ui.make(unreal.HorizontalBox, name)
        add(row, ui.image(name + "Icon", textures[icon], (40, 40)), 0, 14)
        left = ui.make(unreal.VerticalBox, name + "Text")
        add(left, ui.text(name + "Amount", f"{amount}  {unit}", 24, WHITE, wrap=False), 0, 0)
        add(left, ui.text(name + "Note", note, 14, MUTED), 0, 0)
        add(row, left, 0, 0, fill=True)
        add(column, row, 6, 6)
    add(column, ui.text("TxtWalletHint", "ร้านค้าและการเติมเงินจะเปิดในเวอร์ชันถัดไป", 14, GOLD), 8, 0)


def notice_body(column):
    for index, (title, detail, when) in enumerate(NOTICES):
        info_row(column, f"Notice{index}", title, detail, when)


def mail_body(column):
    for index, (title, detail, sender) in enumerate(MAILS):
        info_row(column, f"Mail{index}", title, detail, sender)


def settings_body(column):
    add(column, ui.text("TxtSetQuality", "คุณภาพกราฟิก", 16, GOLD), 0, 4)
    row = ui.make(unreal.HorizontalBox, "QualityRow")
    for index, (name, label, _) in enumerate(QUALITY):
        add(row, ui.button(name, label, height=44, size=17), 0 if index == 0 else 8, 0, fill=True)
    add(column, row, 0, 12)
    add(column, ui.text("TxtSetDisplay", "การแสดงผล", 16, GOLD), 0, 4)
    row = ui.make(unreal.HorizontalBox, "DisplayRow")
    for index, (name, label) in enumerate((("BtnWindowed", "หน้าต่าง"), ("BtnFullscreen", "เต็มจอ"), ("BtnShowFps", "แสดง FPS"))):
        add(row, ui.button(name, label, height=44, size=16), 0 if index == 0 else 8, 0, fill=True)
    add(column, row, 0, 4)


overlay("RaceOverlay", 520, "SELECT WATER", "เลือกสนาม", race_body, [("BtnRaceClose", "กลับ")])
overlay("ProfileOverlay", 560, "PROFILE", "โปรไฟล์นักแข่ง", profile_body, [("BtnProfileGarage", "ไปโชว์รูม"), ("BtnProfileClose", "ปิด")])
overlay("WalletOverlay", 520, "WALLET", "กระเป๋าเงิน", wallet_body, [("BtnWalletStore", "ไปร้านค้า"), ("BtnWalletClose", "ปิด")])
overlay("NoticeOverlay", 600, "NOTIFICATIONS  3", "การแจ้งเตือน", notice_body, [("BtnNoticeEvent", "ไปที่อีเวนต์"), ("BtnNoticeClose", "ปิด")])
overlay("MailOverlay", 560, "MAIL", "กล่องจดหมาย", mail_body, [("BtnMailClaim", "รับทั้งหมด"), ("BtnMailClose", "ปิด")])
overlay("SettingsOverlay", 620, "SETTINGS", "ตั้งค่า", settings_body, [("BtnSettingsClose", "ปิด")])

toast = ui.variable(ui.panel("Toast", (26, 12, 26, 12)))
toast.set_horizontal_alignment(unreal.HorizontalAlignment.H_ALIGN_CENTER)
toast.set_visibility(unreal.SlateVisibility.COLLAPSED)
toast.add_child(ui.variable(ui.text("TxtToast", "-", 20, GOLD, center=True, wrap=False)))
# Just above the bottom bar so it never covers an open panel.
place(stage, toast, width_px / 2 - 280, 735, 560, 58)

ui.expose_variables()
Blueprint.compile_blueprint(widget_bp)
unreal.EditorAssetLibrary.save_loaded_asset(widget_bp, only_if_is_dirty=False)
print("MAINMENU_LAYOUT_READY")

# ---------------------------------------------------------------- graph
ui_theme.clear_event_graph(widget_bp)
# Function graphs hold typed getters of the widgets rebuilt above; recreate all of them so types match.
for stale in [graph.get_name() for graph in Blueprint.list_graphs(widget_bp)]:
    if stale != "EventGraph":
        Blueprint.remove_function_graph(widget_bp, stale)
Blueprint.compile_blueprint(widget_bp)
if "ToastUntil" not in [str(v) for v in Blueprint.list_variables(widget_bp)]:
    Blueprint.add_variable(widget_bp, "ToastUntil", "float")
var = lambda name: f"(Variables|WBP_MainMenu|Get{name})"
hide_all = "\n  ".join(f'(Widget|SetVisibility :self {var(p)} :InVisibility "Collapsed")' for p in PANELS)

ui_theme.write(ui_theme.function(widget_bp, "ShowToast", [("Message", "string")]), f"""(fn ShowToast (Message)
  (Widget|SetText(Text) :self {var("TxtToast")} :InText (Utilities|Text|ToText(String) Message))
  (Widget|SetVisibility :self {var("Toast")} :InVisibility "HitTestInvisible")
  (Variables|Default|SetToastUntil (+ (Utilities|Time|GetGameTimeInSeconds) 3.0)))""", "SetToastUntil")
ui_theme.write(ui_theme.function(widget_bp, "ShowSoon", [("Feature", "string")]), """(fn ShowSoon (Feature)
  (CallFunction|ShowToast :Message (Utilities|String|Append Feature "  ·  เร็ว ๆ นี้")))""", "ShowToast")
ui_theme.write(ui_theme.function(widget_bp, "ClosePanels"), f"""(fn ClosePanels ()
  {hide_all})""", "SettingsOverlay")
ui_theme.write(ui_theme.function(widget_bp, "OpenPanel", object_inputs=[("Panel", unreal.Widget.static_class())]), """(fn OpenPanel (Panel)
  (CallFunction|ClosePanels)
  (Widget|SetVisibility :self Panel :InVisibility "Visible"))""", "ClosePanels")
ui_theme.write(ui_theme.function(widget_bp, "Travel", [("Map", "string")]), """(fn Travel (Map)
  (Widget|RemoveFromParent self)
  (Game|OpenLevel(byName) :LevelName Map))""", "OpenLevel")
profile_graph = ui_theme.function(widget_bp, "OpenProfile")
names = {key: ui_theme.node(profile_graph, "BPBoatGameInstance|" + key) for key in ("GetSelectedBoat", "GetSelectedEngine", "GetBoatInfo", "GetEngineInfo")}
ui_theme.write(profile_graph, f"""(fn OpenProfile ()
  (bind gi (Utilities|Casting|CastToBP_BoatGameInstance (Game|GetGameInstance))
    (:then
      (bind (boatName boatText boatPower) ({names['GetBoatInfo']} :self gi :Index ({names['GetSelectedBoat']} :self gi)))
      (bind (engineName engineText enginePower engineTop) ({names['GetEngineInfo']} :self gi :Index ({names['GetSelectedEngine']} :self gi)))
      (Widget|SetText(Text) :self {var("TxtProfileBoat")} :InText boatName)
      (Widget|SetText(Text) :self {var("TxtProfileEngine")} :InText engineName)
      (CallFunction|OpenPanel :Panel {var("ProfileOverlay")}))
    (:CastFailed)))""", "TxtProfileEngine")
console = ui_theme.node(profile_graph, "Development|ExecuteConsoleCommand")


def click_body(action):
    kind = action[0]
    if kind == "open":
        return f'(CallFunction|Travel :Map "{action[1]}")'
    if kind == "panel":
        return f"(CallFunction|OpenPanel :Panel {var(action[1])})"
    if kind == "profile":
        return "(CallFunction|OpenProfile)"
    if kind == "close":
        return "(CallFunction|ClosePanels)"
    return f'(CallFunction|ShowSoon :Feature "{action[1]}")'


bodies = {"Btn" + name: click_body(action) for name, action in ACTIONS.items()}
for name, _, level in MAPS:
    bodies[name] = f'(CallFunction|Travel :Map "{level}")'
for name in ["BtnRaceClose", "BtnProfileClose", "BtnWalletClose", "BtnNoticeClose", "BtnMailClose", "BtnSettingsClose"] + [f"Btn{p}Dim" for p in PANELS]:
    bodies[name] = "(CallFunction|ClosePanels)"
bodies["BtnProfileGarage"] = f'(CallFunction|Travel :Map "{GARAGE_MAP}")'
bodies["BtnWalletStore"] = '(CallFunction|ShowSoon :Feature "STORE")'
bodies["BtnNoticeEvent"] = f"(CallFunction|OpenPanel :Panel {var('RaceOverlay')})"
bodies["BtnMailClaim"] = '(CallFunction|ClosePanels)\n  (CallFunction|ShowToast :Message "รับรางวัลแล้ว  ·  ระบบเหรียญจะเชื่อมในเวอร์ชันถัดไป")'
for name, label, level in QUALITY:
    bodies[name] = f'({console} :Command "scalability {level}")\n  (CallFunction|ShowToast :Message "คุณภาพกราฟิก: {label}")'
bodies["BtnWindowed"] = f'({console} :Command "r.SetRes 1280x720w")\n  (CallFunction|ShowToast :Message "โหมดหน้าต่าง 1280×720")'
bodies["BtnFullscreen"] = f'({console} :Command "r.SetRes 1920x1080f")\n  (CallFunction|ShowToast :Message "โหมดเต็มจอ")'
bodies["BtnShowFps"] = f'({console} :Command "stat fps")\n  (CallFunction|ShowToast :Message "สลับการแสดง FPS")'

ui_theme.bind_clicks(widget_bp, bodies)
events = "\n\n".join(f"(event OnClicked({name})\n  {body})" for name, body in bodies.items())
ui_theme.write(Blueprint.get_graph(widget_bp, "EventGraph"), f"""(event UserInterface|EventTick (MyGeometry InDeltaTime)
  (if (> (Utilities|Time|GetGameTimeInSeconds) (Variables|Default|GetToastUntil))
    (Widget|SetVisibility :self {var("Toast")} :InVisibility "Collapsed")))

{events}""", "OnClicked(BtnTopProfile)", "OnClicked(BtnShowFps)", "OpenProfile")
Blueprint.compile_blueprint(widget_bp, warnings_as_errors=True)
unreal.EditorAssetLibrary.save_loaded_asset(widget_bp, only_if_is_dirty=False)
print("MAINMENU_GRAPH_READY", len(bodies), "buttons")

# ---------------------------------------------------------------- host
print("MAINMENU_HOST_READY", ui_theme.write_host())

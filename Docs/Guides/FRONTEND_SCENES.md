# ฉากเมนูและโรงรถ

ฉากเริ่มต้นสำหรับ UI อยู่ใน `/Game/Maps/M_MainMenu` และ `/Game/Maps/M_Garage`.

- Main Menu: แท่นโชว์เรือ เสาท่าเรือ หลังคา และพื้นหลัง blockout สำหรับจัดองค์ประกอบเมนู
- Garage: แท่นโชว์เรือ ขารองรับ โต๊ะทำงาน ผนัง และโครงเสา
- ทั้งสองฉากใช้เรือแสดงผล `BP_ThaiLongtailBoat` ที่ปิดฟิสิกส์/การชน แยกจาก Pawn สำหรับขับ
- กล้อง `Frontend_ShowcaseCamera` เปิดใช้อัตโนมัติสำหรับ Player 0; FOV 45 องศา ไม่บังคับสัดส่วนจอ
- วัตถุที่สร้างอยู่ในโฟลเดอร์ Outliner `Frontend`.

ฉากเหล่านี้เป็น blockout ไม่ใช่งาน environment ขั้นสุดท้าย จุดเริ่มต้นใน config เป็น Main Menu
UI ทั้งหมดเป็น Blueprint/UMG จึงไม่ต้อง build C++

ทุกฉากมี `UI_TestNavigationHost` หนึ่งตัว: ฉากเมนูแสดง `WBP_MainMenu` และฉากขับแสดง `WBP_DriveHUD`
(โชว์รูม `M_Garage` ใช้ `BP_ShowroomStage` แทน) widget จะถอดตัวเองก่อนเปลี่ยนฉากเพื่อไม่ให้ UI ซ้อน
ฟอนต์ Noto Sans Thai มี Roboto เป็น fallback สำหรับตัวเลขและอักษรอังกฤษ

## เมนูหลัก (`/Game/UI/MainMenu/WBP_MainMenu`)

พื้นหลังคือ `Content/Boats/UI_REF.png` ทั้งภาพ ปุ่มทุกปุ่มเป็นภาพที่ตัดจากตำแหน่งเดิมมาวางทับพอดี
มีสถานะชี้เมาส์ (ไฮไลต์ส้มหรือกรอบทอง) และสถานะกด แสงเลือกที่ติดมากับภาพเดิม (แถว HOME และการ์ด PLAY/RACE)
ถูกลบออกจากพื้นหลังแล้ว จึงไฮไลต์เฉพาะปุ่มที่ชี้อยู่ หน้าจอย่อพอดีทุกสัดส่วนจอ ถ้าจอไม่ใช่ 16:9 จะมีขอบดำ ปุ่มไม่ถูกตัด

| ปุ่ม | การทำงาน |
| --- | --- |
| GARAGE, CUSTOMIZE, การ์ด GARAGE | ไปโชว์รูม `M_Garage` |
| RACE, การ์ด PLAY/RACE, SEASONAL EVENT | หน้าต่างเลือกสนาม 4 สนาม |
| แถบบัญชีขวาบน | โปรไฟล์ (เรือและเครื่องที่เลือกจริง), กระเป๋าเงิน, แจ้งเตือน, จดหมาย, ตั้งค่า |
| SETTINGS / ไอคอนเฟือง | คุณภาพกราฟิก (`scalability 0–3`), หน้าต่าง/เต็มจอ, แสดง FPS |
| CAREER, MULTIPLAYER, SHOP, EVENT, LEADERBOARD, CHALLENGE, STORE, ข่าว | ข้อความ "เร็ว ๆ นี้" |

คลิกพื้นที่มืดนอกหน้าต่างเพื่อปิดได้ ข้อมูลบัญชี (BoatRacerTH, เหรียญ, เพชร, แจ้งเตือน, จดหมาย) เป็นข้อมูลตัวอย่างตามภาพอ้างอิง ยังไม่มีระบบบัญชีจริง

### ธีมและการสร้างใหม่

ธีมกลาง (แผงกระจกเข้ม ขอบทอง ป้ายหัวข้อทอง ปุ่มทอง/ส้ม) อยู่ใน `Tools/ui_theme.py` ใช้ร่วมกันทั้งเมนูหลัก โชว์รูม และ HUD ระหว่างขับ

1. `powershell -File SourceAssets/UI/Theme/make_theme.ps1`: สร้าง texture ธีม
2. `powershell -File SourceAssets/UI/MainMenu/make_buttons.ps1`: ลบแสงเลือกออกจากพื้นหลัง ตัดปุ่มตาม `layout.json` และสร้างสถานะชี้เมาส์/กด (ใช้เวลาราว 30 วินาที)
3. รัน `mainmenu_build.py`, `showroom_build_ui.py`, `showroom_build_graphs.py` และ `drive_ui_build.py` ตามลำดับ ผ่าน `Tools/run_editor_script.py`

ถ้าจะย้ายหรือเพิ่มปุ่ม ให้แก้กรอบ `[x, y, กว้าง, สูง]` (พิกัดในภาพ 1672×941) ใน `layout.json` แล้วรันข้อ 2–3 ใหม่
ระหว่างที่เปิดเกมแบบ `-game` อยู่ ต้องปิดเกมก่อนรันสคริปต์ เพราะ `run_editor_script.py` จะเจอ Unreal 2 ตัว

## HUD ระหว่างขับ (`/Game/UI/MainMenu/WBP_DriveHUD`)

- มุมซ้ายบน: โลโก้ เรือและเครื่องที่ใช้ ปุ่มเมนูหลักและโชว์รูม และปุ่มควบคุม
- มุมขวาล่าง: ความเร็ว (กม./ชม.) รอบเครื่องและคันเร่ง อ่านจาก `BP_LongtailPhysicsPawn` ทุกเฟรม
- ถ้าเมาส์ถูกจับใน viewport ระหว่าง PIE ให้กด Shift+F1 ก่อนคลิกปุ่ม

## โชว์รูม: เลือกเรือและเครื่องยนต์

`M_Garage` เป็นหน้าโชว์รูม ทำด้วย Blueprint ล้วน จึงไม่ต้อง build C++

- **เรือ 2 ลำ** (ปุ่ม `<` `>`): หางยาวมาตรฐาน (`BP_ThaiLongtailBoat`) และ R3 สปีดเรเซอร์ (`/Game/Showroom/Boats/BP_Boat_R3`) ที่ใช้ตัวเรือ Refine03 ปรับขนาดให้เท่าลำเดิม ส่วนห้องคนขับ แกนท้าย และฟิสิกส์ใช้ชุดเดิม
- **เครื่องยนต์ 4 แบบ**: เครื่องเดิม V4, Racing 150cc, Thai 150cc และ River Racer 125cc เครื่องใหม่เป็น Actor ใน `/Game/Showroom/Engines` ที่ติดบน `EngineAssembly` ตำแหน่ง `EngineMountOffset` (240, 0, 50) แทนชุดเครื่องเดิมที่ถูกซ่อน ภาพจึงสั่นตามเครื่องเหมือนเดิม
- **ค่าที่มีผลตอนขับ**: แรงขับคูณ `เรือ × เครื่อง` และความเร็วเป้าหมายของ governor คูณตามเครื่อง (ฐาน 110 กม./ชม.) ค่าเหล่านี้กำหนดใน `GetBoatInfo` และ `GetEngineInfo` ของ `BP_BoatGameInstance`

| ตัวเลือก | แรงขับ | ความเร็วเป้าหมาย |
| --- | --- | --- |
| เครื่องเดิม V4 | ×1.00 | 110 กม./ชม. |
| Racing 150cc | ×1.12 | 123 กม./ชม. |
| Thai 150cc | ×1.05 | 114 กม./ชม. |
| River Racer 125cc | ×0.90 | 105 กม./ชม. |
| เรือ R3 | ×1.06 (คูณเพิ่มจากเครื่อง) | ตามเครื่อง |

### การทำงาน

1. `BP_BoatGameInstance` (ตั้งใน `DefaultEngine.ini` เป็น `GameInstanceClass`) เก็บ `SelectedBoat` และ `SelectedEngine` และบันทึกลง slot `BoatShowroom` ทุกครั้งที่เลือก ค่าจะยังอยู่หลังปิดเกม
2. `BP_ShowroomStage` ใน `M_Garage` มีแท่นหมุน กล้อง และ `WBP_Showroom` ถ้าจะปรับมุมกล้อง ให้แก้ component `Camera` ใน Blueprint
3. `BP_ThaiLongtailBoat.ApplyLoadoutVisual` ทำงานตอน BeginPlay จึงติดเครื่องที่เลือกให้ทุกที่ที่มีเรือ ทั้งในโชว์รูม เมนูหลัก และตอนขับ
4. `BP_LongtailPhysicsPawn.ApplyLoadout` ทำงานต่อท้าย `LoadHandlingProfile`: เปลี่ยนคลาสตัวเรือที่แสดง แล้วคูณแรงขับและความเร็วเป้าหมาย ค่าใน `DA_ThaiLongtail_Handling` ไม่ถูกแก้
5. ปุ่ม `ไปขับในคลอง` เปิด `M_CanalBlockout` ส่วนปุ่มโชว์รูมในเมนูหลักและระหว่างขับจะพามาที่ `M_Garage`

### สร้างโชว์รูมซ้ำ

เปิด editor และหยุด PIE ก่อน แล้วรันสคริปต์ตามลำดับนี้ด้วย `Tools/run_editor_script.py`:

1. `import_new_boat_models.py`: import โมเดลเครื่องยนต์จาก `../Model/Blender`
2. `showroom_build_assets.py`: สร้าง Blueprint เครื่องยนต์ เรือ R3 และตัวแปรใหม่ของเรือ (ก่อนแก้จะสำรองไฟล์ไว้ที่ `Saved/Backups/*-showroom`)
3. `showroom_build_logic.py`: กราฟของ GameInstance ตัวเรือ และ Pawn
4. `showroom_build_ui.py`, `showroom_build_graphs.py`: หน้าจอ แท่นหมุน และปุ่ม
5. `showroom_setup_level.py`: วางแท่นใน `M_Garage`
6. `showroom_fix_thai_font.py`: ตั้ง Roboto เป็น fallback ของฟอนต์ไทย เพื่อให้ตัวเลขและอักษรอังกฤษแสดงได้

ข้อควรรู้:

- `write_graph_dsl` ไม่ลบ event เดิมที่ผูกกับปุ่ม และฟ้อง error เป็นแค่ warning ใน log สคริปต์จึงอ่าน log ตรวจเองทุกครั้ง
- กราฟ `LoadHandlingProfile` ของ Pawn เขียนผ่าน DSL ทับไม่ได้ จึงต่อ node ทีละตัว
- ห้ามสร้าง widget ชื่อซ้ำกับของเดิมที่เป็นคนละชนิด เพราะ editor จะ crash
- `BoatSlot` ของแท่นหมุนต้องไม่มี Child Actor Class ใน Blueprint (แท่นจะใส่เรือเองตอนเริ่มเกม) ถ้าตั้งคลาสไว้ จะเกิด child-actor template (`*_CAT_*`) ที่เคยหลุดไปอยู่ใน `M_Garage` เป็นเรือลำเดิมอีกลำวางซ้อนตลอด `showroom_setup_level.py` จะลบลำที่หลุดนี้ให้
- ChildActorComponent ส่งสถานะซ่อน/แสดงของ component จากเรือลำก่อนไปให้ลำใหม่ `ApplyLoadoutVisual` จึงตั้งการแสดงตัวเรือทั้งสองทางทุกครั้ง ถ้าตัดส่วนนี้ออก เรือลำเดิมจะไม่มีตัวเรือหลังเปลี่ยนกลับจาก R3
- โค้ด C++ `BoatFrontend*` ใน plugin ยังไม่ได้ build ถ้า build ภายหลัง subsystem ตัวนั้นจะสร้าง UI ของตัวเองในทุกฉาก และซ้อนกับโชว์รูม Blueprint ต้องเลือกใช้ระบบใดระบบหนึ่ง

## สร้างฉากซ้ำ

เปิดโปรเจคนี้ใน Unreal Editor หยุด PIE แล้วรัน:

```powershell
& 'C:/Program Files/Epic Games/UE_5.8/Engine/Binaries/ThirdParty/Python3/Win64/python.exe' Tools/run_editor_script.py Tools/create_frontend_scenes.py
```

สคริปต์บันทึกงานก่อนสลับ level และสร้างวัตถุในโฟลเดอร์ `Frontend` ใหม่.
ย้ายวัตถุที่ปรับแต่งเองออกจากโฟลเดอร์นี้ก่อนรันซ้ำ เพื่อเก็บงานของคุณไว้.
ไม่ใช้ commandlet หรือ NullRHI ในการสร้างฉาก.

# แผนผังไฟล์และระบบโปรเจกต์

อัปเดต 2026-09-30 (Asia/Bangkok). คู่มือนี้อิงไฟล์จริงและ checkpoint ที่ตรวจใน Unreal ก่อนหน้า ไม่ใช่รายการฟีเจอร์ที่คาดว่าจะทำเสร็จ.

## 1. โฟลเดอร์หลัก

ทุก path บนดิสก์ในตารางนี้เริ่มจาก `A:\Project\Unreal Engine 5\BoatlRacing\`.

| ไฟล์/โฟลเดอร์ | หน้าที่ | วิธีจัดการ |
| --- | --- | --- |
| `BoatlRacing.uproject` | เปิดโปรเจกต์และรายการ plugin | เปิดด้วย UE 5.8.3; EngineAssociation ระบุ 5.8 |
| `Content/` | Blueprint, mesh, material, texture, เสียง และแผนที่ | แก้ผ่าน Unreal Editor ไม่แก้ไบนารีด้วย text editor |
| `Config/` | การตั้งค่าโปรเจกต์และ Editor | สำรองก่อนเปลี่ยน; อย่านำ token หรือข้อมูลส่วนตัวไปเผยแพร่ |
| `Plugins/BoatlRacingPhysics/` | C++ runtime bridge สำหรับน้ำ/ทุ่น/แรงท้าย | โค้ดหลักอยู่ใน plugin ไม่ได้อยู่ใน root `Source/` |
| `SourceAssets/` | GLB, OBJ และ WAV ต้นทางนำเข้า | เก็บไว้สำหรับตรวจและ reimport แบบมีแผน |
| `Tools/` | สคริปต์ Unreal Python และสำเนา Blueprint DSL | มีทั้งเครื่องมือเก่าและตัวทดลอง ไม่ใช่ rebuild script ที่รันทั้งหมดได้ |
| `Docs/` | คู่มือ สเปก แผน สถานะ และหลักฐาน | เริ่มที่ [README](../README.md) |
| `Saved/Backups/` | สำเนา package ก่อนแก้ | เก็บจุดกู้คืน; ไม่ลบทิ้งพร้อม cache |
| `Saved/Automation/` | รายงาน Unreal Automation และ standalone tools | ดูชนิด runner และขอบเขตจริง; ไม่ใช้ผล standalone แทนผลในเกม |
| `Saved/Logs/` | log Editor/build/runtime | ใช้วินิจฉัย; ตรวจข้อมูลส่วนตัวก่อนส่งออก |
| `Binaries/`, `Intermediate/`, `DerivedDataCache/` | ผล build และ cache ที่สร้างใหม่ได้ | ไม่ใช่ source; อย่าลบระหว่าง Editor/build ทำงาน |

`/Game/...` ใน Content Browser ตรงกับ `Content/...` บนดิสก์ เช่น `/Game/Maps/M_WaterPhysicsTest` คือ `Content/Maps/M_WaterPhysicsTest.umap`. `.uasset` และ `.umap` เป็น Unreal package ไม่ใช่ไฟล์ข้อความ.

## 2. เรือและ Handling

path ในตารางใช้ Content Browser; prefix เรือคือ `/Game/Boats/ThaiLongtail/`.

| Asset | หน้าที่ |
| --- | --- |
| `Blueprints/BP_LongtailPhysicsPawn` | ตัวขับจริง: Chaos, Buoyancy, input, thrust, drag, กล้อง และเรียกภาพ/FX/เสียง |
| `Blueprints/BP_ThaiLongtailBoat` | ประกอบภาพเรือ 98 ชิ้น และขยับคันบังคับ แกนท้าย ใบพัด เครื่องยนต์ |
| `Physics/SM_BoatPhysicsHull` | convex collider แบบเบา; เป็นตัวรับแรงและชน |
| `Handling/BP_BoatHandlingData` | คลาสข้อมูล Handling; การเพิ่ม field ต้องปรับ loader ตาม |
| `Handling/DA_ThaiLongtail_Handling` | ค่าจูนของเรือลำนี้ 18 fields; ดู [คู่มือ Handling](HANDLING_GUIDE.md) |
| `thai_racing_longtail_runtime_2k/` | mesh/material/texture จาก GLB; 77 Static Mesh + 21 Skeletal Mesh |

Physics Pawn มี visual child ที่ปิด collision. การสั่นเครื่องเป็นภาพ ไม่ใช่การขยับ rigid body ทั้งเรือ. เฉพาะทุ่นลำเรือให้แรงลอยตัว ใบพัดไม่เป็นแท่งค้ำผิวน้ำ.

Visual แยก `HullAssembly`, `InteriorAssembly`, `CockpitAssembly`, `EngineAssembly`, `DrivelineAssembly`, `DetailsAssembly`. ตำแหน่ง pivot และสายบังคับดู [BOAT_ASSEMBLY](../BOAT_ASSEMBLY.md). รุ่นนี้ต่อแกนถึง hub ยาว 246 cm จาก pivot; การ scale แกน X 1.5 ใน Blueprint ยังยืด UV ต้องกลับไปแก้ Blender ก่อน reimport สำหรับ production.

Blender master อยู่นอกโปรเจกต์: `C:\Users\LEONIDASxII\Documents\Codex\2026-09-28\blender-skill-plugin\outputs\thai_racing_longtail.blend`. ต้นทางใช้ texture 4K แต่ GLB runtime ใช้ atlas 2K เพื่อคุมหน่วยความจำ ไม่ใช่ทุก texture ใน Unreal เป็น 4K. การ deduplicate texture/material และ LOD ยังไม่เสร็จ.

## 3. แผนที่และน้ำ

| Asset | หน้าที่ |
| --- | --- |
| `/Game/Maps/M_WaterPhysicsTest` | น้ำเรียบ baseline และ startup map |
| `/Game/Maps/M_WaterSmallWavesTest` | คลื่นเล็กสำหรับตรวจการลอย/สัมผัสใบพัด |
| `/Game/Maps/M_WaterHighWavesTest` | คลื่นสูง stress test; ยังไม่ผ่านเกณฑ์สนามแข่ง |
| `/Game/Water/Waves/WW_SmallGerstner` | wave asset สำหรับคลื่นเล็ก |
| `/Game/Water/Waves/WW_HighGerstner` | wave asset สำหรับคลื่นสูง |
| `/Game/boat` | แผนที่เดิมของผู้ใช้ ไม่ได้ถูกแทนที่ด้วยสนามทดสอบ |

`Content/__ExternalActors__/boat/`, `Content/__ExternalObjects__/boat/` และ `boat_HLOD0_Instancing.uasset` เป็น package ที่สัมพันธ์กับแผนที่เดิม/World Partition. ห้ามคิดว่าเป็นขยะหรือย้ายออกแยกจากแผนที่.

น้ำวาดทะลุห้องเรือกับเรือจมจริงเป็นคนละปัญหา. สเปก [moving hull water mask](../Specs/2026-09-30-moving-hull-water-mask-design.md) เป็นงานออกแบบที่ยังไม่ติดตั้ง จะไม่แทนที่แรงลอยตัวและไม่ปิดน้ำทั่วโลก.

Asset ใหม่ `/Game/Water/Materials/MPC_BoatInteriorMasks` สร้าง/เซฟแล้ว แต่ปิดไว้และยังไม่มี water shader/Pawn ใช้มัน. เป็นช่องข้อมูล 8 slots ไม่ใช่ระบบแก้น้ำทะลุที่ทำงานแล้ว. ชื่อ/packing ดู [คู่มือพัฒนา Water Mask](WATER_MASK_DEVELOPMENT.md).

## 4. ลำดับระบบของ Pawn

| Function | หน้าที่ |
| --- | --- |
| `ConfigureBoatMass` | BeginPlay: โหลด Handling ตั้งมวล/COM และรัศมีทุ่น runtime |
| `LoadHandlingProfile` | ตรวจทั้งโปรไฟล์ แล้ว cache ค่า; หากผิดให้ใช้ค่า fallback ของ Pawn |
| `UpdateDriveState_0` | อ่านคีย์/QA override, throttle, clutch, RPM และคำสั่งเลี้ยว/trim |
| `UpdateShaftState` | แรงเฉื่อยรอบเพลา, ความเร็วแนวราบ, governor และ DriveThrust |
| `GetGovernorDriveScale` | ลดกำลังเมื่อเข้าใกล้ 110 km/h ไม่ล็อก velocity |
| `UpdateWaterPropState` | ถามระดับคลื่นที่ hub จริง ตั้ง immersion/auto trim และเรียก launch pulse |
| `ApplyLaunchPitch` | torque กระชากหัวสั้น ๆ เฉพาะเงื่อนไขออกตัว; ไม่ยึด pitch |
| `ApplyTailWaterSteering` | แรงต้านข้างของแกนที่เปียกน้ำ ให้เลี้ยวระหว่างไหลได้ |
| `ApplyHydrodynamicDrag` | แรงต้านกำลังสองตามความเร็วแนวราบ |
| `UpdateCameraState` | มุมหัวเรือ/คนขับเห็นปลายหัว/3PS/Free Orbit ตามเรือ |
| `UpdateFXState_0` | ส่งสถานะความเร็ว/น้ำ/รอบให้ Niagara |
| `ApplyEngineVibration` | สั่นเฉพาะภาพเครื่องช่วงออกตัวและความเร็วสูงที่มีโหลด |
| `UpdateEngineAudio` | เล่นเสียงสตาร์ท/loop ปรับ pitch และ volume |
| `GetSternWaveHeight` | function เก่าที่เหลืออยู่; native hub query แทนทางเดินนี้แล้ว |

Tick เริ่มจาก input/drive แล้วคำนวณเพลา กล้อง steering น้ำ/trim แรงต้านท้าย และมุมใบพัด ก่อนให้ thrust เมื่อเปียกน้ำ จากนั้นอัปเดตภาพ FX การสั่น drag และเสียง. ระบบ propulsion/tail force เป็นแนวราบ ใช้จุดออกแรงที่ runtime COM world Z เพื่อไม่ค้ำท้าย; อย่าเปลี่ยนไปออกแรงแนวดิ่งที่ใบพัด.

Input ปัจจุบัน poll keyboard ใน Blueprint เป็น prototype ไม่ใช่ Enhanced Input ที่รองรับ gamepad/rebinding แล้ว. `DefaultInput.ini` จึงไม่ใช่ไฟล์หลักสำหรับเปลี่ยนการอ่านคีย์ปัจจุบัน.

## 5. FX และเสียง

| Asset ภายใต้ prefix เรือ | หน้าที่ |
| --- | --- |
| `FX/NS_LongtailWake` | รอยน้ำท้ายตามการเคลื่อนที่ |
| `FX/NS_LongtailPropSpray` | สเปรย์ใบพัดตามสัมผัสน้ำและการขับ |
| `FX/NS_LongtailExhaust` | ควันจากเครื่องตามรอบ/การเร่ง |
| `Audio/SW_LongtailEngineTest` | engine loop สังเคราะห์เพื่อทดสอบ |
| `Audio/SW_LongtailStartTest` | เสียงสตาร์ททดสอบ |

ระบบมีแล้วแต่คุณภาพ spray, particle budget, เสียงที่ฟังจริง และ clipping ยังต้องตรวจ ไม่ใช่เสียงเครื่องยนต์จริงที่เสร็จแล้ว.

## 6. C++ อยู่ที่ไหน

prefix: `Plugins/BoatlRacingPhysics/`.

| ไฟล์ | หน้าที่ |
| --- | --- |
| `BoatlRacingPhysics.uplugin` | ประกาศ runtime plugin และ dependency Water |
| `Source/BoatlRacingPhysics/BoatlRacingPhysics.Build.cs` | dependency module: Core/CoreUObject/Engine/Water |
| `Source/BoatlRacingPhysics/Public/BoatlRacingWaterLibrary.h` | Blueprint-callable API |
| `Source/BoatlRacingPhysics/Private/BoatlRacingWaterLibrary.cpp` | SampleWaveSurface, SetHullPontoonRadii, CalculateTailWaterForce |
| `Source/BoatlRacingPhysics/Private/BoatWaterCurrentPolicy.h` | ใช้กระแสน้ำเฉพาะ River ที่เปิดแรงกระแสน้ำ ไม่ใช้ metadata Ocean/Lake |
| `Source/BoatlRacingPhysics/Private/BoatInteriorMaskMath.h` | reference math/curve profile/slot handles ของ water mask; ยังไม่ได้เรียกจาก runtime |
| `Source/BoatlRacingPhysics/Private/BoatlRacingPhysics.cpp` | เริ่ม module |
| `Source/BoatlRacingPhysics/Private/Tests/BoatlRacingWaterTests.cpp` | Automation: PhysicalCurrent, PontoonInitialization, TailDrag, TailInvalidInput |

`SampleWaveSurface` ใช้ IncludeWaves ที่ตำแหน่ง hub พร้อมตรวจพื้นที่น้ำ/exclusion/ตัวเลขผิด. `SetHullPontoonRadii` ตรวจ component พร้อมใช้งานก่อนแก้สี่ทุ่น. `CalculateTailWaterForce` เป็นแรงต้าน dissipative ที่จำกัดแรงและกัน overflow; comment ภาษาไทยอธิบายกรณีละเอียด.

การ rebuild DLL ต้องจัดการ Editor ที่ใช้งาน DLL อยู่ให้ถูกวิธี: เซฟก่อน ปิดตามปกติ หรือใช้ Live Coding ตาม workflow ที่รองรับ. ห้าม force-kill เพียงเพราะปิดติด Save Content. รอบเอกสารนี้ไม่ได้ build/test native ใหม่.

## 7. Tools และต้นทาง

| ไฟล์/กลุ่ม | หน้าที่และข้อควรระวัง |
| --- | --- |
| `SourceAssets/ThaiLongtail/*.glb` | โมเดล runtime 2K สำหรับ import; ห้าม blind reimport |
| `SourceAssets/Physics/SM_BoatPhysicsHull.obj` | geometry ต้นทาง collider; เปลี่ยนแล้วต้องตรวจ centroid/COM ใหม่ |
| `SourceAssets/Audio/*.wav` | เสียงสังเคราะห์ต้นทาง |
| `Tools/create_handling_assets.py` | สคริปต์สร้างครั้งแรก; constants เก่ากว่าค่าที่ใช้อยู่ ไม่มี TailWaterDragCoefficient; ไม่ใช้เป็นสูตร reset |
| `Tools/create_wave_assets.py`, `configure_wave_assets.py` | สร้าง/แก้ generator คลื่น; มีการ save asset |
| `Tools/create_wave_test_maps.py`, `assign_wave_test_map.py` | สร้าง map copy และผูก wave asset; เปลี่ยน package |
| `Tools/set_wave_map_pontoons.py` | เปลี่ยน Pawn ของ map เพื่อแก้ instance override; อ่าน guard/flag ก่อนใช้ |
| `Tools/verify_wave_test_map.py` | ตรวจ wave reference; query ที่ไม่ได้ IncludeWaves ไม่พิสูจน์ระดับยอดคลื่นจริง |
| `Tools/inspect_boat_water_runtime.py` | ตรวจ graph/map/component/material ไม่เขียน asset; แต่โหลด map เปลี่ยนบริบท Editor |
| `Tools/inspect_ocean_course.py` | อ่าน course; โหลดแผนที่ baseline |
| `Tools/integrate_boat_water_bridge.py` | แก้ graph ในหน่วยความจำแม้ dry-run; save เมื่อมี flag; ยังไม่ใช่ reproduction ครบของการแก้ที่ยืนยันแล้ว |
| `Tools/generate_engine_test_audio.py`, `import_engine_test_audio.py` | สร้าง WAV / import และแก้ looping |
| `Tools/probe_*.py` | สำรวจ API ในอดีต; บางตัวสร้าง object หรือเปลี่ยน property ชั่วคราว ไม่รับประกัน read-only |
| `Tools/BlueprintDSL/*.dsl` | snapshot เก่า ไม่ใช่ source ล่าสุดทุก function |
| `Tools/BlueprintDSL/WaterBridge/` | มีสำเนา 4 functions ที่ apply แล้วและ README ระบุข้อจำกัด |
| `Tools/Tests/run_boat_interior_mask_tests.ps1` | compile/run reference core ด้วย MSVC; ไม่ใช่ Unreal Automation |
| `Tools/Tests/measure_boat_mask_section.ps1` | วัดหน้าตัด GLB และ export triangles แบบตรวจ index/offset/ancestor |
| `Tools/Tests/boat_mask_geometry_test.ps1` | fixture ตรวจการปฏิเสธ ancestor/GLB reference ที่ผิด |
| `Tools/Tests/BoatMaskMesh.h`, `boat_mask_mesh_test.cpp`, `run_boat_mask_mesh_tests.ps1` | ray survey ผิว liner จริงและทดสอบข้อจำกัด; ไม่ใช่ profile ที่รับรองแล้ว |

ใน WaterBridge มี `UpdateDriveState_0.dsl` ที่ **ยังไม่ apply** และเคยถูก auto-review ปฏิเสธ. ห้าม bulk import ทุก DSL. Graph ที่บันทึกใน Blueprint เป็นตัวอ้างอิงพฤติกรรมปัจจุบัน; ต้องอ่านกลับก่อนแทนที่.

## 8. ตั้งค่า หลักฐาน และงานต่อ

`Config/DefaultEngine.ini` ตั้ง startup map และ rendering; `DefaultGame.ini` ตั้ง project/game; `DefaultEditor.ini` และ `DefaultEditorPerProjectUserSettings.ini` เกี่ยวกับ Editor. ไม่แก้ settings ที่ไม่เกี่ยวกับงาน.

หลักฐานล่าสุดก่อนรอบเอกสาร: `Saved/Automation/WaterCurrentGreen/index.json` รายงาน 4 passed/0 failed; `Docs/Work/2026-09-30-water-current-regression.json` เป็น runtime snapshots ตาม wall time ไม่ใช่ telemetry ที่เวลา simulation คงที่. Backup ของ Pawn และสาม map อยู่ที่ `Saved/Backups/2026-09-30-native-bridge/`. โปรเจกต์ไม่มี Git repository; อย่าอ้างว่ามี commit หรือใช้ package backup แทน version control โดยไม่ระบุข้อจำกัด.

งานเปิด: mask น้ำในห้องเรือ, timed coast/launch/reverse/clutch/wave acceptance, input production, ตรวจ linkage/UV/LOD/material memory, เสียง/FX, collision/damage และระบบแข่งขัน. รายละเอียดล่าสุดดู [STATUS](../STATUS.md) และ [HANDOFF](../HANDOFF.md).

ผล mask ใหม่อยู่ใน `Saved/Automation/WaterMaskMath/`: reference core 121 checks, mesh survey 4,279 checks, ทั้งสองเป็น standalone MSVC และไม่พิสูจน์ shader/gameplay. วิธีรันและข้อจำกัดดู [WATER_MASK_DEVELOPMENT](WATER_MASK_DEVELOPMENT.md). ไม่มี mask assets ที่ใช้งานแล้วใน Content.

# คู่มือ Handling เรือ

อัปเดต 2026-09-30 (Asia/Bangkok). ค่าตารางเป็น checkpoint ที่อ่านจาก Unreal ในวันเดียวกันก่อนระบบตรวจสิทธิ์ติดโควตา; การอ่านซ้ำท้ายรอบเอกสารไม่ได้ถูก execute. ไม่ได้ทดสอบฟิสิกส์ใหม่ในรอบนี้.

## 1. จูนที่ไหน

เปิด `/Game/Boats/ThaiLongtail/Handling/DA_ThaiLongtail_Handling` ใน Content Browser. คลาสข้อมูลคือ `BP_BoatHandlingData`; Pawn ขับคือ `BP_LongtailPhysicsPawn` และใช้ตัวแปร `HandlingProfile` อ้างอิง asset นี้.

ไฟล์บนดิสก์: `A:\Project\Unreal Engine 5\BoatlRacing\Content\Boats\ThaiLongtail\Handling\DA_ThaiLongtail_Handling.uasset`. แก้ใน Unreal ไม่แก้ `.uasset` ด้วย text editor. คู่มือนี้เป็น MD อธิบาย ไม่ใช่ไฟล์ config ที่ engine อ่านเอง.

โหลดค่าและตั้งมวลตอน BeginPlay. **แก้ Data Asset แล้ว Stop/Play ใหม่** ไม่ควรคาดว่าค่าจะเปลี่ยนทันทีในเรือที่กำลังเล่น. ห้ามรัน `Tools/create_handling_assets.py` เพื่อรีเซ็ต: มันมีค่าเริ่มต้นเก่าและ guard สำหรับสร้าง asset ครั้งแรก.

## 2. หน่วยและทิศ

ระยะเป็น cm, ความเร็วฟิสิกส์ cm/s, มวล kg. ความเร็ว HUD/engine target = ความยาว velocity แนวราบ * 0.036 เป็น km/h. `ForwardSpeedKmh` เป็นขนาดความเร็วแนวราบ ไม่ใช่ signed speed; ถอยหลังก็มีค่าบวก. การเด้งแนวดิ่งไม่เพิ่ม racing speed.

โมเดลนี้หัวเรืออยู่ -X ท้ายอยู่ +X; Z ขึ้น. pitch ติดลบหมายถึงหัวเงยสำหรับโมเดลนี้. อย่านำเครื่องหมายนี้ไปใช้กับโมเดลที่หัน +X โดยไม่แก้ทิศแรงและ pivot.

แรงใช้หน่วย Unreal kg*cm/s² และ torque kg*cm²/s². เช่น DriveForce 1,200,000 เทียบ 12,000 N ก่อน factor ของระบบขับ; ไม่ใช่แรงม้า และไม่ใช่ค่าที่วัดจากเครื่องจริง. Drag เป็น coefficient ตามสมการใน graph ไม่ใช่ Cd ไร้หน่วยที่คัดลอกจากตารางวิศวกรรมได้ทันที.

## 3. ค่าปัจจุบันทั้ง 18 Fields

| Field | ค่า | หน่วย/ความหมาย | ผลเมื่อเพิ่ม |
| --- | ---: | --- | --- |
| `HullMassKg` | 250 | kg มวลกลุ่มลำเรือ | เร่งยากขึ้นและ COM ขยับเข้าใกล้ HullCenter |
| `EngineMassKg` | 200 | kg มวลกลุ่มเครื่อง | ท้ายหนักขึ้นตามตำแหน่งเครื่อง และมวลรวมเพิ่ม |
| `HullCenterXcm` | -20 | cm จุดมวลลำเรือใน boat space | ขยับ COM ไปท้าย |
| `EngineCenterXcm` | 270 | cm จุดมวลเครื่องใน boat space | ขยับ COM ไปท้ายโดยไม่เพิ่มมวล |
| `CenterZcm` | -20 | cm desired COM ใน boat space | สูงขึ้นมีแนวโน้มโคลงง่ายขึ้น |
| `FrontPontoonRadiusCm` | 60 | cm รัศมีสองทุ่นหน้า | ปริมาตรรับแรงลอยตัวด้านหน้าเพิ่ม |
| `RearPontoonRadiusCm` | 55 | cm รัศมีสองทุ่นท้าย | รองรับท้ายมากขึ้น อาจลดท้ายต่ำ |
| `DriveForce` | 1200000 | แรงขับอ้างอิงหน่วย Unreal | เร่งแรงขึ้น; ต้องทดสอบการเลี้ยว/คลื่นร่วม |
| `LateralDrag` | 1200 | coefficient แรงต้านข้างของลำเรือ | ไถลข้างน้อยลง อาจเสียความเร็วในโค้ง |
| `QuadraticDrag` | 0.015 | coefficient แรงต้านแนวราบกำลังสอง | ไหลช้าลงและเสียความเร็วเร็วขึ้น |
| `TailWaterDragCoefficient` | 0.15 | coefficient แรงต้านข้างที่แกนท้ายเปียกน้ำ | coast steering แรงขึ้นพร้อมแรงต้าน ไม่ได้ให้แรงขับฟรี |
| `GovernorStartKmh` | 105 | km/h เริ่มลด positive drive | เริ่มลดกำลังช้าลงเมื่อเข้าใกล้ target |
| `TargetForwardSpeedKmh` | 110 | km/h เป้าหมายเครื่องในน้ำเรียบ | เป้าหมายกำลังสูงขึ้น ไม่ใช่ล็อกความเร็ว |
| `CruiseThrustScaleAtTarget` | 0.45 | factor 0..1 ณ target | กำลังที่เหลือ ณ target มากขึ้น |
| `OverspeedFadeKmh` | 6 | km/h ช่วงลดกำลังหลัง target | ลดเหลือศูนย์ช้าลง |
| `LaunchPitchTorque` | 12000000 | torque หน่วย Unreal | หัวกระชากขึ้นแรงขึ้นเฉพาะช่วงเข้าเงื่อนไข |
| `LaunchPulseSeconds` | 0.8 | s ระยะ envelope ออกตัว | ช่วงกระชากยาวขึ้น |
| `VibrationStartKmh` | 108 | km/h เริ่ม high-speed visual vibration | เครื่องเริ่มสั่นที่ความเร็วสูงขึ้น |

ทั้งหมดเป็นค่าต้นแบบเพื่อจูน gameplay ไม่ใช่สเปกเรือที่ชั่งหรือวัดจริง. โปรไฟล์ยังไม่ได้แยกมวลคนขับ น้ำมัน เพลา หรือ inertia tensor เป็น fields ของตัวเอง.

## 4. ศูนย์ถ่วงควรอยู่ตรงเครื่องไหม

**ไม่ใช่ทั้งหมดตรงเครื่อง**: จุดศูนย์ถ่วงรวมอยู่ระหว่างจุดมวลของส่วนต่าง ๆ และเข้าใกล้ส่วนที่หนักกว่า.

```text
Mass = HullMassKg + EngineMassKg
COM_X = (HullMassKg * HullCenterXcm + EngineMassKg * EngineCenterXcm) / Mass
      = (250 * -20 + 200 * 270) / 450
      = +108.8889 cm
COM_Z = -20 cm
```

เครื่องอยู่ +270 แต่ COM รวมอยู่ +108.89. นี่คือการให้น้ำหนักกดท้ายตามตำแหน่งจริง ไม่ใช่ตั้งภาพให้ท้ายห้อยด้วย rotation ตายตัว. มวลรวม 450 kg.

Collider ที่ใช้อยู่มี centroid X=75.7778, Z=5 cm. `ConfigureBoatMass` แปลง desired COM เป็น nudge ให้ Chaos: X=33.1111, Y=0, Z=-25 cm. ถ้าแก้ OBJ/collider ต้องคำนวณ centroid ใหม่ ห้ามเอา nudge เดิมไปใช้กับ geometry ใหม่.

ทุ่นหน้าสองลูก/ท้ายสองลูกช่วยลอยเฉพาะตัวเรือ. rear radius ที่เล็กกว่าหน้าอาจทำให้ท้ายต่ำ แต่ลดเกินไปทำให้ท้ายจมต่อเนื่องได้: เคยพบ instance override 48 cm ใน small-wave map แล้วแก้กลับ 55 cm. อย่าใช้ทุ่นเล็กผิดปกติเพื่อบังคับ silhouette.

## 5. แรงขับ แรงต้าน และแรงเฉื่อย

Propulsion ฉายแรงลง world XY และออกแรงที่ท้ายบน runtime COM world Z. จึงเลี้ยวด้วย lever arm ได้ แต่ไม่ให้ใบพัดยกท้ายเหมือนเสาค้ำ. การตอบสนองแนวดิ่งมาจากแรงลอยตัว/คลื่นและ launch torque แยกต่างหาก.

```text
F_hull_quadratic = -QuadraticDrag * |V_horizontal| * V_horizontal
F_lateral       = -LateralDrag * dot(V, HullRight) * HullRight
```

Water Buoyancy มี drag/damping ของมันอีกชุด; การจูน QuadraticDrag ไม่ได้ปิดแรงต้านอื่นทั้งหมด. Linear lateral term ใช้ทิศ HullRight ตาม graph ไม่ใช่คำรับรองว่าแรงทุกชนิด Z=0; ข้อกำหนดแนวราบโดยตรงใช้กับ propulsion และ tail drag.

แรงเฉื่อยเกิดจากมวลและ rigid-body velocity ที่ยังเหลือหลังปล่อย W. อย่าแก้ด้วยการตั้ง velocity=0, ล็อก Z/pitch หรือ anchor เรือ. ถ้าไหลสั้นเกิน ทดลองลด QuadraticDrag ทีละ 5-10% แล้ววัดเวลาจำลอง; ตรวจ drag ของ Buoyancy และ tail contact ร่วมด้วย.

DriveThrust ใน graph มี factor `DriveForce/220000` และ EventGraph คูณ carrier `220000` กลับ. จึง **ไม่จำเป็นต้องอยู่ 0..1** และไม่ใช่ throttle โดยตรง; อย่า clamp เป็น 1 เพราะจะเสียค่าจูนแรงขับ.

## 6. 110 km/h เป็น Soft Governor

ต่ำกว่า 105 km/h กำลัง factor=1. ช่วง 105..110 ใช้ smoothstep ลดเข้าหา 0.45. หลัง 110 factor ค่อย ๆ ลดเป็น 0 เมื่อถึง 116 km/h. Governor ลดเฉพาะ positive drive; ไม่ hard-clamp ความเร็ว rigid body.

```text
t = clamp((Speed - 105) / 5, 0, 1)
scale_105_110 = lerp(1, 0.45, t*t*(3-2*t))
scale_above_110 = 0.45 * clamp(1 - (Speed-110)/6, 0, 1)
```

111+ km/h จากแรงเฉื่อย/คลื่นยังเกิดได้ตามที่ต้องการ. เปลี่ยน target ต้องเปลี่ยน start ให้ต่ำกว่า target และรักษา VibrationStart ไม่เกิน target. ความเร็วสูงสุดจริงยังขึ้นกับแรงต้านและสภาพน้ำ ไม่ได้เท่ากับตัวเลข target เสมอ.

## 7. เลี้ยวระหว่างไหล Q + A/D

`W+A/D` ใช้ thrust ท้ายที่มีมุมเลี้ยว. ปล่อย W ยังมีทางเลี้ยวผ่านแรงต้านข้างของชุดท้าย ถ้าเรือไหลอยู่และชุดท้ายสัมผัสน้ำ.

`Q` ขอ trim ลง -10 องศา; `E` ขอ +14. `A` ขอ steering +18 และ `D` -18 สำหรับโมเดลหัว -X. ระบบ interpolate และ auto deployment ทำให้มุมจริงอาจไม่ตรงคำขอทันที. ตรวจ PropImmersion และ TrimDegrees จริง ไม่ดูแค่ปุ่ม.

```text
WetFactor = clamp(Immersion,0,1) * clamp((-TrimDegrees-3)/7,0,1)
Slip = dot(PointVelocity - WaterVelocity, TailSideHorizontal)
F_tail = -sign(Slip) * min(Coefficient * WetFactor * Slip², 150000) * TailSideHorizontal
```

จุดคำนวณความเร็วและออกแรงใช้ hub XY ที่ COM world Z เดียวกัน. แรงมี Z=0 และต้านการไหลข้าง ไม่สร้างพลังงานเอง. 150000 เป็น cap ใน implementation ยังไม่เป็น field ของ Handling.

Ocean/Lake ไม่ใช้ spline velocity metadata เป็นกระแสน้ำจริง. River ใช้เมื่อเปิด bApplyRiverForces; กระแสน้ำจริงจึงอาจสร้างแรงสัมพัทธ์แม้เรือไม่มี ground speed. ในน้ำเรียบไม่มีกระแส เรือหยุดแล้ว Q+A/D ต้องไม่ทำให้หมุนต่อเอง. ยก tail พ้นน้ำแล้วต้องไม่มีแรง tail steering เพิ่ม แต่ angular momentum เดิมยังเหลือได้.

## 8. รอบใบพัด Space และหัวกระชาก

เพลา interpolate เข้าหารอบเครื่อง * 0.25 * clutch. อัตราขึ้นประมาณ 2.86/s และลง 1.67/s ทำให้หมุนเฉื่อยหลังปล่อย W; มุมใบพัดสะสม RPM * 6 * DeltaSeconds.

`Space` คือปลดคลัตช์ **ไม่ใช่เบรกและไม่ล็อกตำแหน่ง**. W+Space ให้เครื่องเร่งแต่ shaft/thrust ลดลงตามการ interpolate; ตอน settled เคยอ่าน engine 6500 RPM, shaft 0 และ thrust 0. หลังปล่อย Space กลับส่งกำลัง; เรือที่ไหลอยู่ก่อนหน้ายังไหลได้. การกด Space ไม่ทำให้ shaft หยุดทันทีทุก frame.

Propeller auto deployment เป้าหมาย hub จมประมาณ 4 cm; trim คำนวณมีขอบเขต -40..+14 องศา. ค่านี้ไม่ใช่ทุ่นและไม่ย้ายเรือขึ้นตามผิวน้ำ. ความแม่นยำบนคลื่นสูงยังต้องรับรอง.

Launch torque เป็น one-shot ช่วงเร่งเดินหน้า มีคลัตช์/น้ำ/โหลดและต่ำกว่า 40 km/h; ยกเลิกเมื่อหมดเงื่อนไข ไม่เก็บ pulse ค้างแล้วกลับมากระชากตอนลงน้ำ. Torque ลดตั้งแต่หัวเงย -3 จนเป็นศูนย์ที่ -7 องศา; ไม่ล็อก pitch ที่ -7 และคลื่นยังดันเกินได้.

เครื่องสั่นเฉพาะภาพในช่วงออกตัวที่เข้าเงื่อนไขหรือความเร็วสูงมีโหลดเริ่ม 108 km/h. ไม่สั่นต่อเนื่องตอน idle/steady mid-speed/Space ปลดคลัตช์. การปรับ torque หรือ duration ต้องวัด pulse ใหม่; snapshot หลัง pulse จบไม่พิสูจน์ว่าหัวเงยพอดีแล้ว.

## 9. ทำ Handling แยกแต่ละรำ

1. Duplicate `DA_ThaiLongtail_Handling` เป็นชื่อเช่น `DA_Longtail_Race01_Handling` ในโฟลเดอร์เรือของตัวเอง. ชื่อนี้เป็นตัวอย่าง ยังไม่ได้สร้างให้ในรอบเอกสาร.
2. Assign asset ใหม่ให้ `HandlingProfile` บน Pawn/child Blueprint หรือ placed instance ของเรือลำนั้น. ตรวจ instance override ไม่ให้ทุกลำยังชี้ asset เดียว.
3. เริ่มจาก geometry และ pivot ที่เข้ากันได้กับ Pawn เดิม. การเปลี่ยนลำเรือจริงต้องแก้ collider/centroid จุดทุ่น และแกนหน้า/ท้ายด้วย ไม่ใช่เปลี่ยน Data Asset อย่างเดียว.
4. Save แล้วเริ่ม PIE ใหม่ อ่าน profile reference, mass, COM, actual pontoon radii, DriveForce และ drag ของ runtime Actor เพื่อยืนยันว่าโหลดถูก.
5. ถ้าไม่จำเป็น อย่าแก้ schema ของ BP_BoatHandlingData เพราะกระทบทุก profile. Fields ใหม่ต้องเพิ่ม validation/loader/fallback และทดสอบ.

Loader รับทั้งโปรไฟล์เมื่อทุก field ถูกต้องเท่านั้น. ตรวจ finite ด้วยขอบเขต ±1e9, มวล/รัศมี/DriveForce/start/fade/duration >0, drag/torque/vibration >=0, target > start, cruise scale 0..1 และ vibration <= target. โปรไฟล์ผิดทั้งชุดจะคงค่า Pawn fallback ไม่โหลดบางส่วน. Missing-profile path มี guard แต่ยังไม่ได้รับรอง runtime regression; negative-tail fallback เคยทดสอบจริงแล้ว. Fallback ไม่ใช่คำรับรองว่าค่าคลาส default ตรงตารางนี้ทุกครั้ง ต้องอ่าน Pawn ถ้าใช้ fallback.

## 10. วิธีจูนและทดสอบ

1. สำรอง Data Asset/Pawn/map ที่จะแก้ก่อน และจดค่าตั้งต้นพร้อมชื่อ profile/map.
2. เริ่มน้ำเรียบ ตรวจ idle draft/pitch/COM แล้วค่อยคลื่นเล็กและ stress map. ถ้าจมก่อนเร่งให้แก้มวล/ทุ่น/instance override ก่อน DriveForce.
3. เปลี่ยนค่าเดียวทีละ 5-10%; ปรับท้ายหนักด้วยตำแหน่งมวลที่สมเหตุผล ไม่ขยับ COM ไปตรงเครื่องทั้งก้อนและไม่ลด rear radius จนจม.
4. วัด W ออกตัว, ปล่อย W ไหล, Q+A/D ซ้าย/ขวา, ยก tail, S, W+Space และลงน้ำใหม่. บันทึก simulation time, speed แนวราบ, Z/pitch/yaw, hub water height, immersion, shaft/engine RPM และ clutch.
5. แยก water clipping ภาพจาก draft จริง; ถ่ายมุมข้าง/ในห้องเรือ/ใต้น้ำ. อย่าเพิ่มแรงลอยตัวเพียงเพื่อซ่อนภาพน้ำทะลุ.
6. ทดสอบอาการเดิมซ้ำ และให้ Astra ตรวจ graph/C++/หลักฐานก่อนประกาศรับรอง. Stop PIE, ปิด test override ให้ false/zero แล้ว Save.

QA ปัจจุบันมี `bUseTestInput`, `TestThrottle`, `TestSteeringDegrees`, trim/clutch/coast time. เริ่มแต่ละ run ด้วย world ใหม่; TestCoastAfterSeconds อิง world age ไม่ใช่ timer ตั้งแต่เริ่มวัด. DSL timer candidate ยังไม่ apply. JSON snapshots เก่าใช้ wall time จึงห้ามนำไปคำนวณ calibrated turn radius หรือ coast deceleration.

## 11. อาการที่ควรตรวจ

| อาการ | ตรวจตามลำดับ |
| --- | --- |
| ท้ายจมต่อเนื่อง | actual radii/instance override, total mass/COM, อยู่ใน WaterBody หรือไม่ |
| เร่งแล้วท้ายเหมือนถูกค้ำ | ไม่มีแรง prop world Z, จุดออกแรง COM world Z, ไม่มีทุ่นใบพัด |
| ไม่เลี้ยวตอนปล่อย W | ยังมี speed สัมพัทธ์ไหม, hub เปียกไหม, Q/trim/WetFactor, native plugin โหลดใหม่หรือยัง |
| หยุดแล้วหมุนต่อผิดปกติ | แยก angular momentum จาก force; Ocean current ต้องศูนย์, River current ตั้งใจเปิดไหม |
| จูนแล้วไม่เปลี่ยน | HandlingProfile ของ instance, Restart PIE, invalid profile warning/fallback |
| น้ำทับพื้น/ที่นั่ง | ตรวจ draft จริงแยกกับ render mask ที่ยังไม่ติดตั้ง |
| ความเร็วพุ่งตอนตกจากน้ำ | ตรวจ coverage/immersion และขอบ WaterBody; ไม่ถือเป็น top-speed test |

## 12. สิ่งที่ยังไม่ผ่าน Acceptance

มี native report 4 tests ผ่านใน checkpoint ก่อนหน้า และ bounded coast snapshots ซ้าย/ขวา/raised-tail. ยังไม่รับรอง timed inertia, launch bow-rise, reverse/clutch ทุกกรณี, shoreline/exclusion/River, rough-water handling, mask น้ำ และ high-wave racing. ดู [STATUS](../STATUS.md), [หลักฐาน runtime](../Work/2026-09-30-water-current-regression.json) และ [แผนที่เหลือ](../Plans/2026-09-30-boat-handling-waves.md).

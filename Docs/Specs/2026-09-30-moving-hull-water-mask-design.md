# สเปก Moving Hull Water Mask

วันที่ 2026-09-30 (Asia/Bangkok)

สถานะ: ผู้ใช้อนุมัติแนวทาง coordinate-local mask แล้ว และแจ้งให้พักการตรวจเอกสาร ลงมือทำแล้วค่อยอัปเดต MD. ไม่ต้องถาม written-spec/plan approval ซ้ำ. ตอนนี้มี reference math, geometry survey และ MPC ที่ยังปิดไว้ แต่ยังไม่มีระบบ mask ที่ติดตั้งในเกม. ลำดับงานจริงดู [แผนลงมือทำ](../Plans/2026-09-30-moving-hull-water-mask.md).

## เป้าหมายและขอบเขต

แก้น้ำภายนอกที่วาดผ่านพื้น/ที่นั่งในห้องเรือเมื่อเจอคลื่น โดยซ่อนเฉพาะผิวน้ำที่อยู่ในปริมาตรแห้งภายในลำเรือใต้ gunwale. ปริมาตรติดตามตำแหน่ง yaw/pitch/roll ของลำเรือ ไม่ติดตามกล้องหรือใบพัด. น้ำข้างเรือ น้ำใต้ท้องเรือ wake/spray และผิวคลื่นที่สูงพ้นขอบเรือต้องยังอยู่.

ไม่ใช้วิธีเพิ่ม buoyancy เพื่อกลบ rendering, ล็อก Z/pitch, เพิ่มทุ่นใบพัด หรือลดความยาวเพลา. คง shaft pivot-to-hub 246 cm และพฤติกรรม coast/soft governor เดิม. ไม่สร้าง flooding, น้ำขัง/ระบายในเรือ, cavitation, multiplayer replication หรือระบบเรือจมที่มีปริมาตรน้ำภายในในงานนี้.

ข้อจำกัดที่ต้องบอกตรง ๆ: mask นี้ไม่ใช่การจำลองผนังกันน้ำหรืออากาศติดอยู่ใต้น้ำ. เมื่อคลื่นล้นขอบ น้ำส่วนเหนือขอบยังแสดง แต่ไม่มีการเก็บน้ำที่ไหลเข้าห้องเรือไว้หลังคลื่นผ่าน. การทดสอบเรือที่จมทั้งลำเป็นภาพทดสอบ ไม่ใช่ acceptance ของ flooding gameplay.

## ข้อเท็จจริงจากการตรวจของเดิม

- Pawn `/Game/Boats/ThaiLongtail/Blueprints/BP_LongtailPhysicsPawn` ใช้ native water query และ hull-only buoyancy แล้ว; ไม่มี mask ภายในเรือ.
- Ocean material chain ที่ตรวจไว้คือ `/Water/Materials/WaterSurface/Water_Material_Ocean` -> `Water_Material_Inst` -> `Water_Material`.
- Base ใช้ Masked / SingleLayerWater และ Material Attributes. ต่อ MP_OpacityMask โดยตรงอย่างเดียวไม่พอ; ต้อง override OpacityMask ใน attribute chain โดยรักษา attributes อื่น.
- `ClipDynamicBounds` ของ Water ใช้ clipping ขอบเขต XY ของน้ำ ไม่ใช่ tapered hull volume ที่ติดตามเรือ.
- collider แบบ convex ใช้ฟิสิกส์ ไม่ได้แทนรูปร่างโพรงภายในได้แม่นยำ; profile mask ต้องวัดจาก visual interior ไม่ใช่ bounds ของทั้ง Actor ที่รวมเครื่องและเพลา.

## สถาปัตยกรรม

ใช้ runtime subsystem ต่อ World สำหรับจัด slot และ component ต่อเรือสำหรับส่ง transform/profile. Geometry profile เป็น Data Asset แยกจาก Handling เพราะค่ารูปทรงไม่ควรเปลี่ยนพร้อมแรงขับ/มวล. เก็บใน plugin เดิม `BoatlRacingPhysics` เพื่อไม่สร้าง runtime module ใหม่; component/subsystem ไม่มีการเรียก AddForce, SetVelocity หรือแก้ Buoyancy.

Asset/โค้ดที่ต้องใช้ (ยกเว้น MPC และ reference helper รายการอื่นยังไม่มี):

| Asset/โค้ด | หน้าที่ |
| --- | --- |
| `/Game/Boats/ThaiLongtail/WaterMask/DA_ThaiLongtail_DryHull` | profile ปริมาตรภายในใน boat-local cm |
| `/Game/Water/Materials/MPC_BoatInteriorMasks` | สร้าง/เซฟแล้ว: 416 vectors + 2 scalars; ยังปิดและไม่ผูกกับ water shader |
| `/Game/Water/Materials/MF_BoatInteriorMask` | ประเมินปริมาตรและให้ factor 0/1 |
| `/Game/Water/Materials/BoatInterior/` | สำเนา parent chain เฉพาะที่ต้องแก้และ Ocean instance ของโปรเจกต์ |
| `BoatInteriorMaskComponent` | register/unregister และอัปเดต transform หลัง physics |
| `BoatInteriorMaskSubsystem` | จัด slot ต่อ World, reset ที่ PIE/end world และส่งค่า MPC |
| native containment helper/tests | มี standalone reference/tests และ comment ภาษาไทย; ยังไม่ตรวจ shader parity |

คัดลอก base และ instance chain ที่จำเป็นเข้าพื้นที่ `/Game` และ reparent ให้สำเนาใช้สำเนา base จริง. รักษา existing parameter overrides/static switches; สำรอง material references ของ WaterBody ทั้งสาม map ก่อนเปลี่ยน. ห้ามแก้ `/Water` engine/plugin assets หรือเพียงสร้าง instance ใต้ parent เดิมแล้วอ้างว่ามี mask.

## รูปร่างปริมาตรแห้ง

reference core รองรับ profile สมมาตรซ้าย/ขวา 8 stations เรียง X จากหัว (-X) ถึงท้าย (+X). แต่ละ station เก็บ X, CenterY, FloorZ, GunwaleZ, HalfWidthAtFloor และ HalfWidthAtGunwale หน่วย cm พร้อม width curve สูงสุด 8 knots `(normalizedHeight, halfWidth)`. knot แรก/สุดท้ายอยู่ที่ 0/1 และตรงกับความกว้างพื้น/ขอบ. ภายในช่วง X ให้ interpolate floor/rim/centerY; ประเมิน width curve ของสอง stations ที่ normalizedHeight เดียวกันแล้ว interpolate ความกว้างตาม X.

เหตุผลที่แก้จากสเปกเดิม: GLB จริงที่ X=30 cm มี single-width-chord ล้ำผนังสูงสุด 3.5367 cm. จึงไม่ใช้เส้น floor-to-rim เส้นเดียวกับผนังโค้ง. โหมด linear ยังอยู่สำหรับ simple fixture/legacy profile แต่ไม่ถือว่าเหมาะกับเรือจริง. curved fixture ใน unit test มาจากหน้าตัดเดียว ไม่ใช่ fitted profile ทั้งลำ.

```text
station span: X_i <= local.X < X_(i+1), รวมปลายสุดท้ายที่ X_max
t = (local.X - X_i) / (X_(i+1) - X_i)
floor, rim, centerY = lerp(station_i, station_(i+1), t)
zRatio = (local.Z - floor) / (rim - floor)
widthA = piecewiseLinearWidth(station_i.heightKnots, zRatio)
widthB = piecewiseLinearWidth(station_(i+1).heightKnots, zRatio)
halfWidth = lerp(widthA, widthB, t)
inside = floor <= local.Z < rim && abs(local.Y-centerY) <= halfWidth
```

วัด stations จากพื้น/ด้านในผนัง/ขอบเรือของ visual mesh จริง โดยรวมช่วงหัวแหลมและ transom; ไม่ใช้ค่า hull length/width จากภาพโดยเดา. เว้นผนังด้านข้างเข้าไป 2 cm และเว้นเหนือพื้น 1 cm เพื่อไม่ตัดน้ำภายนอก/ใต้ท้อง. rim อยู่ไม่สูงกว่าขอบจริง. ลดความกว้างปลายหัวตาม geometry ห้ามใช้ box กว้างเท่ากันทั้งลำ.

ก่อนส่ง profile เข้า material ต้องตรวจ X เพิ่มจริง, finite, rim>floor, ความกว้างไม่ติดลบและปริมาตรไม่ว่าง. Invalid profile หรือ transform ให้ slot inactive พร้อม warning ครั้งเดียว. หาก 8 stations ไม่สามารถอยู่ภายในโพรงและครอบคลุมพื้นที่แห้งโดยเหลือขอบคลาดเกิน 2 cm ต้องหยุด acceptance และแก้ profile representation ผ่าน review ไม่ขยาย mask ให้ตัดน้ำด้านนอกเพื่อให้ภาพดูผ่าน.

ผล survey ปัจจุบัน: 532 X sections ในช่วง -230..301 cm และแปด height samples ต่อ section จาก triangles ของ `Hull | teak inner liner`. นี่ยังไม่รวมการรับรอง floor plank/transom, ส่วนหัวที่ปิดด้วย deck, หรือ continuous clearance ระหว่างจุด. ตัววัดสมมติ liner ชิ้นเดียวและโพรงอยู่รอบ centerline; ตรวจ paired oriented edges/vertex connectivity ไม่ใช่ general solid validator. ผิว coplanar ให้ผล ambiguous แล้วปฏิเสธ; rim ใช้ขอบฝั่งที่ต่ำกว่า. ห้ามนำ survey ไปอ้างว่า fitted dry volume ผ่านแล้ว.

รองรับ positive scale ของ frame โดยแปลง world-to-local ด้วย inverse transform เดียวกับ geometry. Reject zero/negative scale และ transform ไม่ finite. ผูก component กับ frame ของลำเรือที่ให้ boat-local coordinates ตรงกับ mesh ไม่ใช่ engine pivot. UI/debug แสดง profile wire volume สำหรับวัด ไม่เพิ่ม collision หรือ distance-field proxy.

## Material และพิกัด

ในแต่ละ slot ส่ง origin, inverse-transform rows และ station data ไป MPC. world position ที่ material ใช้ต้องเป็นตำแหน่งผิวน้ำ **หลัง wave displacement** ในพิกัดเดียวกับข้อมูล CPU เพื่อให้คลื่นที่สูงพ้น gunwaleไม่ถูกตัดด้วยตำแหน่งระนาบก่อนคลื่น. ตำแหน่ง origin/rows ต้องอัปเดตจาก frame หลัง physics tick เพื่อหลีกเลี่ยง lag เมื่อหมุนและเคลื่อนเร็ว.

ก่อนสร้าง graph ตรวจตำแหน่ง wave/WPO ของ base จริงและเลือก AbsoluteWorldPosition ที่รวม material offsets; ห้ามใช้ non-displaced plane Z. ถ้า Water base ไม่ให้ displaced position ที่สอดคล้องกับคลื่น ต้องหยุดและรายงานข้อจำกัด ไม่เปลี่ยนเป็น flat-plane mask เงียบ ๆ. ในการทดสอบ world-origin shift ต้อง reset/ส่ง transform ใหม่จาก World เดียวกัน โดยใช้ position convention เดียวทั้ง material และ CPU.

```text
dryInside = max(inside(active_slot_0), ..., inside(active_slot_7))
waterKeep = 1 - dryInside
finalOpacityMask = existingOpacityMask * waterKeep
```

ใช้ SetMaterialAttributes เพื่อแก้เฉพาะ OpacityMask ก่อนส่ง MP_MaterialAttributes. ไม่ override color, normal, water absorption/scattering, WPO หรือ opacity อย่างอื่น. Preserve masked clip threshold และ shading model. สร้าง reusable material function และ expose enable/debug scalar ของสำเนาเพื่อ A/B ทดสอบ/rollback; ไม่เพิ่ม static switch ทุกลำหรือ copy shader ทุก frame.

Water mesh LOD/far material และ underwater rendering ต้องตรวจ: การผูก Ocean instance ไม่พิสูจน์ว่าทุก water path ใช้ base เดียวกัน. ใช้ project-owned masked chain กับ active water surface paths ที่เกี่ยวข้อง; หาก path ใดแก้ไม่ได้ให้บันทึกและไม่ผ่านภาพ acceptance ของ path นั้น. Niagara ไม่ใช้ mask นี้.

## เรือหลายลำและวงจรชีวิต

รองรับพร้อมกัน 8 slots สำหรับต้นแบบนี้ ไม่ใช่คำรับรองจำนวนผู้เล่นของเกมสุดท้าย. กำหนด owner ต่อ slot, ไม่เลือก slot จากลำดับ Tick และไม่ overwrite เรืออื่น. register ตอน component พร้อม/BeginPlay; release ที่ EndPlay/destruction. Clear active flag ก่อนเขียนข้อมูลชุดใหม่ แล้ว enable เมื่อครบ. ข้อมูล geometry ส่งเมื่อ register/profile เปลี่ยน; transform ส่งต่อ tick ไม่ upload geometry ซ้ำ.

ถ้าเต็ม เรือเกิน 8 ลำคงน้ำตามเดิมและเตือนครั้งเดียว ไม่มี mask ผิดลำ. เมื่อ owner ถูกลบคืน slot; reuse ต้องล้างข้อมูลเก่า. เมื่อ Stop PIE/เปลี่ยน World เคลียร์ slots ทั้งหมด ไม่เหลือรูน้ำค้างใน Editor. MPC instance เป็น per-World จึงห้ามจับ singleton ที่ข้าม PIE World.

ไม่มี material mutation/disk save ใน gameplay tick. ไม่ tick เมื่อ component inactive. ตรวจ non-finite geometry/transforms ก่อน shader; warning ไม่ spam ต่อ frame. Native logicละเอียดต้องมี comment ภาษาไทย.

การกลับมาใช้งานต้องไม่พึ่ง tick ที่ถูกปิด: component มี explicit `SetMaskEnabled` และ `SetDryHullProfile` ที่ validate/register หรือ release slot ทันทีตาม readiness. BeginPlay/registration เรียกเส้นทางเดียวกัน. Disable คืน slot; enable หรือเปลี่ยน invalid profile เป็น valid ขอ slot ใหม่แล้วส่งข้อมูลครบก่อนเปิด active. หากเปิดเมื่อ slots เต็มต้องคง fail-visible จนมีการลอง register ใหม่แบบ explicit ไม่แย่ง owner และไม่อ้างว่าฟื้นเองโดยไม่มี trigger.

## การทดสอบและเกณฑ์ยอมรับ

| กลุ่ม | เกณฑ์ |
| --- | --- |
| Reference math | unit tests: ภายใน/นอก side/floor/rim/bow/transom, station seam, transform yaw/pitch/roll/scale, invalid profile และ active mask รวมหลายลำ |
| Shader | compile material ผ่าน; existing attributes/คลื่น/สี/opacity เดิมยังอยู่; CPU reference และภาพ debug ให้ผลตรงกันที่จุดตัวอย่าง |
| ภาพ baseline | เปรียบเทียบ mask off/on ใน flat และ small waves จากมุมข้าง cockpit bow และใต้น้ำ; น้ำไม่ผ่านพื้น/ที่นั่งใน cavity และไม่หายด้านนอก |
| คลื่นสูง | crest สูงพ้น rim ยังแสดง; ไม่เพิ่มแรงลอยตัวเพื่อซ่อนการจม และไม่ตีความเป็น flooding simulation |
| เคลื่อนที่ | W/S/Q/A/D/Space, coasting และยก/ลง tail: mask ติด hull ไม่มีรูน้ำค้างหรือ lag ข้ามขอบที่มองเห็น |
| หลายลำ | อย่างน้อยสองลำคนละ transform/profile ใกล้กัน, ลบ/เกิดใหม่, disable -> re-enable, invalid -> repaired profile, เต็ม 8 แล้วลำที่ 9/ลอง register หลังคืน slot, Stop/Start PIE, เปลี่ยน map และ world-origin shift |
| ฟิสิกส์ไม่เปลี่ยน | คู่ทดสอบ settings/input/เวลา simulation เดียวกัน mask on/off; component ไม่ออกแรง ค่า mass/COM/pontoons และ native force state ต้องเหมือนเดิม; ใช้ tolerance ใน telemetry สำหรับ nondeterminism ของ Chaos ไม่บังคับ trajectory bit-identical |
| Performance | เก็บ hardware/render settings/resolution จริง, warm shader ก่อนวัด; A/B water GPU pass เป้าหมายเพิ่มไม่เกิน 0.5 ms ที่ 1920x1080 และ CPU update รวม 8 ลำไม่เกิน 0.1 ms; ยังไม่มีผลวัดและห้ามอ้างว่าผ่านล่วงหน้า |
| กู้คืน | stop PIE ก่อน save, save project-owned assets/map references; toggle off กลับ water เดิมได้; `/Game/boat` และ source `/Water` ไม่ถูกแก้ |

ภาพต้องเก็บตำแหน่งกล้อง/สถานะคลื่น/เวลา simulation ไม่ใช้แค่ snapshot หนึ่งภาพเป็นข้อพิสูจน์ทุกสภาพ. Astra ตรวจ math, slot lifecycle, material flow และหลักฐานภาพก่อนรับรอง. ทำ native RED/GREEN ที่เพิ่มจริง ไม่ใช้รายงาน 4 tests เดิมเป็นหลักฐาน mask.

## ลำดับส่งต่อ

1. ทำต่อจาก [execution checkpoint](../Plans/2026-09-30-moving-hull-water-mask.md); ผู้ใช้ให้เลื่อนการตรวจเอกสารไปหลังทำแล้ว.
2. Fit profile และตรวจ clearance ของปริมาตรจริง; ใช้ reference core/tests ที่มีแล้ว ไม่ใช้ curved fixture หน้าตัดเดียวเป็น asset ทั้งลำ.
3. ต่อ runtime slot lifecycle และวัสดุสำเนาในโปรเจกต์ หลัง MCP กลับมาและตรวจ live state แล้ว. Astra ตรวจทุก pass; คง rollback และการทดสอบภาพ/performance.
4. อัปเดต STATUS/HANDOFF/คู่มือตามหลักฐานจริง ไม่ย้ายรายการเสนอไปส่วนใช้งานแล้วก่อนเวลา.

คู่มือ: [PROJECT_MAP](../Guides/PROJECT_MAP.md), [HANDLING_GUIDE](../Guides/HANDLING_GUIDE.md). งานแม่: [handling/waves plan](../Plans/2026-09-30-boat-handling-waves.md). โปรเจกต์ไม่มี Git repository จึงใช้เอกสารและ package backups; ไม่ได้สร้าง commit.

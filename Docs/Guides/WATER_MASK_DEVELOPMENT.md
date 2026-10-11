# คู่มือพัฒนา Water Mask

อัปเดต 2026-09-30. root ของ path ด้านล่างคือ `A:\Project\Unreal Engine 5\BoatlRacing`.

## สถานะจริง

มี reference C++ และเครื่องมือวัด geometry แล้ว แต่ยังไม่มี shader mask / component / subsystem / profile Data Asset ที่ติดตั้งในเกม. ปัญหาน้ำวาดทะลุเรือยังไม่ถือว่าแก้แล้ว. ไม่เปลี่ยน Handling มวล COM แรงขับ ทุ่น หรือความยาวแกนในงานรอบนี้.

สร้าง/เซฟ `/Game/Water/Materials/MPC_BoatInteriorMasks` แล้ว: 416 vectors + 2 scalars, ปิดทั้งหมดเป็น default และยังไม่ผูกกับ material/Pawn. [MCP readback](../Work/2026-09-30-water-mask-mpc-readback.json) ตรวจชื่อ ค่า default และ unique IDs ครบ. เครื่องมือ MCP กลับมาและ live `IsPIERunning=false` ผ่าน โดยไม่ปิด Editor/ทิ้งงาน.

เก็บ [parameter payload ที่อ่านกลับจริง](../Work/2026-09-30-water-mask-mpc-parameters.json) พร้อม IDs ไว้สำหรับ audit; ไม่ใช่ไฟล์สั่ง reset asset. ถ้าแก้ layout ภายหลังต้องอ่านกลับใหม่และตรวจ references ก่อน ไม่ apply JSON นี้ทับงานปัจจุบันโดยไม่ตรวจ.

## สัญญาข้อมูล MPC

ชื่อ prefix `BoatMask_{slot}_`, slot 0..7. ทุก vector ใช้ช่อง R/G/B/A เก็บตัวเลข ไม่ใช่สีที่ต้อง clamp เป็น 0..1. 52 vectors ต่อ slot: frame 4 + 8 stations x 6.

| ชื่อหลัง prefix | R / G / B / A |
| --- | --- |
| `Origin` | World X / Y / Z / active (0 หรือ 1) |
| `InverseX`, `InverseY`, `InverseZ` | inverse-transform row X / Y / Z / reserved 0 |
| `S{station}_Bounds` | local X / CenterY / FloorZ / RimZ |
| `S{station}_Widths` | FloorHalfWidth / RimHalfWidth / HeightKnotCount / reserved 0 |
| `S{station}_K{pair}` | height[2*pair] / width[2*pair] / height[2*pair+1] / width[2*pair+1] |

station 0..7; pair 0..3. height fraction อยู่ใน 0..1, coordinate/width เป็น cm. knot count เป็นจำนวนเต็ม 0 (legacy linear) หรือ 2..8; zero-fill unused pairs. global scalars `BoatMask_Enable` และ `BoatMask_Debug` default 0. inverse rows default identity; Origin.active default 0; geometry defaults 0 จึงไม่ใช่ valid profile.

สัญญานี้เป็น layout ที่เตรียมไว้ ไม่ใช่ uploader/shader ที่ใช้งานแล้ว. Runtime ต้องปิด active ก่อนเขียนค่าทั้งชุด ตรวจ valid profile/frame/scale และเปิดเฉพาะเมื่อสำเร็จ. ห้ามตั้ง enable/active จากการเดา geometry; มี runtime tests/shader parity ที่ต้องทำต่อ.

## ไฟล์ไหนทำอะไร

| ไฟล์ | หน้าที่ |
| --- | --- |
| `Plugins/BoatlRacingPhysics/Source/BoatlRacingPhysics/Private/BoatInteriorMaskMath.h` | containment, width curves, inverse frame และ slot handles; ยังไม่ถูกเรียกใน UE runtime |
| `Tools/Tests/boat_interior_mask_math_test.cpp` | fixture ภายใน/นอกโพรง ขอบบน transform ตัวเลขผิด และ owner/registry/reuse |
| `Tools/Tests/run_boat_interior_mask_tests.ps1` | compile/run fixture ด้วย MSVC x64; สร้าง log/result ใน Saved |
| `Tools/Tests/measure_boat_mask_section.ps1` | อ่าน GLB แบบ structured, ตรวจ ancestor และวัดหน้าตัด X; `-ExportMesh` ส่ง vertices/triangles ที่ผ่าน bounds checks |
| `Tools/Tests/boat_mask_geometry_test.ps1` | สร้าง fixture ใน Saved เพื่อตรวจการปฏิเสธ transformed ancestor และ reference/offset ผิด |
| `Tools/Tests/BoatMaskMesh.h` | ray intersections กับ triangles; ตรวจ paired oriented edges และ vertex connectivity ของ liner |
| `Tools/Tests/boat_mask_mesh_test.cpp` | synthetic fixtures และ survey GLB จริง 532 sections x 8 heights |
| `Tools/Tests/run_boat_mask_mesh_tests.ps1` | export mesh, compile/run survey แล้วเก็บ source hash/ผลตรวจ |

## วิธีรันทดสอบ

ใช้ PowerShell 7 จาก root โปรเจกต์ และติดตั้ง MSVC x64 Build Tools. Runner หา toolchain ผ่าน vswhere และใช้ `/W4 /WX /utf-8`.

```powershell
& './Tools/Tests/run_boat_interior_mask_tests.ps1'
& './Tools/Tests/boat_mask_geometry_test.ps1'
& './Tools/Tests/run_boat_mask_mesh_tests.ps1'
& './Tools/Tests/measure_boat_mask_section.ps1' -SectionXcm 30
```

หาก exit ไม่เป็น 0 หรือไม่มี summary ให้ถือว่าทดสอบไม่ผ่าน. คำสั่งแต่ละบรรทัดเป็นการรันแยก ไม่ต้องปิด Unreal สำหรับ standalone tests. สคริปต์สร้างเฉพาะ report/fixture/binary ใน Saved ไม่เขียน Unreal assets.

## รายงาน

โฟลเดอร์: `Saved/Automation/WaterMaskMath/`.

| รายงาน | สิ่งที่พิสูจน์ |
| --- | --- |
| `result.json`, `green.log`, `compile.log` | reference core ล่าสุด 121 checks / 0 failures |
| `mesh-result.json`, `mesh-test.log`, `mesh-compile.log` | survey/fixture ล่าสุด 4,279 checks / 0 failures |
| `geometry-section.json` | actual vertex section X=30: single-width-chord ล้ำผนัง 3.5367 cm |
| `hull-survey.json` | ray survey liner ในช่วง X=-230..301 cm ทีละ 1 cm และแปดระดับความสูง |
| `liner-mesh.txt` | input triangles ใน boat-local cm ให้ standalone survey; ไม่ใช่ UE mesh/profile asset |
| `*.glb`, `*.obj`, `*.exe` | generated fixtures/build artifacts; ไม่ใช่เรือที่ต้อง import |

ต้นทาง `SourceAssets/ThaiLongtail/thai_racing_longtail_runtime_2k.glb`, SHA256 `BD9B22D720481394AD8D19A79D7B05FCC4B443AE4C5C22D49771F35DDB561ED4`. GLB Y-up แปลงเป็น boat X=X*100, Y=-Z*100, Z=Y*100. Tool ปฏิเสธ node/ancestor transform ที่ยังไม่รองรับ ไม่สมมติว่า local mesh เป็น boat coordinates หาก parent เปลี่ยน.

## ข้อจำกัดที่ห้ามข้าม

- `hull-survey` วัดเฉพาะ `Hull | teak inner liner`. ยังต้องตรวจพื้นไม้จริง transom และช่วงที่ nose deck ปิด ไม่ใช่ bounds ทั้ง Actor.
- width คือผนังคู่ที่ใกล้ centerline ใน known centered liner. ผิว coplanar ให้ผล ambiguous แล้วปฏิเสธ; ขอบบนใช้ฝั่งที่ต่ำกว่า. paired hits ไม่ได้พิสูจน์ air/solid classification ทั่วไป.
- topology check ตรวจ edge pairing/orientation และ vertex connectivity เท่านั้น ไม่รับรอง manifold ทุกชนิด, triangle area, self-intersection หรือ shell ที่แตะกันแค่ vertex. ไม่ใช้เป็น general mesh-validity gate.
- 1 cm X grid และแปด heights ยังพลาด feature แคบได้. ผลทดสอบไม่พิสูจน์ continuous clearance ของ profile ที่ interpolate หรือ shader parity.
- curved unit fixture คัดจากหนึ่งหน้าตัดแล้วทำซ้ำทุก stationเพื่อทดสอบ math ไม่ใช่รูปร่างเรือทั้งลำ. ห้ามนำไปเป็น `DA_ThaiLongtail_DryHull`.
- MSVC standalone ไม่ใช่ Unreal Automation, ไม่ใช่ native DLL reload และไม่ใช่ภาพ mask-on/off ใน PIE. รายงาน physics เดิม 4 native tests อยู่คนละโฟลเดอร์และไม่ใช้แทน mask tests.

ขั้นถัดไปดู [execution plan](../Plans/2026-09-30-moving-hull-water-mask.md); การจูนเรือแต่ละรำยังใช้ [HANDLING_GUIDE](HANDLING_GUIDE.md) ไม่ใช่ geometry mask profile.

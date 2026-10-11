# โฟมสะสม (Girardot part 2) ต่อเข้าวัสดุน้ำได้แล้ว — 2026-10-02

ทดสอบบน `M_WaterSmallWavesTest` อย่างเดียว PIE หยุดแล้ว test override เป็น false/0

## ชิ้นที่ขาดอยู่: วัสดุน้ำอ่าน RT ที่สร้างตอนรันไทม์ไม่ได้

แก้โดย **ไม่สร้าง RT ตอนรันไทม์** — ทำเป็น asset ไปเลย สองตัว duplicate มาจาก
`/Water/FluidSimulation/Textures/RT_A` แล้วตั้งเป็น 1024² `RTF_R16f`:

- `/Game/Water/Materials/BoatContact/TR_BoatFoam` — โฟมที่สะสม
- `/Game/Water/Materials/BoatContact/TR_BoatFoamBuffer` — บัฟเฟอร์ ping-pong

`SetupFoamCapture` เลยเหลือแค่ชี้ตัวแปรไปที่ asset สองตัวนี้ + `ClearRenderTarget2D`
แทน `CreateRenderTarget2D` ทำให้วัสดุอ้างอิงตรงๆ ได้ ไม่ต้องไปยุ่งกับ
`GetWaterMaterialInstance` หรือ MID ของ water body เลย

> ponytail: RT เป็น asset ตัวเดียวร่วมกันทั้งเกม — เรือลำเดียวพอ ถ้ามีหลายลำ
> ต้องกลับไปทาง MID

`M_WaterBoatContact` `MaterialExpressionCustom_3` เพิ่มสองอินพุต `FoamRT`
(TextureObjectParameter "BoatFoamRT" ชี้ที่ `TR_BoatFoam`) และ `FoamFrame`
(CollectionParameter บน `MPC_BoatContactFrame`) แล้วผสม:

```hlsl
float2 fuv = (World.xy - FoamFrame.rg) / max(FoamFrame.b, 1.0);
float inside = (fuv.x > 0 && fuv.x < 1 && fuv.y > 0 && fuv.y < 1) ? 1 : 0;
float trail = Texture2DSample(FoamRT, FoamRTSampler, fuv).r * inside;
trail = saturate(trail * 1.6) * grain * 0.82;
return max(live, trail);
```

`grain` คือเทกซ์เจอร์โฟมเดิมที่แยกออกมาเป็นตัวแปร ใช้ร่วมกันทั้งโฟมแบบ
amplitude และโฟมสะสม ลายเลยเป็นเนื้อเดียวกัน

## ทำไมโฟมเป็นเหลี่ยม — สองสาเหตุ แก้แล้วทั้งคู่

**1. `step()` ตัดขอบแบบแข็งใน `M_BoatFoamComposite`**

```hlsl
rim *= step(-245.0, p.x) * (1.0 - step(315.0, p.x));   // เดิม
```

ทุกเฟรมปั๊มสี่เหลี่ยมที่มีขอบคมตรงหัวกับท้ายลงไปใน RT พอเรือเคลื่อน ขอบคมนั้น
ก็ค้างอยู่เป็นฟันเลื่อย เพราะ blur 5-tap รัศมี 1.8 texel ลบไม่ทัน เปลี่ยนเป็น

```hlsl
rim *= smoothstep(-305.0, -205.0, p.x) * (1.0 - smoothstep(255.0, 375.0, p.x));
float added = rim * rim * Birth;
```

**2. RT เป็น `TA_Wrap`** — มาจาก `RT_A` ที่ duplicate มา เวลา transport shift ดัน
UV เลย 0-1 โฟมจะวาร์ปไปโผล่อีกฝั่งเป็นแถบตรง ตั้งเป็น `TA_Clamp` + `TF_Bilinear`
ทั้งสอง RT

พร้อมกันนั้น blur 5-tap → **9-tap** (มุมด้วย) และ `Diffusion` 0.0018 → **0.0032**
box mask เริ่ม fade ที่ 0.40 แทน 0.42

ผล: thumbnail ของ `TR_BoatFoam` จากฟันเลื่อยเป็นแถบเรียบสองเส้นตามแนวกราบเรือ
ที่ค่อยๆ จางท้ายเรือ ในเกมได้ทางโฟมขาวยาวต่อเนื่องขอบนุ่ม

## ที่เจอระหว่างทางและยังไม่ได้แก้

**เรือจมน้ำบนแมพคลื่น** วัดที่ 108 km/h: hull Z แกว่ง 325-409 ส่วนผิวน้ำแกว่ง
370-447 — ตัวเรืออยู่ **ต่ำกว่าผิวน้ำ 10-60 ซม.** แทบตลอด เห็นแต่เครื่องกับหัวเรือ
`PropImmersion` กระพริบ 0/1 ตาม คือผลของ rear pontoon radius 53 ที่
`handling-pass.md` บันทึกไว้แล้วว่าเหลือ reserve buoyancy 101% ตอนนี้ยืนยันแล้วว่า
น้อยไปจริงเมื่อมีคลื่น เป็นการตัดสินใจเรื่องดีไซน์ ไม่ได้แก้เอง

**`M_WaterPhysicsTest` เรือลอยเหนือน้ำ** จับภาพได้ชัด เงาทอดบนผิวน้ำ ไม่มีคลื่นท้ายเลย
`PropImmersion` = 0 ตลอด คนละอาการกับแมพคลื่น

## กับดักเครื่องมือ

- `CaptureEditorImage` ถ่ายทั้งหน้าจอ หน้าต่าง asset editor ที่ลอยอยู่จะบัง
  viewport ต้องย่อหน้าต่างนั้นก่อน (ไม่มี MCP tool ปิด ใช้ `ShowWindow` ผ่าน
  PowerShell)
- `OpenEditorForAsset` กับไฟล์แมพ **หยุด PIE** และสลับแมพกลับ
- `load_level` ไม่ยอมโหลดถ้าแมพปลายทางยัง dirty ต้อง `save_assets` ก่อน
- `CaptureAssetImage` บน render target ใช้ดูเนื้อ RT ได้ตรงๆ ดีกว่าเดาจากภาพในเกม

## รอบสอง — ขอบเหลี่ยมที่เหลือ

หลังแก้ `step()` กับ `TA_Wrap` แล้วยังเหลือขอบอีกจุด และเป็นจุดที่เห็นชัดที่สุด

**ขอบหน้าต่าง RT ถูกตัดแบบ binary** ใน `M_WaterBoatContact`:

```hlsl
float inside = (fuv.x > 0 && fuv.x < 1 && fuv.y > 0 && fuv.y < 1) ? 1 : 0;   // เดิม
```

นี่คือการวาดสี่เหลี่ยมลงบนผิวน้ำตรงๆ โฟมหายวับตรงขอบหน้าต่าง และหน้าต่างเลื่อน
ตามเรือ สี่เหลี่ยมนั้นเลยวิ่งตามไปด้วย เปลี่ยนเป็น fade:

```hlsl
float2 we = abs(fuv - 0.5);
float window = 1.0 - smoothstep(0.34, 0.49, max(we.x, we.y));
float trail = Texture2DSample(FoamRT, FoamRTSampler, saturate(fuv)).r * window;
```

**หน้าต่างกว้างแค่ 10 ม.** ซึ่งที่ 110 km/h คือหางน้ำแค่ 0.33 วินาที ขอบเลยมา
จ่ออยู่ติดท้ายเรือตลอดเวลา ขยายเป็น **4096 ซม. (40 ม.)** บน RT 1024² เท่าเดิม =
4 ซม./texel ยังละเอียดกว่าตัว fluid sim ที่ 8 ซม./cell อยู่เท่าตัว

`UpdateFoamCapture` snap จุดกำเนิดเป็นกริด **4 ซม.** แทน 1 ซม. (`Floor(x/4)*4 - 2048`)
เพื่อให้ยังตรง texel พอดี — ถ้า snap ไม่ตรง texel ภาพจะสั่นตอนเรือเคลื่อน
`FoamShift` หารด้วย 4096 ตาม ทำให้ค่า shift เป็นจำนวนเต็ม texel เป๊ะ ไม่มี resample

ปรับตามสเกลใหม่: `Diffusion` 0.0032 → **0.0020** (0.0032 UV ที่ 4 ซม./texel คือเบลอ
13 ซม./เฟรม เละเกิน) และ box mask ในตัว composite ขยับเป็น 0.44-0.50 ให้ fade ที่
มองเห็นมาจากฝั่งวัสดุน้ำอย่างเดียว ไม่ซ้อนกันเป็นวง

ยังไม่ได้เทสในเกม (ผู้ใช้จะเทสเอง) คอมไพล์ผ่านทั้งวัสดุและ Blueprint

## โฟมล้นเลยหัวเรือ

หัวเรืออยู่ที่ local X **ติดลบ** (ตัวชนกินพื้นที่ -310 ถึง +310 และจุดกระแทกคลื่น
หัวเรืออยู่ที่ -240 ท้ายเรือ +250) ตอนเปลี่ยน `step` เป็น `smoothstep` รอบก่อน
จุดเริ่มถูกดันจาก -245 ไปเป็น -305 คือยื่นเลยหัวเรือออกไปอีก 60 ซม.

```hlsl
rim *= smoothstep(-235.0, -140.0, p.x) * (1.0 - smoothstep(255.0, 375.0, p.x));
```

เริ่มจางที่ -235 (หลังหัวเรือ 75 ซม.) เต็มที่ -140 ด้านท้ายไม่แตะ หางน้ำยาวเท่าเดิม

ปรับความล้นด้านข้างที่ `Range` (ตอนนี้ 70 = โฟมกว้างออกจากกราบเรือข้างละ 70 ซม.)

**กับดัก**: เซฟ asset ไม่ได้ตอน PIE รัน ขึ้น `Asset does not exist` แต่
`set_properties` กับ recompile ทำได้และมีผลทันทีใน PIE ที่รันอยู่ — แก้แล้วต้อง
รอหยุด PIE ค่อยเซฟ ไม่งั้นงานหาย (เคยหายมาแล้วหนึ่งครั้งตาม handling-pass.md)

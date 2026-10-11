# ละออง/หมอกน้ำ — ปรับที่ไหน — 2026-10-02

ละอองมี **สองชั้น** คนละไฟล์ อย่าแก้ผิดตัว:

| ชั้น | ไฟล์ | ทำอะไร |
|---|---|---|
| **หมอก / ละอองฟุ้ง** | `Content/Boats/ThaiLongtail/FX/NS_LongtailSprayMist.uasset` | แผ่นควันโปร่ง ลอยค้าง |
| หยดน้ำ | `Content/Boats/ThaiLongtail/FX/NS_LongtailSideSpray.uasset` | เม็ดเล็ก ตกเร็ว |
| วัสดุของหมอก | `Content/Boats/ThaiLongtail/FX/M_LongtailSprayMist.uasset` | unlit translucent, opacity = flipbook **alpha** × particle alpha |
| ตัวสั่งความแรง | `BP_LongtailPhysicsPawn` → ฟังก์ชัน `UpdateSideSpray` | ป้อน SpawnRate/SpraySpeed/SpraySpread ทุกเฟรม |

## ค่าปัจจุบันใน NS_LongtailSprayMist

สองอีมิตเตอร์ชื่อ `Fountain` (ซ้าย) และ `Starboard` (ขวา) — **ต้องแก้ทั้งคู่ให้ตรงกัน**

| อยากได้อะไร | โมดูล | อินพุต | ค่าตอนนี้ |
|---|---|---|---|
| หมอกหนา/บาง | `InitializeParticle` | Color.**A** | **0.14** |
| ก้อนใหญ่/เล็ก | `InitializeParticle` | Uniform Sprite Size Min / Max | **70 / 185** |
| ลอยค้างนาน | `InitializeParticle` | Lifetime Min / Max | **1.2 / 2.8** s |
| ตกเร็ว/ช้า | `GravityForce` | Gravity.Z | **-260** |
| เบรกอากาศ | `Drag` | Drag | **2.2** |
| จำนวน | `EmitterUpdateScript/SpawnRate` | SpawnRate | ผูกกับ `User.SpawnRate` |
| พุ่งแรง | `AddVelocity` | Velocity Speed | ผูกกับ `User.SpraySpeed` |
| บานกว้าง | `AddVelocity` | Cone Angle | ผูกกับ `User.SpraySpread` |
| พุ่งขึ้น/ออกข้าง | `AddVelocity` | Cone Axis | **(0, ±0.55, 0.84)** |
| เกิดกระจายตามลำเรือ | `ShapeLocation` | Sphere Radius | **180** cm |
| ควันกลิ้งเป็นก้อน | `SubUVAnimation` | Random Start Frame | เปิดอยู่ |

สามตัวที่ผูก `User.*` **ไม่ต้องแก้ในนี้** — มันถูกเขียนทับทุกเฟรมจาก
`UpdateSideSpray` ใน `BP_LongtailPhysicsPawn` สูตรคือ `a = clamp(speed/90)` แล้ว

```
SpawnRate  =  9 + 38a        (หมอก)      /  300 + 1400a  (หยด)
SpraySpeed =  450 + 950a
SpraySpread=  20 + 26a
```

จะปรับความแรงรวม → แก้ที่ฟังก์ชันนั้น จะปรับหน้าตา → แก้ที่อีมิตเตอร์ตามตารางบน

## เทียบกับหยดน้ำ (NS_LongtailSideSpray)

ขนาด 1.5–5 cm, gravity **-1900**, drag **0.08**, life 0.30–0.85 s — ตั้งใจให้ตกเร็ว
กว่าจริง เพราะหยดเล็กจริงถูกอากาศหน่วง แต่เป้าหมายภาพคือน้ำที่ตกไว

## กับดัก

- opacity ต้องดึงจากช่อง **alpha** ของ flipbook ไม่ใช่ R — ใช้ R แล้วสไปรต์เป็นสี่เหลี่ยมขอบคม
- วัสดุต้องติด `bUsedWithNiagaraSprites` ไม่งั้น fallback เป็นสี่เหลี่ยมดำ
- `bOutputTranslucentVelocity` ต้องเปิด ไม่งั้น TSR ลากเป็นเงาตอนหมุนกล้อง

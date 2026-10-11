#pragma once

#include "CoreMinimal.h"

namespace BoatWater
{
    /** หนึ่งเฟรมของสนามคลื่น GPU ที่อ่านกลับมาฝั่ง CPU แล้ว ครอบเฉพาะหน้าต่างรอบเรือ ไม่ใช่ทั้งผืน */
    struct FRippleSnapshot
    {
        TArray<float> Heights;                           // ช่อง B ของ NormalRT เรียงทีละแถว
        int32 Width = 0;
        int32 Height = 0;
        FVector2D OriginWorld = FVector2D::ZeroVector;   // พิกัดโลกของจุดกึ่งกลางเซลล์ (0,0)
        double CellSizeCm = 0.0;
    };

    /** จุดกึ่งกลางเซลล์ (0,0) ของกริดเต็มผืน ค่ากลางเซลล์เลื่อนครึ่งช่องจากขอบซ้ายบน */
    inline FVector2D RippleGridOrigin(FVector2D GridCenter, double WorldSizeCm, int32 TextureWidth)
    {
        if (TextureWidth <= 0 || !FMath::IsFinite(WorldSizeCm))
        {
            return GridCenter;
        }
        const double CellSizeCm = WorldSizeCm / TextureWidth;
        return GridCenter - FVector2D(WorldSizeCm * 0.5) + FVector2D(CellSizeCm * 0.5);
    }

    /** แปลงพิกัดโลกเป็นพิกัดเซลล์ทศนิยมของ snapshot นอกกรอบคืน false */
    inline bool RippleCellCoords(const FRippleSnapshot& Snapshot, FVector2D WorldXY,
        double& OutCellX, double& OutCellY)
    {
        OutCellX = 0.0;
        OutCellY = 0.0;
        if (Snapshot.Width < 2 || Snapshot.Height < 2 || !FMath::IsFinite(Snapshot.CellSizeCm)
            || Snapshot.CellSizeCm <= 0.0 || !FMath::IsFinite(WorldXY.X) || !FMath::IsFinite(WorldXY.Y)
            || Snapshot.Heights.Num() < Snapshot.Width * Snapshot.Height)
        {
            return false;
        }
        OutCellX = (WorldXY.X - Snapshot.OriginWorld.X) / Snapshot.CellSizeCm;
        OutCellY = (WorldXY.Y - Snapshot.OriginWorld.Y) / Snapshot.CellSizeCm;
        // ขอบนอกสุดไม่มีเพื่อนบ้านครบสี่ช่อง จึงไม่ยอมประมาณค่าเลยขอบหน้าต่างออกไป
        return OutCellX >= 0.0 && OutCellY >= 0.0
            && OutCellX <= Snapshot.Width - 1 && OutCellY <= Snapshot.Height - 1;
    }

    /** ความสูงระลอกแบบ bilinear หน่วยเซนติเมตร นอกกรอบคืน 0 เพื่อไม่เดาค่านอกสนามจำลอง */
    inline double SampleRippleHeight(const FRippleSnapshot& Snapshot, FVector2D WorldXY)
    {
        double CellX = 0.0;
        double CellY = 0.0;
        if (!RippleCellCoords(Snapshot, WorldXY, CellX, CellY))
        {
            return 0.0;
        }
        const int32 X0 = FMath::Clamp(static_cast<int32>(FMath::FloorToDouble(CellX)), 0, Snapshot.Width - 2);
        const int32 Y0 = FMath::Clamp(static_cast<int32>(FMath::FloorToDouble(CellY)), 0, Snapshot.Height - 2);
        const double FracX = FMath::Clamp(CellX - X0, 0.0, 1.0);
        const double FracY = FMath::Clamp(CellY - Y0, 0.0, 1.0);
        // ค่า NaN/Inf ที่หลุดมาจาก GPU ต้องกลายเป็นศูนย์ ไม่ใช่ไหลต่อเข้าแรงที่ส่งให้ Chaos
        auto At = [&Snapshot](int32 X, int32 Y) -> double
        {
            const float Value = Snapshot.Heights[Y * Snapshot.Width + X];
            return FMath::IsFinite(Value) ? static_cast<double>(Value) : 0.0;
        };
        const double Near = FMath::Lerp(At(X0, Y0), At(X0 + 1, Y0), FracX);
        const double Far = FMath::Lerp(At(X0, Y0 + 1), At(X0 + 1, Y0 + 1), FracX);
        return FMath::Lerp(Near, Far, FracY);
    }

    /** ปริมาตรจมของทุ่นทรงกลม สูตรเดียวกับ UBuoyancyComponent::ComputeBuoyancy */
    inline double PontoonSubmergedVolume(double RadiusCm, double CenterZCm, double WaterLevelCm)
    {
        const double SubmersionDiff =
            FMath::Clamp(WaterLevelCm - (CenterZCm - RadiusCm), 0.0, 2.0 * RadiusCm);
        return (UE_DOUBLE_PI / 3.0) * SubmersionDiff * SubmersionDiff
            * (3.0 * RadiusCm - SubmersionDiff);
    }

    /** สัมประสิทธิ์ลอยตัวหลังคูณ ramp ตามความเร็ว เลียนของ engine ตรง ๆ */
    inline double RampedBuoyancyCoefficient(double Coefficient, double RampMinKmh,
        double RampMaxKmh, double RampMax, double ForwardSpeedKmh)
    {
        if (!FMath::IsFinite(Coefficient) || Coefficient <= 0.0 || !FMath::IsFinite(ForwardSpeedKmh))
        {
            return 0.0;
        }
        // ช่วงความเร็วที่ตั้งไว้เท่ากันจะหารศูนย์ ถือว่าโปรไฟล์นั้นไม่มี ramp แทนการคืนค่าอนันต์
        const double Span = RampMaxKmh - RampMinKmh;
        if (!FMath::IsFinite(Span) || FMath::IsNearlyZero(Span) || !FMath::IsFinite(RampMax))
        {
            return Coefficient;
        }
        const double Factor = FMath::Clamp((ForwardSpeedKmh - RampMinKmh) / Span, 0.0, 1.0);
        return Coefficient * (1.0 + Factor * (RampMax - 1.0));
    }

    /**
     * แรงลอยตัว "ส่วนเพิ่ม" จากระลอกคลื่น GPU คือผลต่างของแรงที่ engine จะได้ถ้าระดับน้ำสูงขึ้นเท่าระลอก
     * คำนวณผ่านสูตรและเพดานชุดเดียวกับ engine จึงไม่ต้องตั้งค่าคงที่ฟิสิกส์ใหม่ และคืน 0 เมื่อระลอกเป็นศูนย์
     * ไม่รวมพจน์หน่วง เพราะหน่วงขึ้นกับความเร็วแนวดิ่งไม่ใช่ระดับน้ำ ผลต่างจึงตัดกันพอดี
     */
    inline double RippleBuoyancyForceZ(double RadiusCm, double CenterZCm, double BaseWaterLevelCm,
        double RippleHeightCm, double Coefficient, double MaxBuoyantForce)
    {
        if (!FMath::IsFinite(RadiusCm) || RadiusCm <= 0.0 || !FMath::IsFinite(CenterZCm)
            || !FMath::IsFinite(BaseWaterLevelCm) || !FMath::IsFinite(RippleHeightCm)
            || !FMath::IsFinite(Coefficient) || Coefficient <= 0.0
            || !FMath::IsFinite(MaxBuoyantForce) || MaxBuoyantForce <= 0.0)
        {
            return 0.0;
        }
        const double Base = FMath::Clamp(
            PontoonSubmergedVolume(RadiusCm, CenterZCm, BaseWaterLevelCm) * Coefficient,
            0.0, MaxBuoyantForce);
        const double Rippled = FMath::Clamp(
            PontoonSubmergedVolume(RadiusCm, CenterZCm, BaseWaterLevelCm + RippleHeightCm) * Coefficient,
            0.0, MaxBuoyantForce);
        return Rippled - Base;
    }
}

#include "BoatlRacingWaterLibrary.h"
#include "BoatWaterCurrentPolicy.h"

#include "BuoyancyComponent.h"
#include "Components/PrimitiveComponent.h"
#include "WaterBodyComponent.h"
#include "WaterBodyTypes.h"

bool UBoatlRacingWaterLibrary::SampleWaveSurface(UBuoyancyComponent* Buoyancy,
    FVector WorldLocation, float& WaterHeightCm, FVector& WaterVelocity)
{
    WaterHeightCm = 0.0f;
    WaterVelocity = FVector::ZeroVector;
    if (!IsValid(Buoyancy) || WorldLocation.ContainsNaN())
    {
        return false;
    }

    bool bFound = false;
    const EWaterBodyQueryFlags Flags = EWaterBodyQueryFlags::ComputeLocation
        | EWaterBodyQueryFlags::ComputeVelocity | EWaterBodyQueryFlags::IncludeWaves;

    // ใช้แหล่งน้ำที่ทุ่นเรือกำลังสัมผัส แล้วถามระดับคลื่น ณ จุดใบพัดจริง
    // ค่าเฉลี่ยทุ่นท้ายใช้แทนไม่ได้ เพราะยอดคลื่นอาจต่างกันหลายเมตรตามแนวยาวเรือ
    for (UWaterBodyComponent* Body : Buoyancy->GetCurrentWaterBodyComponents())
    {
        if (!IsValid(Body))
        {
            continue;
        }

        const auto Query = Body->TryQueryWaterInfoClosestToWorldLocation(WorldLocation, Flags);
        if (!Query.HasValue() || Query.GetValue().IsInExclusionVolume())
        {
            continue;
        }

        const FWaterBodyQueryResult& Result = Query.GetValue();
        const float CandidateHeight = Result.GetWaterSurfaceLocation().Z;
        const FVector CandidateVelocity = BoatWater::ResolvePhysicalCurrent(
            Body->GetWaterBodyType(), Buoyancy->BuoyancyData.bApplyRiverForces, Result.GetVelocity());
        if (!FMath::IsFinite(Result.GetWaterPlaneLocation().Z)
            || !FMath::IsFinite(CandidateHeight) || CandidateVelocity.ContainsNaN())
        {
            continue;
        }
        // API ถามจุดที่ใกล้ที่สุดอาจคืนผิวน้ำแม้ใบพัดพ้นตลิ่งแล้ว
        // ตรวจที่ระดับระนาบน้ำ เพื่อไม่ให้ยอดคลื่นสูงทำให้หลุดกรอบชนแนวดิ่ง
        FVector CoveragePoint(WorldLocation.X, WorldLocation.Y, Result.GetWaterPlaneLocation().Z);
        bool bCovered = false;
        for (UPrimitiveComponent* Collision : Body->GetCollisionComponents())
        {
            FVector ClosestPoint;
            if (IsValid(Collision)
                && Collision->GetClosestPointOnCollision(CoveragePoint, ClosestPoint) == 0.0f)
            {
                bCovered = true;
                break;
            }
        }
        if (!bCovered)
        {
            continue;
        }
        if (!bFound || CandidateHeight > WaterHeightCm)
        {
            WaterHeightCm = CandidateHeight;
            WaterVelocity = CandidateVelocity;
            bFound = true;
        }
    }

    return bFound;
}

bool UBoatlRacingWaterLibrary::SetHullPontoonRadii(UBuoyancyComponent* Buoyancy,
    float FrontRadiusCm, float RearRadiusCm)
{
    if (!IsValid(Buoyancy) || !IsValid(Buoyancy->GetSimulatingComponent())
        || Buoyancy->BuoyancyData.Pontoons.Num() < 4
        || !FMath::IsFinite(FrontRadiusCm) || !FMath::IsFinite(RearRadiusCm)
        || FrontRadiusCm <= 0.0f || RearRadiusCm <= 0.0f)
    {
        return false;
    }

    // สี่ทุ่นแรกเป็นตัวรับน้ำหนักของลำเรือเท่านั้น ใบพัดไม่มีทุ่นและไม่ค้ำท้ายเรือ
    // เรียกจาก Pawn BeginPlay หลัง component เริ่มและตั้งมวล/ศูนย์ถ่วงแล้ว แต่ก่อน physics tick
    for (int32 Index = 0; Index < 4; ++Index)
    {
        Buoyancy->BuoyancyData.Pontoons[Index].Radius =
            Index < 2 ? FrontRadiusCm : RearRadiusCm;
    }
    // รัศมีไม่เปลี่ยนตำแหน่งหรือ enabled mask ของทุ่น จึงไม่ต้องคำนวณ sprung mass ใหม่
    // Water component จะส่ง Pontoons ทั้งชุดรวมรัศมีใหม่เข้า async physics ใน Update ถัดไป
    return true;
}

FVector UBoatlRacingWaterLibrary::CalculateTailWaterForce(FVector PointVelocity,
    FVector WaterVelocity, FVector TailSideDirection, float Immersion, float TrimDegrees,
    float DragCoefficient, float MaximumForce)
{
    if (PointVelocity.ContainsNaN() || WaterVelocity.ContainsNaN() || TailSideDirection.ContainsNaN()
        || !FMath::IsFinite(Immersion) || !FMath::IsFinite(TrimDegrees)
        || !FMath::IsFinite(DragCoefficient) || !FMath::IsFinite(MaximumForce)
        || DragCoefficient <= 0.0f || MaximumForce <= 0.0f)
    {
        return FVector::ZeroVector;
    }

    // ใช้ทิศด้านข้างและความเร็วสัมพัทธ์บนระนาบเดียวกัน เพื่อไม่แปลงการเด้งจากคลื่นเป็นแรงเร่ง
    // F dot V ต้องไม่เป็นบวกในกรอบน้ำ แกนที่ยกพ้นน้ำหรือเรือหยุดจึงไม่มีแรงเลี้ยวจากกระแสน้ำ
    TailSideDirection.Z = 0.0;
    const FVector Normal = TailSideDirection.GetSafeNormal();
    const double WetFactor = FMath::Clamp(Immersion, 0.0f, 1.0f)
        * FMath::Clamp((-TrimDegrees - 3.0f) / 7.0f, 0.0f, 1.0f);
    if (WetFactor <= 0.0 || Normal.IsNearlyZero() || Normal.ContainsNaN())
    {
        return FVector::ZeroVector;
    }
    // ตัวเลขต้นทางอาจ finite แต่ผลลบหรือ dot ล้นได้ ต้องหยุดก่อนส่งแรงผิดเข้า Chaos
    const FVector RelativeVelocity = PointVelocity - WaterVelocity;
    if (RelativeVelocity.ContainsNaN())
    {
        return FVector::ZeroVector;
    }
    const double Slip = FVector::DotProduct(RelativeVelocity, Normal);
    if (!FMath::IsFinite(Slip))
    {
        return FVector::ZeroVector;
    }
    // จำกัดแรงก่อนยกกำลังสอง เพื่อให้ความเร็วสูงมากไม่ทำให้แรงคำนวณล้น
    const double EffectiveDrag = static_cast<double>(DragCoefficient) * WetFactor;
    const double SaturationSpeed = FMath::Sqrt(static_cast<double>(MaximumForce) / EffectiveDrag);
    const double Magnitude = FMath::Abs(Slip) >= SaturationSpeed
        ? static_cast<double>(MaximumForce) : EffectiveDrag * Slip * Slip;
    const double ForceMagnitude = Slip > 0.0 ? -Magnitude : Magnitude;
    return Normal * ForceMagnitude;
}

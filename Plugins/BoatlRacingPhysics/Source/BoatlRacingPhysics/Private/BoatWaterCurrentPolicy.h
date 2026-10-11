#pragma once

#include "WaterBodyTypes.h"

namespace BoatWater
{
    inline FVector ResolvePhysicalCurrent(EWaterBodyType BodyType, bool bApplyRiverForces,
        FVector QueryVelocity)
    {
        // Ocean/Lake มีค่า spline velocity ได้ แต่ไม่ใช่แรงกระแสน้ำที่ Water ใช้กับลำเรือ
        // ใช้เฉพาะแม่น้ำที่เปิดแรงกระแส เพื่อไม่ให้หางเรือสร้างแรงเลี้ยวเองตอนเรือหยุด
        return bApplyRiverForces && BodyType == EWaterBodyType::River
            ? QueryVelocity : FVector::ZeroVector;
    }
}

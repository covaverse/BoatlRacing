#pragma once

#include "CoreMinimal.h"
#include "BoatRippleFieldMath.h"
#include "RHIGPUReadback.h"

/**
 * สถานะการอ่านสนามคลื่นกลับจาก GPU
 * ฟิลด์ชุด InFlight เป็นของ render thread เท่านั้น ส่วน snapshot ส่งข้ามเธรดใต้ล็อก
 * ถือด้วย shared pointer เพื่อให้ render command ที่ยังค้างไม่อ้างถึง component ที่ถูกทำลายไปแล้ว
 */
struct FBoatRippleReadback
{
    TUniquePtr<FRHIGPUTextureReadback> Texture;
    bool bCopyInFlight = false;
    FIntRect InFlightRect = FIntRect(0, 0, 0, 0);
    FVector2D InFlightOrigin = FVector2D::ZeroVector;
    double InFlightCellSizeCm = 0.0;

    TSharedPtr<const BoatWater::FRippleSnapshot, ESPMode::ThreadSafe> GetSnapshot() const
    {
        FScopeLock Lock(&SnapshotLock);
        return Snapshot;
    }

    void PublishSnapshot(TSharedPtr<const BoatWater::FRippleSnapshot, ESPMode::ThreadSafe> Resolved)
    {
        FScopeLock Lock(&SnapshotLock);
        Snapshot = MoveTemp(Resolved);
        ResolvedFrames.Increment();
    }

    int32 GetResolvedFrames() const { return ResolvedFrames.GetValue(); }

private:
    mutable FCriticalSection SnapshotLock;
    TSharedPtr<const BoatWater::FRippleSnapshot, ESPMode::ThreadSafe> Snapshot;
    FThreadSafeCounter ResolvedFrames;
};

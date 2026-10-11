#include "BoatRippleFieldComponent.h"
#include "BoatRippleReadback.h"

#include "BuoyancyComponent.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/TextureRenderTarget2D.h"
#include "RenderingThread.h"
#include "TextureResource.h"

namespace
{
    /**
     * เก็บผลรอบก่อนแล้วค่อยสั่งคัดลอกรอบใหม่ จึงมีสำเนาค้างบน GPU ครั้งละชุดเดียวเสมอ
     * ทำงานบน render thread ล้วน เพราะ Lock ของ readback ใช้ immediate command list
     */
    void TickRippleReadback_RenderThread(FRHICommandListImmediate& RHICmdList,
        FBoatRippleReadback& State, FTextureRenderTargetResource* Resource,
        FIntRect Rect, FVector2D WindowOrigin, double CellSizeCm)
    {
        if (State.bCopyInFlight && State.Texture.IsValid() && State.Texture->IsReady())
        {
            int32 RowPitchInPixels = 0;
            int32 BufferHeight = 0;
            const FFloat16Color* Pixels =
                static_cast<const FFloat16Color*>(State.Texture->Lock(RowPitchInPixels, &BufferHeight));
            if (Pixels)
            {
                const int32 Width = State.InFlightRect.Width();
                const int32 Height = State.InFlightRect.Height();
                // staging surface กว้างกว่าที่ขอได้ แต่แคบกว่าแปลว่าอ่านผิดแถว ต้องทิ้งทั้งเฟรม
                if (Width > 0 && Height > 0 && RowPitchInPixels >= Width && BufferHeight >= Height)
                {
                    TSharedRef<BoatWater::FRippleSnapshot, ESPMode::ThreadSafe> Snapshot =
                        MakeShared<BoatWater::FRippleSnapshot, ESPMode::ThreadSafe>();
                    Snapshot->Width = Width;
                    Snapshot->Height = Height;
                    Snapshot->OriginWorld = State.InFlightOrigin;
                    Snapshot->CellSizeCm = State.InFlightCellSizeCm;
                    Snapshot->Heights.SetNumUninitialized(Width * Height);
                    for (int32 Y = 0; Y < Height; ++Y)
                    {
                        const FFloat16Color* Row = Pixels + static_cast<int64>(Y) * RowPitchInPixels;
                        for (int32 X = 0; X < Width; ++X)
                        {
                            // Ripple Solver เก็บความสูงไว้ในช่อง B ของ NormalRT
                            Snapshot->Heights[Y * Width + X] = Row[X].B.GetFloat();
                        }
                    }
                    State.PublishSnapshot(Snapshot);
                }
                State.Texture->Unlock();
            }
            State.bCopyInFlight = false;
        }

        if (State.bCopyInFlight || !Resource)
        {
            return;
        }
        FRHITexture* SourceTexture = Resource->GetRenderTargetTexture();
        if (!SourceTexture)
        {
            return;
        }
        if (!State.Texture.IsValid())
        {
            State.Texture = MakeUnique<FRHIGPUTextureReadback>(TEXT("BoatRippleHeightReadback"));
        }
        State.Texture->EnqueueCopy(RHICmdList, SourceTexture,
            FIntVector(Rect.Min.X, Rect.Min.Y, 0), 0,
            FIntVector(Rect.Width(), Rect.Height(), 1));
        State.bCopyInFlight = true;
        State.InFlightRect = Rect;
        State.InFlightOrigin = WindowOrigin;
        State.InFlightCellSizeCm = CellSizeCm;
    }
}

UBoatRippleFieldComponent::UBoatRippleFieldComponent()
{
    PrimaryComponentTick.bCanEverTick = false;
}

UBoatRippleFieldComponent::~UBoatRippleFieldComponent() = default;

void UBoatRippleFieldComponent::BeginPlay()
{
    Super::BeginPlay();
    State = MakeShared<FBoatRippleReadback, ESPMode::ThreadSafe>();
}

void UBoatRippleFieldComponent::EndPlay(const EEndPlayReason::Type EndPlayReason)
{
    // render command ที่ยังค้างถือ shared pointer ของตัวเอง หน่วยความจำจึงคืนหลังงานนั้นจบ
    State.Reset();
    Super::EndPlay(EndPlayReason);
}

int32 UBoatRippleFieldComponent::GetResolvedFrameCount() const
{
    return State.IsValid() ? State->GetResolvedFrames() : 0;
}

bool UBoatRippleFieldComponent::UpdateRippleField(UTextureRenderTarget2D* NormalHeightRT,
    FVector GridCenter, float SimulationWorldSizeCm, FVector FocusWorldLocation)
{
    if (!bEnabled || !State.IsValid() || !IsValid(NormalHeightRT)
        || !FMath::IsFinite(SimulationWorldSizeCm) || SimulationWorldSizeCm <= 0.0f
        || GridCenter.ContainsNaN() || FocusWorldLocation.ContainsNaN())
    {
        return false;
    }
    // สนามคลื่นของ Water plugin เป็น RGBA16f เท่านั้น รูปแบบอื่นแปลว่าต่อผิดพื้นผิว
    if (NormalHeightRT->GetFormat() != PF_FloatRGBA)
    {
        return false;
    }
    const int32 TextureWidth = NormalHeightRT->SizeX;
    const int32 TextureHeight = NormalHeightRT->SizeY;
    if (TextureWidth < 2 || TextureHeight < 2)
    {
        return false;
    }
    FTextureRenderTargetResource* Resource = NormalHeightRT->GetRenderTargetResource();
    if (!Resource)
    {
        return false;
    }

    const double CellSizeCm = static_cast<double>(SimulationWorldSizeCm) / TextureWidth;
    const FVector2D GridOrigin = BoatWater::RippleGridOrigin(
        FVector2D(GridCenter.X, GridCenter.Y), SimulationWorldSizeCm, TextureWidth);

    // อ่านเฉพาะหน้าต่างรอบเรือ เพราะทั้งผืน 1024x1024 RGBA16f คือ 8 MB ต่อเฟรม
    const int32 Side = FMath::Clamp(WindowCells, 32, FMath::Min(TextureWidth, TextureHeight));
    const double FocusCellX = (FocusWorldLocation.X - GridOrigin.X) / CellSizeCm;
    const double FocusCellY = (FocusWorldLocation.Y - GridOrigin.Y) / CellSizeCm;
    if (!FMath::IsFinite(FocusCellX) || !FMath::IsFinite(FocusCellY))
    {
        return false;
    }
    // หนีบเป็น double ก่อนแปลงเป็นจำนวนเต็ม เพราะเรือที่อยู่ไกลสนามจำลองมากทำให้ cast ล้น
    const int32 MinX = static_cast<int32>(FMath::Clamp(
        FMath::FloorToDouble(FocusCellX) - Side / 2, 0.0, static_cast<double>(TextureWidth - Side)));
    const int32 MinY = static_cast<int32>(FMath::Clamp(
        FMath::FloorToDouble(FocusCellY) - Side / 2, 0.0, static_cast<double>(TextureHeight - Side)));
    const FIntRect Rect(MinX, MinY, MinX + Side, MinY + Side);
    const FVector2D WindowOrigin = GridOrigin + FVector2D(MinX * CellSizeCm, MinY * CellSizeCm);

    TSharedPtr<FBoatRippleReadback, ESPMode::ThreadSafe> SharedState = State;
    ENQUEUE_RENDER_COMMAND(BoatRippleFieldTick)(
        [SharedState, Resource, Rect, WindowOrigin, CellSizeCm](FRHICommandListImmediate& RHICmdList)
        {
            TickRippleReadback_RenderThread(RHICmdList, *SharedState, Resource,
                Rect, WindowOrigin, CellSizeCm);
        });
    return true;
}

float UBoatRippleFieldComponent::GetRippleHeight(FVector WorldLocation) const
{
    if (!State.IsValid() || WorldLocation.ContainsNaN() || !FMath::IsFinite(MaxRippleHeightCm))
    {
        return 0.0f;
    }
    const TSharedPtr<const BoatWater::FRippleSnapshot, ESPMode::ThreadSafe> Snapshot = State->GetSnapshot();
    if (!Snapshot.IsValid())
    {
        return 0.0f;
    }
    const double Limit = FMath::Max(0.0, static_cast<double>(MaxRippleHeightCm));
    return static_cast<float>(FMath::Clamp(
        BoatWater::SampleRippleHeight(*Snapshot, FVector2D(WorldLocation.X, WorldLocation.Y)),
        -Limit, Limit));
}

FVector UBoatRippleFieldComponent::ApplyRippleBuoyancy(UBuoyancyComponent* Buoyancy)
{
    if (!bEnabled || !State.IsValid() || !IsValid(Buoyancy))
    {
        return FVector::ZeroVector;
    }
    UPrimitiveComponent* Body = Buoyancy->GetSimulatingComponent();
    if (!IsValid(Body) || !Body->IsSimulatingPhysics())
    {
        return FVector::ZeroVector;
    }
    const TSharedPtr<const BoatWater::FRippleSnapshot, ESPMode::ThreadSafe> Snapshot = State->GetSnapshot();
    if (!Snapshot.IsValid())
    {
        return FVector::ZeroVector;
    }

    const FBuoyancyData& Data = Buoyancy->BuoyancyData;
    // ความเร็วหน้าเรือคิดหน่วยเดียวกับ engine เพื่อให้ ramp ของสัมประสิทธิ์ตรงกับที่ทุ่นใช้จริง
    const double ForwardSpeedKmh =
        FVector::DotProduct(Body->GetForwardVector(), Body->GetComponentVelocity()) * 0.036;
    const double Coefficient = BoatWater::RampedBuoyancyCoefficient(Data.BuoyancyCoefficient,
        Data.BuoyancyRampMinVelocity, Data.BuoyancyRampMaxVelocity, Data.BuoyancyRampMax,
        ForwardSpeedKmh);
    const double Limit = FMath::Max(0.0, static_cast<double>(MaxRippleHeightCm));

    FVector TotalForce = FVector::ZeroVector;
    for (const FSphericalPontoon& Pontoon : Data.Pontoons)
    {
        // ทุ่นที่พ้นน้ำไม่มีแรงลอยตัวให้แก้ และ engine เองก็ไม่คิดแรงให้ทุ่นนั้น
        if (!Pontoon.bIsInWater || Pontoon.CenterLocation.ContainsNaN())
        {
            continue;
        }
        const double RippleHeightCm = FMath::Clamp(BoatWater::SampleRippleHeight(*Snapshot,
            FVector2D(Pontoon.CenterLocation.X, Pontoon.CenterLocation.Y)), -Limit, Limit);
        if (FMath::IsNearlyZero(RippleHeightCm))
        {
            continue;
        }
        // engine หนีบแรงก่อนคูณ PontoonCoefficient จึงต้องคูณทีหลังเช่นกัน ไม่งั้นเพดานเพี้ยน
        const double ForceZ = BoatWater::RippleBuoyancyForceZ(Pontoon.Radius,
            Pontoon.CenterLocation.Z, Pontoon.WaterHeight, RippleHeightCm,
            Coefficient, Data.MaxBuoyantForce) * Pontoon.PontoonCoefficient;
        if (!FMath::IsFinite(ForceZ) || FMath::IsNearlyZero(ForceZ))
        {
            continue;
        }
        const FVector Force(0.0, 0.0, ForceZ);
        Body->AddForceAtLocation(Force, Pontoon.CenterLocation);
        TotalForce += Force;
    }
    return TotalForce;
}

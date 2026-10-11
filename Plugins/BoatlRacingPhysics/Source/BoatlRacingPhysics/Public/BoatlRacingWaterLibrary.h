#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "BoatlRacingWaterLibrary.generated.h"

class UBuoyancyComponent;

UCLASS()
class BOATLRACINGPHYSICS_API UBoatlRacingWaterLibrary : public UBlueprintFunctionLibrary
{
    GENERATED_BODY()

public:
    UFUNCTION(BlueprintCallable, Category = "Boat|Water")
    static bool SampleWaveSurface(UBuoyancyComponent* Buoyancy, FVector WorldLocation,
        float& WaterHeightCm, FVector& WaterVelocity);

    UFUNCTION(BlueprintCallable, Category = "Boat|Water")
    static bool SetHullPontoonRadii(UBuoyancyComponent* Buoyancy,
        float FrontRadiusCm, float RearRadiusCm);

    UFUNCTION(BlueprintPure, Category = "Boat|Water")
    static FVector CalculateTailWaterForce(FVector PointVelocity, FVector WaterVelocity,
        FVector TailSideDirection, float Immersion, float TrimDegrees,
        float DragCoefficient, float MaximumForce = 150000.0f);
};

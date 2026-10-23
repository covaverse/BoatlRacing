#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "Engine/DeveloperSettings.h"
#include "Engine/World.h"
#include "Subsystems/GameInstanceSubsystem.h"
#include "GameFramework/SaveGame.h"
#include "GameFramework/Actor.h"
#include "Blueprint/UserWidget.h"
#include "BoatFrontend.generated.h"

class UStaticMesh;
class UMaterialInterface;
class APawn;
class USkeletalMesh;
class UTexture2D;
class UTextBlock;
class UProgressBar;
class UCanvasPanel;
class UBoatFrontendWidget;
class UBoatRPMWidget;
class USoundMix;
class USoundClass;

USTRUCT(BlueprintType)
struct FBoatPreviewPart
{
    GENERATED_BODY()
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<UStaticMesh> StaticMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<USkeletalMesh> SkeletalMesh;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FTransform Transform = FTransform::Identity;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<TSoftObjectPtr<UMaterialInterface>> Materials;
};

UCLASS(BlueprintType)
class BOATLRACINGPHYSICS_API UBoatDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<UTexture2D> Thumbnail;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftClassPtr<APawn> PawnClass;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<UDataAsset> HandlingProfile;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FBoatPreviewPart> PreviewParts;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TArray<FName> CompatibleEngines;
};

UCLASS(BlueprintType)
class BOATLRACINGPHYSICS_API UBoatEngineDefinition : public UDataAsset
{
    GENERATED_BODY()
public:
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FName Id;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) FText DisplayName;
    UPROPERTY(EditAnywhere, BlueprintReadWrite) TSoftObjectPtr<UTexture2D> Thumbnail;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0")) float EngineMassKg = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0")) float DriveForce = 0;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0")) float IdleRPM = 900;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1")) float LoadedMaxRPM = 5600;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1")) float FreeMaxRPM = 6500;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="0.001")) float ShaftRatio = 0.25f;
    UPROPERTY(EditAnywhere, BlueprintReadWrite, meta=(ClampMin="1")) float ShaftFullRPM = 1400;
};

UCLASS(Config=Game, DefaultConfig, meta=(DisplayName="Boat Frontend"))
class BOATLRACINGPHYSICS_API UBoatFrontendSettings : public UDeveloperSettings
{
    GENERATED_BODY()
public:
    UPROPERTY(Config, EditAnywhere) TArray<TSoftObjectPtr<UBoatDefinition>> Boats;
    UPROPERTY(Config, EditAnywhere) TArray<TSoftObjectPtr<UBoatEngineDefinition>> Engines;
    UPROPERTY(Config, EditAnywhere) TSoftObjectPtr<USoundMix> MasterMix;
    UPROPERTY(Config, EditAnywhere) TSoftObjectPtr<USoundClass> MasterClass;
};

UCLASS()
class BOATLRACINGPHYSICS_API UBoatFrontendSave : public USaveGame
{
    GENERATED_BODY()
public:
    UPROPERTY() int32 Version = 1;
    UPROPERTY() FName BoatId;
    UPROPERTY() FName EngineId;
    UPROPERTY() bool Sport = false;
    UPROPERTY() FString Map = TEXT("/Game/Maps/M_CanalBlockout");
    UPROPERTY() float MasterVolume = 0.8f;
    UPROPERTY() float HUDScale = 1;
};

UCLASS()
class BOATLRACINGPHYSICS_API UBoatFrontendSubsystem : public UGameInstanceSubsystem
{
    GENERATED_BODY()
public:
    virtual void Initialize(FSubsystemCollectionBase& Collection) override;
    virtual void Deinitialize() override;
    UPROPERTY(Transient) TObjectPtr<UBoatFrontendSave> Selection;
    UPROPERTY(Transient) TArray<TObjectPtr<UBoatDefinition>> Boats;
    UPROPERTY(Transient) TArray<TObjectPtr<UBoatEngineDefinition>> Engines;
    UBoatDefinition* CurrentBoat() const;
    UBoatEngineDefinition* CurrentEngine() const;
    bool IsCompatible(const UBoatEngineDefinition* Engine) const;
    void ValidateSelection();
    bool Save();
    void ApplyAudio(UWorld* World);
    static const TArray<FString>& Maps();
    static bool IsFrontend(UWorld* World);
private:
    void WorldReady(const UWorld::FActorsInitializedParams& Params);
    void ConfigurePawn(APawn* Pawn);
    FDelegateHandle WorldHandle;
};

UCLASS()
class BOATLRACINGPHYSICS_API ABoatUIHost : public AActor
{
    GENERATED_BODY()
public:
    ABoatUIHost();
    virtual void Tick(float DeltaSeconds) override;
    virtual void EndPlay(const EEndPlayReason::Type Reason) override;
    void TogglePause();
    void SetPaused(bool Paused);
    void BuildPreview();
    void RotatePreview(float Degrees);
    UPROPERTY(Transient) TObjectPtr<UBoatFrontendWidget> Screen;
    UPROPERTY(Transient) TObjectPtr<AActor> Preview;
    UPROPERTY(Transient) TObjectPtr<AActor> PreviewCamera;
    bool bPaused = false;
};

UCLASS()
class BOATLRACINGPHYSICS_API UBoatMenuAction : public UObject
{
    GENERATED_BODY()
public:
    UPROPERTY() TObjectPtr<UBoatFrontendWidget> Screen;
    FString Action;
    FString Value;
    UFUNCTION() void Invoke();
};

UCLASS()
class BOATLRACINGPHYSICS_API UBoatRPMWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    float RPM = 0;
    float Maximum = 6500;
protected:
    virtual int32 NativePaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling,
        FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool Enabled) const override;
};

UCLASS()
class BOATLRACINGPHYSICS_API UBoatFrontendWidget : public UUserWidget
{
    GENERATED_BODY()
public:
    UPROPERTY() TObjectPtr<ABoatUIHost> Host;
    void Build(const FString& Page);
    void Dispatch(const FString& Action, const FString& Value);
    UFUNCTION() void VolumeChanged(float Value);
    UFUNCTION() void ScaleChanged(float Value);
protected:
    virtual void NativeTick(const FGeometry& Geometry, float DeltaSeconds) override;
    virtual FReply NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event) override;
    virtual FReply NativeOnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply NativeOnMouseMove(const FGeometry& Geometry, const FPointerEvent& Event) override;
    virtual FReply NativeOnMouseButtonUp(const FGeometry& Geometry, const FPointerEvent& Event) override;
private:
    UPROPERTY() TArray<TObjectPtr<UBoatMenuAction>> Actions;
    UPROPERTY() TObjectPtr<UTextBlock> SpeedText;
    UPROPERTY() TObjectPtr<UTextBlock> StateText;
    UPROPERTY() TObjectPtr<UTextBlock> RPMText;
    UPROPERTY() TObjectPtr<UTextBlock> Feedback;
    UPROPERTY() TObjectPtr<UProgressBar> ThrottleBar;
    UPROPERTY() TObjectPtr<UBoatRPMWidget> Dial;
    UPROPERTY() TObjectPtr<UWidget> HUDPanel;
    FString CurrentPage;
    bool bDragging = false;
    UBoatFrontendSubsystem* Data() const;
    void Persist();
};

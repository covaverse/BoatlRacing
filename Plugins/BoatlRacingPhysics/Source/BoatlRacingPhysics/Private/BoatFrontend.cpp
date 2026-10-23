#include "BoatFrontend.h"
#include "Camera/CameraActor.h"
#include "Camera/CameraComponent.h"
#include "Components/InputComponent.h"
#include "Components/StaticMeshComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "EngineUtils.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Sound/SoundMix.h"
#include "Sound/SoundClass.h"
#include "UObject/UnrealType.h"

namespace BoatFrontend
{
    const FString Slot = TEXT("BoatFrontend_v1");

    double ReadNumber(const UObject* Object, FName Name, double Fallback = 0)
    {
        if (!Object) return Fallback;
        const FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        if (!Property) return Fallback;
        const void* Address = Property->ContainerPtrToValuePtr<void>(Object);
        return Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Address) : Property->GetSignedIntPropertyValue(Address);
    }

    bool WriteNumber(UObject* Object, FName Name, double Value)
    {
        if (!Object || !FMath::IsFinite(Value)) return false;
        FNumericProperty* Property = FindFProperty<FNumericProperty>(Object->GetClass(), Name);
        if (!Property) return false;
        void* Address = Property->ContainerPtrToValuePtr<void>(Object);
        if (Property->IsFloatingPoint()) Property->SetFloatingPointPropertyValue(Address, Value);
        else Property->SetIntPropertyValue(Address, int64(Value));
        return true;
    }
}

const TArray<FString>& UBoatFrontendSubsystem::Maps()
{
    static const TArray<FString> Values = { TEXT("/Game/Maps/M_CanalBlockout"), TEXT("/Game/Maps/M_WaterPhysicsTest"),
        TEXT("/Game/Maps/M_WaterSmallWavesTest"), TEXT("/Game/Maps/M_WaterHighWavesTest") };
    return Values;
}

bool UBoatFrontendSubsystem::IsFrontend(UWorld* World)
{
    if (!World) return false;
    const FString Name = World->GetOutermost()->GetName();
    return Name.EndsWith(TEXT("M_MainMenu")) || Name.EndsWith(TEXT("M_Garage"));
}

void UBoatFrontendSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
    Super::Initialize(Collection);
    const UBoatFrontendSettings* Settings = GetDefault<UBoatFrontendSettings>();
    for (const auto& Reference : Settings->Boats)
        if (UBoatDefinition* Boat = Reference.LoadSynchronous())
            if (!Boat->Id.IsNone() && Boat->PawnClass.LoadSynchronous()) Boats.Add(Boat);
    for (const auto& Reference : Settings->Engines)
        if (UBoatEngineDefinition* Engine = Reference.LoadSynchronous())
            if (!Engine->Id.IsNone() && Engine->IdleRPM >= 0 && Engine->LoadedMaxRPM > Engine->IdleRPM &&
                Engine->FreeMaxRPM >= Engine->LoadedMaxRPM && Engine->ShaftRatio > 0 && Engine->ShaftFullRPM > 0 &&
                FMath::IsFinite(Engine->DriveForce) && FMath::IsFinite(Engine->EngineMassKg) &&
                Engine->DriveForce >= 0 && Engine->EngineMassKg >= 0) Engines.Add(Engine);
    Selection = Cast<UBoatFrontendSave>(UGameplayStatics::LoadGameFromSlot(BoatFrontend::Slot, 0));
    if (!Selection || Selection->Version != 1) Selection = NewObject<UBoatFrontendSave>(this);
    ValidateSelection();
    WorldHandle = FWorldDelegates::OnWorldInitializedActors.AddUObject(this, &UBoatFrontendSubsystem::WorldReady);
}

void UBoatFrontendSubsystem::Deinitialize()
{
    FWorldDelegates::OnWorldInitializedActors.Remove(WorldHandle);
    Super::Deinitialize();
}

UBoatDefinition* UBoatFrontendSubsystem::CurrentBoat() const
{
    for (UBoatDefinition* Boat : Boats) if (Boat->Id == Selection->BoatId) return Boat;
    return Boats.IsEmpty() ? nullptr : Boats[0];
}

bool UBoatFrontendSubsystem::IsCompatible(const UBoatEngineDefinition* Engine) const
{
    const UBoatDefinition* Boat = CurrentBoat();
    return Boat && Engine && (Boat->CompatibleEngines.IsEmpty() || Boat->CompatibleEngines.Contains(Engine->Id));
}

UBoatEngineDefinition* UBoatFrontendSubsystem::CurrentEngine() const
{
    for (UBoatEngineDefinition* Engine : Engines)
        if (Engine->Id == Selection->EngineId && IsCompatible(Engine)) return Engine;
    for (UBoatEngineDefinition* Engine : Engines) if (IsCompatible(Engine)) return Engine;
    return nullptr;
}

void UBoatFrontendSubsystem::ValidateSelection()
{
    if (UBoatDefinition* Boat = CurrentBoat()) Selection->BoatId = Boat->Id;
    else Selection->BoatId = NAME_None;
    if (UBoatEngineDefinition* Engine = CurrentEngine()) Selection->EngineId = Engine->Id;
    else Selection->EngineId = NAME_None;
    if (!Maps().Contains(Selection->Map)) Selection->Map = Maps()[0];
    Selection->MasterVolume = FMath::IsFinite(Selection->MasterVolume) ? FMath::Clamp(Selection->MasterVolume, 0.f, 1.f) : 0.8f;
    Selection->HUDScale = FMath::IsFinite(Selection->HUDScale) ? FMath::Clamp(Selection->HUDScale, 0.75f, 1.5f) : 1.f;
}

bool UBoatFrontendSubsystem::Save()
{
    ValidateSelection();
    return UGameplayStatics::SaveGameToSlot(Selection, BoatFrontend::Slot, 0);
}

void UBoatFrontendSubsystem::ApplyAudio(UWorld* World)
{
    const UBoatFrontendSettings* Settings = GetDefault<UBoatFrontendSettings>();
    USoundMix* Mix = Settings->MasterMix.LoadSynchronous();
    USoundClass* SoundClass = Settings->MasterClass.LoadSynchronous();
    if (Mix && SoundClass)
    {
        UGameplayStatics::SetBaseSoundMix(World, Mix);
        UGameplayStatics::SetSoundMixClassOverride(World, Mix, SoundClass, Selection->MasterVolume, 1.f, 0.1f, true);
    }
}

void UBoatFrontendSubsystem::ConfigurePawn(APawn* Pawn)
{
    UBoatDefinition* Boat = CurrentBoat();
    UBoatEngineDefinition* Engine = CurrentEngine();
    if (!Pawn || !Boat || !Engine) return;
    FObjectPropertyBase* Property = FindFProperty<FObjectPropertyBase>(Pawn->GetClass(), TEXT("HandlingProfile"));
    if (!Property) return;
    UObject* Original = Property->GetObjectPropertyValue_InContainer(Pawn);
    if (!Original) Original = Boat->HandlingProfile.LoadSynchronous();
    if (!Original) return;
    UObject* Profile = DuplicateObject(Original, Pawn);
    Profile->SetFlags(RF_Transient);
    double Force = Engine->DriveForce > 0 ? Engine->DriveForce : BoatFrontend::ReadNumber(Profile, TEXT("DriveForce"));
    BoatFrontend::WriteNumber(Profile, TEXT("DriveForce"), Force * (Selection->Sport ? 1.1 : 1.0));
    if (Engine->EngineMassKg > 0) BoatFrontend::WriteNumber(Profile, TEXT("EngineMassKg"), Engine->EngineMassKg);
    Property->SetObjectPropertyValue_InContainer(Pawn, Profile);
    BoatFrontend::WriteNumber(Pawn, TEXT("UIIdleRPM"), Engine->IdleRPM);
    BoatFrontend::WriteNumber(Pawn, TEXT("UILoadedMaxRPM"), Engine->LoadedMaxRPM);
    BoatFrontend::WriteNumber(Pawn, TEXT("UIFreeMaxRPM"), Engine->FreeMaxRPM);
    BoatFrontend::WriteNumber(Pawn, TEXT("UIShaftRatio"), Engine->ShaftRatio);
    BoatFrontend::WriteNumber(Pawn, TEXT("UIShaftFullRPM"), Engine->ShaftFullRPM);
}

void UBoatFrontendSubsystem::WorldReady(const UWorld::FActorsInitializedParams& Params)
{
    UWorld* World = Params.World;
    if (!World || !World->IsGameWorld() || World->GetGameInstance() != GetGameInstance()) return;
    ValidateSelection();
    if (!IsFrontend(World))
    {
        UBoatDefinition* Boat = CurrentBoat();
        UClass* SelectedClass = Boat ? Boat->PawnClass.LoadSynchronous() : nullptr;
        TArray<APawn*> Candidates;
        for (TActorIterator<APawn> Iterator(World); Iterator; ++Iterator)
            if (FindFProperty<FObjectPropertyBase>(Iterator->GetClass(), TEXT("HandlingProfile"))) Candidates.Add(*Iterator);
        for (APawn* Pawn : Candidates)
        {
            if (SelectedClass && Pawn->GetClass() != SelectedClass)
            {
                const FTransform Transform = Pawn->GetActorTransform();
                const EAutoReceiveInput::Type Possess = Pawn->AutoPossessPlayer;
                Pawn->Destroy();
                APawn* Replacement = World->SpawnActorDeferred<APawn>(SelectedClass, Transform, nullptr, nullptr, ESpawnActorCollisionHandlingMethod::AlwaysSpawn);
                if (Replacement)
                {
                    Replacement->AutoPossessPlayer = Possess;
                    ConfigurePawn(Replacement);
                    Replacement->FinishSpawning(Transform);
                }
            }
            else ConfigurePawn(Pawn);
        }
    }
    World->SpawnActor<ABoatUIHost>();
}

ABoatUIHost::ABoatUIHost()
{
    PrimaryActorTick.bCanEverTick = true;
    PrimaryActorTick.bTickEvenWhenPaused = true;
}

void ABoatUIHost::Tick(float DeltaSeconds)
{
    Super::Tick(DeltaSeconds);
    APlayerController* Controller = UGameplayStatics::GetPlayerController(this, 0);
    if (!Controller || Screen) return;
    EnableInput(Controller);
    InputComponent->BindKey(EKeys::Escape, IE_Pressed, this, &ABoatUIHost::TogglePause).bExecuteWhenPaused = true;
    Screen = CreateWidget<UBoatFrontendWidget>(Controller);
    Screen->Host = this;
    if (UBoatFrontendSubsystem::IsFrontend(GetWorld()))
    {
        BuildPreview();
        Screen->Build(GetWorld()->GetOutermost()->GetName().EndsWith(TEXT("M_Garage")) ? TEXT("garage") : TEXT("main"));
        Screen->AddToViewport(100);
        Controller->bShowMouseCursor = true;
        FInputModeUIOnly Mode;
        Mode.SetWidgetToFocus(Screen->TakeWidget());
        Controller->SetInputMode(Mode);
    }
    else
    {
        Screen->Build(TEXT("hud"));
        Screen->AddToViewport(100);
        Controller->bShowMouseCursor = false;
        Controller->SetInputMode(FInputModeGameOnly());
    }
    GetGameInstance()->GetSubsystem<UBoatFrontendSubsystem>()->ApplyAudio(GetWorld());
}

void ABoatUIHost::TogglePause()
{
    if (!UBoatFrontendSubsystem::IsFrontend(GetWorld())) SetPaused(!bPaused);
}

void ABoatUIHost::SetPaused(bool Paused)
{
    APlayerController* Controller = UGameplayStatics::GetPlayerController(this, 0);
    if (!Controller || !Screen) return;
    bPaused = Paused;
    UGameplayStatics::SetGamePaused(this, Paused);
    Controller->bShowMouseCursor = Paused;
    if (Paused)
    {
        Screen->Build(TEXT("pause"));
        FInputModeGameAndUI Mode;
        Mode.SetWidgetToFocus(Screen->TakeWidget());
        Mode.SetHideCursorDuringCapture(false);
        Controller->SetInputMode(Mode);
    }
    else
    {
        Screen->Build(TEXT("hud"));
        Controller->SetInputMode(FInputModeGameOnly());
        Controller->FlushPressedKeys();
    }
}

void ABoatUIHost::BuildPreview()
{
    if (Preview) Preview->Destroy();
    UBoatDefinition* Boat = GetGameInstance()->GetSubsystem<UBoatFrontendSubsystem>()->CurrentBoat();
    if (!Boat) return;
    Preview = GetWorld()->SpawnActor<AActor>();
    USceneComponent* Root = NewObject<USceneComponent>(Preview);
    Preview->SetRootComponent(Root);
    Preview->AddInstanceComponent(Root);
    Root->RegisterComponent();
    for (const FBoatPreviewPart& Part : Boat->PreviewParts)
    {
        UMeshComponent* Mesh = nullptr;
        if (UStaticMesh* Asset = Part.StaticMesh.LoadSynchronous())
        {
            UStaticMeshComponent* Component = NewObject<UStaticMeshComponent>(Preview);
            Component->SetStaticMesh(Asset);
            Mesh = Component;
        }
        else if (USkeletalMesh* Asset = Part.SkeletalMesh.LoadSynchronous())
        {
            USkeletalMeshComponent* Component = NewObject<USkeletalMeshComponent>(Preview);
            Component->SetSkeletalMeshAsset(Asset);
            Mesh = Component;
        }
        if (!Mesh) continue;
        Preview->AddInstanceComponent(Mesh);
        for (int32 Index = 0; Index < Part.Materials.Num(); ++Index)
            if (UMaterialInterface* Material = Part.Materials[Index].LoadSynchronous()) Mesh->SetMaterial(Index, Material);
        Mesh->SetupAttachment(Root);
        Mesh->SetRelativeTransform(Part.Transform);
        Mesh->SetCollisionEnabled(ECollisionEnabled::NoCollision);
        Mesh->SetSimulatePhysics(false);
        Mesh->RegisterComponent();
    }
    Preview->SetActorRotation(FRotator(0, 25, 0));
    if (!PreviewCamera) PreviewCamera = GetWorld()->SpawnActor<ACameraActor>();
    FVector Center, Extent;
    Preview->GetActorBounds(false, Center, Extent);
    const float Radius = FMath::Max(Extent.Size(), 250.f);
    PreviewCamera->SetActorLocation(Center + FVector(-1.15f, -1.5f, 0.8f) * Radius);
    PreviewCamera->SetActorRotation((Center - PreviewCamera->GetActorLocation()).Rotation());
    Cast<ACameraActor>(PreviewCamera)->GetCameraComponent()->SetFieldOfView(45);
    if (APlayerController* Controller = UGameplayStatics::GetPlayerController(this, 0)) Controller->SetViewTarget(PreviewCamera);
}

void ABoatUIHost::RotatePreview(float Degrees)
{
    if (Preview) Preview->AddActorWorldRotation(FRotator(0, Degrees, 0));
}

void ABoatUIHost::EndPlay(const EEndPlayReason::Type Reason)
{
    if (Screen) Screen->RemoveFromParent();
    if (Preview) Preview->Destroy();
    if (PreviewCamera) PreviewCamera->Destroy();
    Super::EndPlay(Reason);
}

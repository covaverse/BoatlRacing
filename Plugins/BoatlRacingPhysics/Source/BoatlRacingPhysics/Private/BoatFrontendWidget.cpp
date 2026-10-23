#include "BoatFrontend.h"
#include "Blueprint/WidgetTree.h"
#include "Components/Border.h"
#include "Components/Button.h"
#include "Components/CanvasPanel.h"
#include "Components/CanvasPanelSlot.h"
#include "Components/HorizontalBox.h"
#include "Components/HorizontalBoxSlot.h"
#include "Components/Image.h"
#include "Components/ProgressBar.h"
#include "Components/ScrollBox.h"
#include "Components/SizeBox.h"
#include "Components/Slider.h"
#include "Components/TextBlock.h"
#include "Components/VerticalBox.h"
#include "Components/VerticalBoxSlot.h"
#include "Components/PrimitiveComponent.h"
#include "Engine/Texture2D.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "Kismet/GameplayStatics.h"
#include "Rendering/DrawElements.h"
#include "UObject/UnrealType.h"

namespace BoatUI
{
    const FLinearColor Cyan(0.05f, 0.78f, 1.f);
    const FLinearColor Muted(0.55f, 0.66f, 0.74f);
    const FLinearColor Panel(0.012f, 0.025f, 0.042f, 0.94f);

    UTextBlock* Text(UWidgetTree* Tree, const FString& Value, int32 Size = 20, FLinearColor Color = FLinearColor::White)
    {
        UTextBlock* Widget = Tree->ConstructWidget<UTextBlock>();
        Widget->SetText(FText::FromString(Value));
        FSlateFontInfo Font = Widget->GetFont();
        Font.Size = Size;
        Widget->SetFont(Font);
        Widget->SetColorAndOpacity(FSlateColor(Color));
        Widget->SetAutoWrapText(true);
        return Widget;
    }

    void Line(UVerticalBox* Box, UWidget* Widget, float Padding = 8)
    {
        Box->AddChildToVerticalBox(Widget)->SetPadding(FMargin(0, Padding));
    }

    UBorder* Card(UWidgetTree* Tree, UWidget* Content)
    {
        UBorder* Border = Tree->ConstructWidget<UBorder>();
        Border->SetBrushColor(Panel);
        Border->SetPadding(FMargin(24));
        Border->SetContent(Content);
        return Border;
    }

    double Number(UObject* Object, FName Name)
    {
        const FNumericProperty* Property = Object ? FindFProperty<FNumericProperty>(Object->GetClass(), Name) : nullptr;
        if (!Property) return 0;
        const void* Address = Property->ContainerPtrToValuePtr<void>(Object);
        return Property->IsFloatingPoint() ? Property->GetFloatingPointPropertyValue(Address) : Property->GetSignedIntPropertyValue(Address);
    }

    bool Boolean(UObject* Object, FName Name)
    {
        const FBoolProperty* Property = Object ? FindFProperty<FBoolProperty>(Object->GetClass(), Name) : nullptr;
        return Property && Property->GetPropertyValue_InContainer(Object);
    }

    FVector Velocity(APawn* Pawn)
    {
        if (!Pawn) return FVector::ZeroVector;
        const FObjectPropertyBase* Property = FindFProperty<FObjectPropertyBase>(Pawn->GetClass(), TEXT("StaticMesh"));
        if (Property)
            if (UPrimitiveComponent* Hull = Cast<UPrimitiveComponent>(Property->GetObjectPropertyValue_InContainer(Pawn)))
                return Hull->GetComponentVelocity();
        return Pawn->GetVelocity();
    }
}

void UBoatMenuAction::Invoke()
{
    if (Screen) Screen->Dispatch(Action, Value);
}

UBoatFrontendSubsystem* UBoatFrontendWidget::Data() const
{
    return GetGameInstance()->GetSubsystem<UBoatFrontendSubsystem>();
}

void UBoatFrontendWidget::Build(const FString& Page)
{
    CurrentPage = Page;
    SetIsFocusable(true);
    SpeedText = nullptr;
    StateText = nullptr;
    RPMText = nullptr;
    ThrottleBar = nullptr;
    Dial = nullptr;
    Feedback = nullptr;
    HUDPanel = nullptr;
    Actions.Reset();
    UCanvasPanel* Canvas = Cast<UCanvasPanel>(WidgetTree->RootWidget);
    if (Canvas) Canvas->ClearChildren();
    else Canvas = WidgetTree->ConstructWidget<UCanvasPanel>();
    Canvas->SetVisibility(ESlateVisibility::Visible);
    WidgetTree->RootWidget = Canvas;
    auto Position = [Canvas](UWidget* Widget, FVector2D Offset, FVector2D Size, FVector2D Anchor = FVector2D::ZeroVector, FVector2D Alignment = FVector2D::ZeroVector)
    {
        UCanvasPanelSlot* Slot = Canvas->AddChildToCanvas(Widget);
        Slot->SetAnchors(FAnchors(Anchor.X, Anchor.Y));
        Slot->SetAlignment(Alignment);
        Slot->SetPosition(Offset);
        Slot->SetSize(Size);
        return Slot;
    };
    auto Button = [this](UVerticalBox* Box, const FString& Label, const FString& Action, const FString& Value = FString())
    {
        UButton* Widget = WidgetTree->ConstructWidget<UButton>();
        Widget->SetBackgroundColor(FLinearColor(0.035f, 0.11f, 0.17f));
        UTextBlock* Caption = BoatUI::Text(WidgetTree, Label, 19);
        Caption->SetMargin(FMargin(16, 12));
        Widget->SetContent(Caption);
        UBoatMenuAction* Handler = NewObject<UBoatMenuAction>(this);
        Handler->Screen = this;
        Handler->Action = Action;
        Handler->Value = Value;
        Actions.Add(Handler);
        Widget->OnClicked.AddDynamic(Handler, &UBoatMenuAction::Invoke);
        BoatUI::Line(Box, Widget, 4);
        return Widget;
    };
    auto Thumbnail = [this](UVerticalBox* Box, UTexture2D* Texture, const FString& Missing)
    {
        if (Texture)
        {
            UImage* Image = WidgetTree->ConstructWidget<UImage>();
            Image->SetBrushFromTexture(Texture);
            USizeBox* Size = WidgetTree->ConstructWidget<USizeBox>();
            Size->SetHeightOverride(115);
            Size->SetContent(Image);
            BoatUI::Line(Box, Size);
        }
        else BoatUI::Line(Box, BoatUI::Text(WidgetTree, Missing, 16, BoatUI::Muted));
    };
    if (Page == TEXT("hud"))
    {
        Canvas->SetVisibility(ESlateVisibility::HitTestInvisible);
        UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
        UHorizontalBox* Top = WidgetTree->ConstructWidget<UHorizontalBox>();
        SpeedText = BoatUI::Text(WidgetTree, TEXT("000"), 72);
        Top->AddChildToHorizontalBox(SpeedText);
        UTextBlock* Unit = BoatUI::Text(WidgetTree, TEXT("KM/H"), 16, BoatUI::Cyan);
        UHorizontalBoxSlot* UnitSlot = Top->AddChildToHorizontalBox(Unit);
        UnitSlot->SetVerticalAlignment(VAlign_Bottom);
        UnitSlot->SetPadding(FMargin(12, 0, 0, 15));
        BoatUI::Line(Stack, Top, 0);
        Dial = WidgetTree->ConstructWidget<UBoatRPMWidget>();
        USizeBox* DialSize = WidgetTree->ConstructWidget<USizeBox>();
        DialSize->SetHeightOverride(82);
        DialSize->SetContent(Dial);
        BoatUI::Line(Stack, DialSize, 0);
        RPMText = BoatUI::Text(WidgetTree, TEXT("0 RPM"), 18, BoatUI::Cyan);
        BoatUI::Line(Stack, RPMText, 0);
        ThrottleBar = WidgetTree->ConstructWidget<UProgressBar>();
        ThrottleBar->SetFillColorAndOpacity(BoatUI::Cyan);
        USizeBox* Bar = WidgetTree->ConstructWidget<USizeBox>();
        Bar->SetHeightOverride(5);
        Bar->SetContent(ThrottleBar);
        BoatUI::Line(Stack, Bar, 10);
        StateText = BoatUI::Text(WidgetTree, TEXT("CLUTCH ENGAGED   TRIM 0°"), 15, BoatUI::Muted);
        BoatUI::Line(Stack, StateText, 0);
        HUDPanel = BoatUI::Card(WidgetTree, Stack);
        Position(HUDPanel, FVector2D(-35, -35), FVector2D(320, 270), FVector2D(1, 1), FVector2D(1, 1));
        HUDPanel->SetRenderTransformPivot(FVector2D(1, 1));
        HUDPanel->SetRenderScale(FVector2D(Data()->Selection->HUDScale));
        Position(BoatUI::Text(WidgetTree, TEXT("FREE DRIVE   /   ESC PAUSE"), 16, BoatUI::Muted), FVector2D(35, 30), FVector2D(430, 40));
        return;
    }
    if (Page != TEXT("garage") && Page != TEXT("main"))
    {
        UBorder* Shade = WidgetTree->ConstructWidget<UBorder>();
        Shade->SetBrushColor(FLinearColor(0.005f, 0.015f, 0.03f, 0.78f));
        UCanvasPanelSlot* ShadeSlot = Canvas->AddChildToCanvas(Shade);
        ShadeSlot->SetAnchors(FAnchors(0, 0, 1, 1));
        ShadeSlot->SetOffsets(FMargin(0));
    }
    Position(BoatUI::Text(WidgetTree, TEXT("BOATL / RACING"), 36), FVector2D(45, 30), FVector2D(650, 60));
    Position(BoatUI::Text(WidgetTree, TEXT("THAI LONGTAIL  •  FREE DRIVE"), 14, BoatUI::Cyan), FVector2D(48, 90), FVector2D(600, 35));
    UVerticalBox* Stack = WidgetTree->ConstructWidget<UVerticalBox>();
    UBoatFrontendSubsystem* State = Data();
    if (Page == TEXT("main"))
    {
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("READY FOR THE WATER"), 25));
        Button(Stack, TEXT("FREE DRIVE / ขับอิสระ"), TEXT("page"), TEXT("maps"));
        Button(Stack, TEXT("GARAGE / โรงรถ"), TEXT("garage"));
        Button(Stack, TEXT("SETTINGS / ตั้งค่า"), TEXT("page"), TEXT("settings"));
        Button(Stack, TEXT("QUIT / ออกเกม"), TEXT("quit"));
    }
    else if (Page == TEXT("maps"))
    {
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("SELECT WATER / เลือกสนาม"), 24));
        const TArray<FString> Names = { TEXT("CANAL / คลอง"), TEXT("CALM WATER / น้ำนิ่ง"), TEXT("SMALL WAVES / คลื่นเล็ก"), TEXT("HIGH WAVES / คลื่นสูง") };
        for (int32 Index = 0; Index < Names.Num(); ++Index)
            Button(Stack, (State->Selection->Map == UBoatFrontendSubsystem::Maps()[Index] ? TEXT("● ") : TEXT("○ ")) + Names[Index], TEXT("map"), UBoatFrontendSubsystem::Maps()[Index]);
        UButton* Start = Button(Stack, TEXT("START DRIVE / เริ่มขับ"), TEXT("drive"));
        Start->SetIsEnabled(State->CurrentBoat() && State->CurrentEngine());
        Button(Stack, TEXT("BACK / กลับ"), TEXT("page"), TEXT("main"));
    }
    else if (Page == TEXT("garage"))
    {
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("GARAGE / โรงรถ"), 24));
        for (UBoatDefinition* Boat : State->Boats)
            Button(Stack, (State->Selection->BoatId == Boat->Id ? TEXT("● ") : TEXT("○ ")) + Boat->DisplayName.ToString(), TEXT("boat"), Boat->Id.ToString());
        UBoatDefinition* Boat = State->CurrentBoat();
        if (Boat)
        {
            Thumbnail(Stack, Boat->Thumbnail.LoadSynchronous(), TEXT("NO THUMBNAIL / ดูเรือ 3D ด้านข้าง"));
            BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("ENGINE / เครื่องยนต์"), 18, BoatUI::Cyan));
            for (UBoatEngineDefinition* Engine : State->Engines)
                if (State->IsCompatible(Engine)) Button(Stack, (State->Selection->EngineId == Engine->Id ? TEXT("● ") : TEXT("○ ")) + Engine->DisplayName.ToString(), TEXT("engine"), Engine->Id.ToString());
            if (UBoatEngineDefinition* Engine = State->CurrentEngine())
            {
                Thumbnail(Stack, Engine->Thumbnail.LoadSynchronous(), TEXT("ENGINE PREVIEW NOT AVAILABLE / ยังไม่มีภาพเครื่อง"));
                UDataAsset* Profile = Boat->HandlingProfile.LoadSynchronous();
                const double Mass = Engine->EngineMassKg > 0 ? Engine->EngineMassKg : BoatUI::Number(Profile, TEXT("EngineMassKg"));
                const double Force = (Engine->DriveForce > 0 ? Engine->DriveForce : BoatUI::Number(Profile, TEXT("DriveForce"))) * (State->Selection->Sport ? 1.1 : 1);
                BoatUI::Line(Stack, BoatUI::Text(WidgetTree, FString::Printf(TEXT("%.0f–%.0f RPM  |  %.0f kg\nDRIVE %.0f UE units  |  SHAFT ×%.2f"), Engine->IdleRPM, Engine->FreeMaxRPM, Mass, Force, Engine->ShaftRatio), 16, BoatUI::Muted));
            }
            Button(Stack, State->Selection->Sport ? TEXT("○ STOCK / ค่าเดิม") : TEXT("● STOCK / ค่าเดิม"), TEXT("tune"), TEXT("stock"));
            Button(Stack, State->Selection->Sport ? TEXT("● SPORT / แรงขับ +10%") : TEXT("○ SPORT / แรงขับ +10%"), TEXT("tune"), TEXT("sport"));
        }
        else BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("NO BOATS CONFIGURED / ยังไม่มีข้อมูลเรือ"), 18));
        Button(Stack, TEXT("ROTATE LEFT / หมุนซ้าย"), TEXT("rotate"), TEXT("-15"));
        Button(Stack, TEXT("ROTATE RIGHT / หมุนขวา"), TEXT("rotate"), TEXT("15"));
        Button(Stack, TEXT("FREE DRIVE / ไปขับ"), TEXT("page"), TEXT("maps"));
        Button(Stack, TEXT("MAIN MENU / เมนูหลัก"), TEXT("main"));
        Position(BoatUI::Text(WidgetTree, TEXT("DRAG TO ROTATE / ลากเมาส์บนเรือเพื่อหมุน"), 16, BoatUI::Muted), FVector2D(-40, -35), FVector2D(540, 35), FVector2D(1, 1), FVector2D(1, 1));
    }
    else if (Page == TEXT("settings"))
    {
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("SETTINGS / ตั้งค่า"), 24));
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("MASTER VOLUME / เสียงรวม"), 18, BoatUI::Cyan));
        USlider* Volume = WidgetTree->ConstructWidget<USlider>();
        Volume->SetValue(State->Selection->MasterVolume);
        Volume->OnValueChanged.AddDynamic(this, &UBoatFrontendWidget::VolumeChanged);
        BoatUI::Line(Stack, Volume, 18);
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("HUD SCALE / ขนาด HUD  75–150%"), 18, BoatUI::Cyan));
        USlider* Scale = WidgetTree->ConstructWidget<USlider>();
        Scale->SetValue((State->Selection->HUDScale - 0.75f) / 0.75f);
        Scale->OnValueChanged.AddDynamic(this, &UBoatFrontendWidget::ScaleChanged);
        BoatUI::Line(Stack, Scale, 18);
        Button(Stack, TEXT("SAVE & BACK / บันทึกและกลับ"), TEXT("settings_back"));
    }
    else if (Page == TEXT("pause"))
    {
        BoatUI::Line(Stack, BoatUI::Text(WidgetTree, TEXT("PAUSED / หยุดพัก"), 28));
        Button(Stack, TEXT("RESUME / เล่นต่อ"), TEXT("resume"));
        Button(Stack, TEXT("RESTART / เริ่มใหม่"), TEXT("restart"));
        Button(Stack, TEXT("SETTINGS / ตั้งค่า"), TEXT("page"), TEXT("settings"));
        Button(Stack, TEXT("MAIN MENU / เมนูหลัก"), TEXT("main"));
    }
    Feedback = BoatUI::Text(WidgetTree, TEXT(""), 14, BoatUI::Cyan);
    BoatUI::Line(Stack, Feedback, 4);
    UScrollBox* Scroll = WidgetTree->ConstructWidget<UScrollBox>();
    Scroll->AddChild(Stack);
    Position(BoatUI::Card(WidgetTree, Scroll), FVector2D(45, 140), FVector2D(400, 0))->SetAutoSize(false);
    UCanvasPanelSlot* PanelSlot = Cast<UCanvasPanelSlot>(Scroll->GetParent()->Slot);
    PanelSlot->SetAnchors(FAnchors(0, 0, 0, 1));
    PanelSlot->SetOffsets(FMargin(45, 140, 400, 35));
}

void UBoatFrontendWidget::Persist()
{
    if (Feedback) Feedback->SetText(FText::FromString(Data()->Save() ? TEXT("SAVED / บันทึกแล้ว") : TEXT("SAVE FAILED / บันทึกไม่สำเร็จ")));
    else Data()->Save();
}

void UBoatFrontendWidget::Dispatch(const FString& Action, const FString& Value)
{
    UBoatFrontendSubsystem* State = Data();
    if (Action == TEXT("page")) { Build(Value); return; }
    if (Action == TEXT("boat"))
    {
        State->Selection->BoatId = FName(Value);
        State->ValidateSelection();
        Host->BuildPreview();
        Build(TEXT("garage"));
        Persist();
    }
    else if (Action == TEXT("engine")) { State->Selection->EngineId = FName(Value); Build(TEXT("garage")); Persist(); }
    else if (Action == TEXT("tune")) { State->Selection->Sport = Value == TEXT("sport"); Build(TEXT("garage")); Persist(); }
    else if (Action == TEXT("map")) { State->Selection->Map = Value; Build(TEXT("maps")); Persist(); }
    else if (Action == TEXT("rotate")) Host->RotatePreview(FCString::Atof(*Value));
    else if (Action == TEXT("resume")) Host->SetPaused(false);
    else if (Action == TEXT("settings_back")) { Build(Host->bPaused ? TEXT("pause") : TEXT("main")); Persist(); }
    else if (Action == TEXT("quit")) UGameplayStatics::QuitGame(this, GetOwningPlayer(), EQuitPreference::Quit, false);
    else if (Action == TEXT("drive") || Action == TEXT("restart") || Action == TEXT("main") || Action == TEXT("garage"))
    {
        State->ValidateSelection();
        if (Action == TEXT("drive") && (!State->CurrentBoat() || !State->CurrentEngine())) return;
        if (!State->Save()) { if (Feedback) Feedback->SetText(FText::FromString(TEXT("SAVE FAILED / บันทึกไม่สำเร็จ"))); return; }
        UGameplayStatics::SetGamePaused(this, false);
        Host->bPaused = false;
        GetOwningPlayer()->FlushPressedKeys();
        const FString Map = Action == TEXT("main") ? TEXT("/Game/Maps/M_MainMenu") : Action == TEXT("garage") ? TEXT("/Game/Maps/M_Garage") : Action == TEXT("restart") ? GetWorld()->GetOutermost()->GetName().Replace(*GetWorld()->StreamingLevelsPrefix, TEXT("")) : State->Selection->Map;
        UGameplayStatics::OpenLevel(this, FName(Map));
    }
}

void UBoatFrontendWidget::VolumeChanged(float Value)
{
    Data()->Selection->MasterVolume = FMath::Clamp(Value, 0.f, 1.f);
    Data()->ApplyAudio(GetWorld());
    Persist();
}

void UBoatFrontendWidget::ScaleChanged(float Value)
{
    Data()->Selection->HUDScale = 0.75f + FMath::Clamp(Value, 0.f, 1.f) * 0.75f;
    Persist();
}

FReply UBoatFrontendWidget::NativeOnKeyDown(const FGeometry& Geometry, const FKeyEvent& Event)
{
    if (Event.GetKey() == EKeys::Escape)
    {
        if (Host->bPaused) Host->SetPaused(false);
        else if (CurrentPage != TEXT("main")) Build(TEXT("main"));
        return FReply::Handled();
    }
    return Super::NativeOnKeyDown(Geometry, Event);
}

FReply UBoatFrontendWidget::NativeOnMouseButtonDown(const FGeometry& Geometry, const FPointerEvent& Event)
{
    if (CurrentPage == TEXT("garage") && Event.GetEffectingButton() == EKeys::LeftMouseButton &&
        Geometry.AbsoluteToLocal(Event.GetScreenSpacePosition()).X > 470)
    {
        bDragging = true;
        return FReply::Handled().CaptureMouse(TakeWidget());
    }
    return Super::NativeOnMouseButtonDown(Geometry, Event);
}

FReply UBoatFrontendWidget::NativeOnMouseMove(const FGeometry& Geometry, const FPointerEvent& Event)
{
    if (bDragging)
    {
        Host->RotatePreview(Event.GetCursorDelta().X * 0.3f);
        return FReply::Handled();
    }
    return Super::NativeOnMouseMove(Geometry, Event);
}

FReply UBoatFrontendWidget::NativeOnMouseButtonUp(const FGeometry& Geometry, const FPointerEvent& Event)
{
    if (bDragging && Event.GetEffectingButton() == EKeys::LeftMouseButton)
    {
        bDragging = false;
        return FReply::Handled().ReleaseMouseCapture();
    }
    return Super::NativeOnMouseButtonUp(Geometry, Event);
}

void UBoatFrontendWidget::NativeTick(const FGeometry& Geometry, float DeltaSeconds)
{
    Super::NativeTick(Geometry, DeltaSeconds);
    if (!SpeedText) return;
    APawn* Pawn = GetOwningPlayer()->GetPawn();
    const FVector Velocity = BoatUI::Velocity(Pawn);
    SpeedText->SetText(FText::AsNumber(FMath::RoundToInt(Velocity.Size2D() * 0.036)));
    const float RPM = BoatUI::Number(Pawn, TEXT("EngineRPM"));
    const UBoatEngineDefinition* Engine = Data()->CurrentEngine();
    Dial->RPM = RPM;
    Dial->Maximum = Engine ? Engine->FreeMaxRPM : 6500;
    Dial->InvalidateLayoutAndVolatility();
    RPMText->SetText(FText::FromString(FString::Printf(TEXT("%.0f RPM"), RPM)));
    const float Throttle = BoatUI::Number(Pawn, TEXT("Throttle"));
    ThrottleBar->SetPercent(FMath::Abs(Throttle));
    StateText->SetText(FText::FromString(FString::Printf(TEXT("%s  |  CLUTCH %s\nTRIM %+.1f°  |  THROTTLE %.0f%%"), Throttle < 0 ? TEXT("REV") : TEXT("FWD"), BoatUI::Boolean(Pawn, TEXT("ClutchHeld")) ? TEXT("OPEN") : TEXT("ENGAGED"), BoatUI::Number(Pawn, TEXT("TrimDegrees")), FMath::Abs(Throttle) * 100)));
}

int32 UBoatRPMWidget::NativePaint(const FPaintArgs& Args, const FGeometry& Geometry, const FSlateRect& Culling,
    FSlateWindowElementList& Elements, int32 Layer, const FWidgetStyle& Style, bool Enabled) const
{
    const int32 Base = Super::NativePaint(Args, Geometry, Culling, Elements, Layer, Style, Enabled);
    const FVector2D Size = Geometry.GetLocalSize();
    const FVector2D Center(Size.X * 0.5, Size.Y - 5);
    const float Radius = FMath::Min(Size.X * 0.47f, Size.Y - 10);
    const float Fraction = FMath::Clamp(RPM / FMath::Max(Maximum, 1.f), 0.f, 1.f);
    for (int32 Segment = 0; Segment < 40; ++Segment)
    {
        TArray<FVector2D> Points;
        const float Start = PI + PI * Segment / 40.f;
        const float End = Start + PI * 0.75f / 40.f;
        Points.Add(Center + FVector2D(FMath::Cos(Start), FMath::Sin(Start)) * Radius);
        Points.Add(Center + FVector2D(FMath::Cos(End), FMath::Sin(End)) * Radius);
        const FLinearColor Color = Segment >= 34 ? FLinearColor(1, 0.15f, 0.12f) : Segment / 40.f <= Fraction ? BoatUI::Cyan : FLinearColor(0.13f, 0.22f, 0.28f);
        FSlateDrawElement::MakeLines(Elements, Base + 1, Geometry.ToPaintGeometry(), Points, ESlateDrawEffect::None, Color, true, 4);
    }
    const float Angle = PI + PI * Fraction;
    TArray<FVector2D> Needle = { Center, Center + FVector2D(FMath::Cos(Angle), FMath::Sin(Angle)) * (Radius - 8) };
    FSlateDrawElement::MakeLines(Elements, Base + 2, Geometry.ToPaintGeometry(), Needle, ESlateDrawEffect::None, FLinearColor::White, true, 2);
    return Base + 2;
}

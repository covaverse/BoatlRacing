#pragma once

#include "Components/ActorComponent.h"
#include "BoatRippleFieldComponent.generated.h"

class UBuoyancyComponent;
class UTextureRenderTarget2D;
struct FBoatRippleReadback;

/**
 * อ่านความสูงของสนามคลื่น GPU (NormalRT ของ Ripple Solver) กลับมาฝั่ง CPU แบบไม่หยุดเธรดเรนเดอร์
 * แล้วเติมแรงลอยตัวส่วนที่ระลอกคลื่นทำให้ต่างจากผิวน้ำ Gerstner ที่ทุ่นใช้อยู่เดิม
 * เรือจึงรู้สึกถึงคลื่นจากใบพัด หัวเรือ และคลื่นของเรือลำอื่นที่วิ่งตัดผ่าน
 */
UCLASS(ClassGroup = (Boat), meta = (BlueprintSpawnableComponent))
class BOATLRACINGPHYSICS_API UBoatRippleFieldComponent : public UActorComponent
{
    GENERATED_BODY()

public:
    UBoatRippleFieldComponent();
    virtual ~UBoatRippleFieldComponent() override;

    /** ด้านของหน้าต่างที่อ่านกลับ หน่วยเซลล์ ต้องกว้างคลุมลำเรือบวกระยะที่แล่นไปได้ระหว่างรอ readback */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boat|Ripple", meta = (ClampMin = "32", ClampMax = "1024"))
    int32 WindowCells = 256;

    /** เพดานความสูงระลอกที่ยอมรับ กันค่าผิดเพี้ยนจาก GPU ดีดลำเรือ */
    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boat|Ripple", meta = (ClampMin = "0"))
    float MaxRippleHeightCm = 50.0f;

    UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Boat|Ripple")
    bool bEnabled = true;

    /** เรียกทุกเฟรมก่อน ApplyRippleBuoyancy ส่งค่าปัจจุบันของ Ripple Solver เข้ามา */
    UFUNCTION(BlueprintCallable, Category = "Boat|Ripple")
    bool UpdateRippleField(UTextureRenderTarget2D* NormalHeightRT, FVector GridCenter,
        float SimulationWorldSizeCm, FVector FocusWorldLocation);

    /** ความสูงระลอก ณ จุดในโลก คืน 0 เมื่อยังไม่มีเฟรมหรืออยู่นอกหน้าต่าง */
    UFUNCTION(BlueprintPure, Category = "Boat|Ripple")
    float GetRippleHeight(FVector WorldLocation) const;

    /** เติมแรงลอยตัวส่วนเพิ่มที่ทุ่นแต่ละตัว คืนแรงรวมที่ใส่เข้าไปจริงเพื่อใช้ตรวจใน QA */
    UFUNCTION(BlueprintCallable, Category = "Boat|Ripple")
    FVector ApplyRippleBuoyancy(UBuoyancyComponent* Buoyancy);

    /** จำนวนเฟรมที่อ่านกลับสำเร็จ ใช้ยืนยันว่า readback เดินจริง ไม่ใช่ค้างที่ศูนย์ */
    UFUNCTION(BlueprintPure, Category = "Boat|Ripple")
    int32 GetResolvedFrameCount() const;

protected:
    virtual void BeginPlay() override;
    virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;

private:
    TSharedPtr<FBoatRippleReadback, ESPMode::ThreadSafe> State;
};

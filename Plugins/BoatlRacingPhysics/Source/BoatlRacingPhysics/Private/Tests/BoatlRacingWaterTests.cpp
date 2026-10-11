#include "BoatlRacingWaterLibrary.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "BuoyancyComponent.h"
#include "BoatRippleFieldMath.h"
#include "BoatWaterCurrentPolicy.h"
#include "Misc/AutomationTest.h"
#include <limits>

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBoatTailDragTest, "BoatlRacing.Physics.TailDrag",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FBoatTailDragTest::RunTest(const FString& Parameters)
{
    const FVector TiltedNormal(0.3, 0.9, 0.6);
    const FVector Flow(120.0, -50.0, 0.0);
    for (double Heave : {-5000.0, 0.0, 5000.0})
    {
        for (double Forward : {-3000.0, 0.0, 3000.0})
        {
            const FVector Velocity(Forward, 400.0, Heave);
            const FVector Force = UBoatlRacingWaterLibrary::CalculateTailWaterForce(
                Velocity, Flow, TiltedNormal, 1.0f, -10.0f, 0.15f);
            TestTrue(TEXT("Tail drag dissipates water-relative energy"),
                FVector::DotProduct(Force, Velocity - Flow) <= 0.001);
            TestEqual(TEXT("Tail never supports the hull vertically"), Force.Z, 0.0);
            const FVector NoHeave = UBoatlRacingWaterLibrary::CalculateTailWaterForce(
                FVector(Forward, 400.0, 0.0), Flow, TiltedNormal, 1.0f, -10.0f, 0.15f);
            TestTrue(TEXT("Heave does not change horizontal drag"), Force.Equals(NoHeave));
            TestTrue(TEXT("Tail force is bounded"), Force.Size() <= 150000.01);
        }
    }
    TestTrue(TEXT("Rest in still water cannot turn"),
        UBoatlRacingWaterLibrary::CalculateTailWaterForce(FVector::ZeroVector,
            FVector::ZeroVector, TiltedNormal, 1, -10, 0.15f).IsZero());
    TestTrue(TEXT("Dry tail has no drag"),
        UBoatlRacingWaterLibrary::CalculateTailWaterForce(FVector(3000, 0, 0),
            Flow, TiltedNormal, 0, -10, 0.15f).IsZero());
    TestTrue(TEXT("Raised tail has no drag"),
        UBoatlRacingWaterLibrary::CalculateTailWaterForce(FVector(3000, 0, 0),
            Flow, TiltedNormal, 1, 0, 0.15f).IsZero());
    TestTrue(TEXT("Invalid negative damping is rejected"),
        UBoatlRacingWaterLibrary::CalculateTailWaterForce(FVector(3000, 0, 0),
            Flow, TiltedNormal, 1, -10, -0.15f).IsZero());
    TestTrue(TEXT("An invalid water source has no sample"), [&]()
    {
        float Height = 100;
        FVector WaterVelocity(1, 2, 3);
        const bool Valid = UBoatlRacingWaterLibrary::SampleWaveSurface(nullptr,
            FVector::ZeroVector, Height, WaterVelocity);
        return !Valid && Height == 0 && WaterVelocity.IsZero();
    }());
    TestFalse(TEXT("Invalid buoyancy cannot receive radii"),
        UBoatlRacingWaterLibrary::SetHullPontoonRadii(nullptr, 60, 55));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBoatPontoonInitializationTest,
    "BoatlRacing.Physics.PontoonInitialization",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FBoatPontoonInitializationTest::RunTest(const FString& Parameters)
{
    UBuoyancyComponent* Buoyancy = NewObject<UBuoyancyComponent>();
    Buoyancy->BuoyancyData.Pontoons.SetNum(4);
    for (FSphericalPontoon& Pontoon : Buoyancy->BuoyancyData.Pontoons)
    {
        Pontoon.bEnabled = false;
        Pontoon.Radius = 48.0f;
    }
    TestFalse(TEXT("Radii must wait for the component's physics initialization"),
        UBoatlRacingWaterLibrary::SetHullPontoonRadii(Buoyancy, 60, 55));
    for (const FSphericalPontoon& Pontoon : Buoyancy->BuoyancyData.Pontoons)
    {
        TestEqual(TEXT("Rejected initialization leaves radii unchanged"), Pontoon.Radius, 48.0f);
    }
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBoatTailInvalidInputTest,
    "BoatlRacing.Physics.TailInvalidInput",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FBoatTailInvalidInputTest::RunTest(const FString& Parameters)
{
    const float Nan = std::numeric_limits<float>::quiet_NaN();
    const float Infinity = std::numeric_limits<float>::infinity();
    for (float Invalid : {Nan, Infinity, -Infinity})
    {
        TestTrue(TEXT("Invalid velocity is rejected"),
            UBoatlRacingWaterLibrary::CalculateTailWaterForce(
                FVector(Invalid, 0, 0), FVector::ZeroVector, FVector::RightVector,
                1, -10, 0.15f).IsZero());
        TestTrue(TEXT("Invalid coefficient is rejected"),
            UBoatlRacingWaterLibrary::CalculateTailWaterForce(
                FVector(3000, 0, 0), FVector::ZeroVector, FVector::RightVector,
                1, -10, Invalid).IsZero());
    }
    for (FVector Normal : {FVector::ZeroVector, FVector::UpVector})
    {
        TestTrue(TEXT("No horizontal tail normal produces no force"),
            UBoatlRacingWaterLibrary::CalculateTailWaterForce(
                FVector(3000, 400, 5000), FVector::ZeroVector, Normal,
                1, -10, 0.15f).IsZero());
    }
    const FVector ExtremeForce = UBoatlRacingWaterLibrary::CalculateTailWaterForce(
        FVector(1.0e308, 1.0e308, 0), FVector(-1.0e308, -1.0e308, 0),
        FVector::RightVector, 1, -10, 0.15f);
    TestFalse(TEXT("Finite inputs that overflow relative velocity cannot poison Chaos"),
        ExtremeForce.ContainsNaN());
    TestTrue(TEXT("Overflowing relative velocity safely rejects the force"), ExtremeForce.IsZero());
    for (float Trim : {-10.0f, 0.0f})
    {
        const FVector DryForce = UBoatlRacingWaterLibrary::CalculateTailWaterForce(
            FVector(1.0e308, 1.0e308, 0), FVector(-1.0e308, -1.0e308, 0),
            FVector::RightVector, 0, Trim, 0.15f);
        TestTrue(TEXT("Dry extreme input cannot generate force"), DryForce.IsZero());
    }
    TestTrue(TEXT("Raised extreme input cannot generate force"),
        UBoatlRacingWaterLibrary::CalculateTailWaterForce(
            FVector(1.0e308, 1.0e308, 0), FVector(-1.0e308, -1.0e308, 0),
            FVector::RightVector, 1, 0, 0.15f).IsZero());
    TestTrue(TEXT("Huge but representable slip saturates without arithmetic overflow"),
        UBoatlRacingWaterLibrary::CalculateTailWaterForce(
            FVector(0, 1.0e200, 0), FVector::ZeroVector, FVector::RightVector,
            1, -10, 0.15f).Equals(FVector(0, -150000, 0)));
    return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBoatPhysicalCurrentTest,
    "BoatlRacing.Physics.PhysicalCurrent",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FBoatPhysicalCurrentTest::RunTest(const FString& Parameters)
{
    const FVector SplineVelocity(-7.73, 127.77, 0);
    for (EWaterBodyType Type : {EWaterBodyType::Ocean, EWaterBodyType::Lake, EWaterBodyType::River})
    {
        TestTrue(TEXT("Disabled river forces do not drive tail current"),
            BoatWater::ResolvePhysicalCurrent(Type, false, SplineVelocity).IsZero());
    }
    for (EWaterBodyType Type : {EWaterBodyType::Ocean, EWaterBodyType::Lake})
    {
        TestTrue(TEXT("Ocean and lake spline metadata are not physical river flow"),
            BoatWater::ResolvePhysicalCurrent(Type, true, SplineVelocity).IsZero());
    }
    TestTrue(TEXT("Enabled river flow remains available to tail drag"),
        BoatWater::ResolvePhysicalCurrent(EWaterBodyType::River, true, SplineVelocity)
            .Equals(SplineVelocity));
    TestTrue(TEXT("Ignored invalid Ocean metadata cannot invalidate a height sample"),
        BoatWater::ResolvePhysicalCurrent(EWaterBodyType::Ocean, false,
            FVector(std::numeric_limits<double>::infinity(), 0, 0)).IsZero());
    return true;
}
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FBoatRippleFieldTest, "BoatlRacing.Physics.RippleField",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FBoatRippleFieldTest::RunTest(const FString& Parameters)
{
    // กริดจริงกว้าง 4096 ซม. บนพื้นผิว 1024 ช่อง จุดกึ่งกลางเซลล์แรกจึงเลื่อนเข้ามาครึ่งช่อง
    const FVector2D Origin = BoatWater::RippleGridOrigin(FVector2D(2048, 0), 4096.0, 1024);
    TestTrue(TEXT("Grid origin sits half a cell inside the simulated square"),
        Origin.Equals(FVector2D(2048 - 2048 + 2, -2048 + 2), 0.0001));

    BoatWater::FRippleSnapshot Snapshot;
    Snapshot.Width = 3;
    Snapshot.Height = 3;
    Snapshot.CellSizeCm = 10.0;
    Snapshot.OriginWorld = FVector2D::ZeroVector;
    Snapshot.Heights = {1, 2, 3, 4, 5, 6, 7, 8, 9};

    TestEqual(TEXT("A cell centre reads its own height"),
        BoatWater::SampleRippleHeight(Snapshot, FVector2D(0, 0)), 1.0);
    TestEqual(TEXT("The far corner reads the last cell"),
        BoatWater::SampleRippleHeight(Snapshot, FVector2D(20, 20)), 9.0);
    TestEqual(TEXT("A point between four cells reads their average"),
        BoatWater::SampleRippleHeight(Snapshot, FVector2D(5, 5)), 3.0);
    TestEqual(TEXT("Rows advance along Y, not X"),
        BoatWater::SampleRippleHeight(Snapshot, FVector2D(0, 10)), 4.0);
    // นอกหน้าต่างที่อ่านกลับมาต้องไม่เดาค่า ไม่งั้นเรือจะได้แรงจากพื้นที่ที่ไม่ได้จำลอง
    for (const FVector2D Outside : {FVector2D(-0.01, 0), FVector2D(0, -0.01),
        FVector2D(20.01, 0), FVector2D(0, 20.01), FVector2D(1e9, 1e9)})
    {
        TestEqual(TEXT("Outside the readback window there is no ripple"),
            BoatWater::SampleRippleHeight(Snapshot, Outside), 0.0);
    }
    TestEqual(TEXT("A non-finite world location has no ripple"),
        BoatWater::SampleRippleHeight(Snapshot,
            FVector2D(std::numeric_limits<double>::quiet_NaN(), 0)), 0.0);
    // ค่าเสียจาก GPU ต้องถูกปัดเป็นศูนย์ที่จุดอ่าน ไม่ใช่ไหลต่อไปเป็นแรง
    BoatWater::FRippleSnapshot Corrupt = Snapshot;
    Corrupt.Heights[0] = std::numeric_limits<float>::quiet_NaN();
    TestEqual(TEXT("A corrupt cell contributes nothing instead of poisoning the sample"),
        BoatWater::SampleRippleHeight(Corrupt, FVector2D(5, 5)), 2.75);
    BoatWater::FRippleSnapshot Truncated = Snapshot;
    Truncated.Heights.SetNum(4);
    TestEqual(TEXT("A short readback buffer is rejected whole"),
        BoatWater::SampleRippleHeight(Truncated, FVector2D(0, 0)), 0.0);

    // ทุ่นจมครึ่งลูก คลื่นยกขึ้นต้องได้แรงเพิ่ม คลื่นลดลงต้องได้แรงลบขนาดใกล้กัน
    const double Radius = 70.0;
    const double CentreZ = 400.0;
    const double WaterLevel = 400.0;
    const double Coefficient = 0.1;
    const double MaxForce = 1.0e9;
    const double Lift = BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, WaterLevel, 8.0, Coefficient, MaxForce);
    const double Drop = BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, WaterLevel, -8.0, Coefficient, MaxForce);
    TestTrue(TEXT("A crest adds buoyancy"), Lift > 0.0);
    TestTrue(TEXT("A trough removes buoyancy"), Drop < 0.0);
    TestTrue(TEXT("A still surface changes nothing"),
        BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, WaterLevel, 0.0, Coefficient, MaxForce) == 0.0);
    // ทุ่นที่จมมิดอยู่แล้วมีปริมาตรเต็ม คลื่นที่สูงขึ้นอีกจึงเพิ่มแรงไม่ได้
    TestEqual(TEXT("A fully submerged pontoon cannot gain more displacement"),
        BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, CentreZ + Radius + 50.0, 8.0,
            Coefficient, MaxForce), 0.0);
    TestEqual(TEXT("A pontoon clear of the water gains nothing from a crest below it"),
        BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, CentreZ - Radius - 50.0, 8.0,
            Coefficient, MaxForce), 0.0);
    // เพดานของ engine ต้องคุมส่วนเพิ่มด้วย ค่าคลื่นผิดปกติจึงดีดเรือไม่ได้
    for (double Ripple : {-500.0, 500.0})
    {
        TestTrue(TEXT("The correction never exceeds the engine force ceiling"),
            FMath::Abs(BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, WaterLevel, Ripple,
                Coefficient, 1000.0)) <= 1000.0);
    }
    for (double Bad : {0.0, -1.0, std::numeric_limits<double>::infinity()})
    {
        TestEqual(TEXT("An invalid radius produces no correction"),
            BoatWater::RippleBuoyancyForceZ(Bad, CentreZ, WaterLevel, 8.0, Coefficient, MaxForce), 0.0);
        TestEqual(TEXT("An invalid coefficient produces no correction"),
            BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, WaterLevel, 8.0, Bad, MaxForce), 0.0);
    }
    TestEqual(TEXT("A non-finite ripple height produces no correction"),
        BoatWater::RippleBuoyancyForceZ(Radius, CentreZ, WaterLevel,
            std::numeric_limits<double>::quiet_NaN(), Coefficient, MaxForce), 0.0);

    // ramp ต้องตรงกับของ engine ไม่งั้นแรงส่วนเพิ่มจะคนละสเกลกับแรงหลักตอนเรือเร่ง
    TestEqual(TEXT("Below the ramp window the plain coefficient is used"),
        BoatWater::RampedBuoyancyCoefficient(0.1, 20.0, 60.0, 3.0, 0.0), 0.1);
    TestEqual(TEXT("Above the ramp window the full multiplier is used"),
        BoatWater::RampedBuoyancyCoefficient(0.1, 20.0, 60.0, 3.0, 200.0), 0.3);
    TestTrue(TEXT("Mid ramp interpolates"),
        FMath::IsNearlyEqual(BoatWater::RampedBuoyancyCoefficient(0.1, 20.0, 60.0, 3.0, 40.0), 0.2));
    TestEqual(TEXT("A zero-width ramp window does not divide by zero"),
        BoatWater::RampedBuoyancyCoefficient(0.1, 60.0, 60.0, 3.0, 100.0), 0.1);
    TestEqual(TEXT("A non-finite speed yields no coefficient"),
        BoatWater::RampedBuoyancyCoefficient(0.1, 20.0, 60.0, 3.0,
            std::numeric_limits<double>::quiet_NaN()), 0.0);
    return true;
}

#endif

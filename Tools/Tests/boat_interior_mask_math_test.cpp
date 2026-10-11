#include "BoatInteriorMaskMath.h"

#include <cmath>
#include <iostream>
#include <limits>

using namespace BoatInteriorMask;

namespace
{
int Checks = 0;
int Failures = 0;

void Check(bool Condition, const char* Name)
{
    ++Checks;
    if (!Condition)
    {
        ++Failures;
        std::cout << "FAIL: " << Name << '\n';
    }
}

Profile Fixture()
{
    Profile Result;
    for (int I = 0; I < StationCount; ++I)
    {
        // รูปทดสอบมีค่าคำนวณด้วยมือ ไม่ใช่คัดความกว้างจาก helper ที่กำลังทดสอบ
        Result[I] = {I * 100.0, 5.0, 10.0, 50.0, I * 2.0, I * 4.0};
    }
    return Result;
}

void CavityBoundaries()
{
    const Profile P = Fixture();
    Check(IsValid(P), "usable tapered cavity accepted");
    // X=250: floor width 5, rim width 10; ที่ Z=30 ได้ half width 7.5
    Check(ContainsLocal(P, {250, 12.5, 30}), "inside interpolated side boundary");
    Check(!ContainsLocal(P, {250, 12.51, 30}), "outside side preserves water");
    Check(ContainsLocal(P, {250, -2.5, 30}), "opposite side boundary");
    Check(!ContainsLocal(P, {250, -2.51, 30}), "opposite outside preserves water");
    Check(ContainsLocal(P, {250, 5, 10}), "floor boundary inside");
    Check(!ContainsLocal(P, {250, 5, 9.99}), "below floor keeps water");
    Check(!ContainsLocal(P, {250, 5, 50}), "rim crest keeps water");
    Check(!ContainsLocal(P, {250, 5, 51}), "above rim keeps water");
    Check(!ContainsLocal(P, {-0.01, 5, 30}), "outside bow keeps water");
    Check(!ContainsLocal(P, {700.01, 5, 30}), "outside transom keeps water");
    Check(ContainsLocal(P, {700, 5, 30}), "last station inclusive");
    for (int I = 0; I < StationCount; ++I)
    {
        Check(ContainsLocal(P, {I * 100.0, 5, 30}), "no hole at station seam");
    }
}

void FailVisible()
{
    const double NaN = std::numeric_limits<double>::quiet_NaN();
    const double Inf = std::numeric_limits<double>::infinity();
    auto P = Fixture();
    P[3].X = P[2].X;
    Check(!IsValid(P), "duplicate station rejected");
    Check(!ContainsLocal(P, {250, 5, 30}), "invalid profile never clips");
    P = Fixture(); P[3].RimZ = P[3].FloorZ;
    Check(!IsValid(P), "zero cavity height rejected");
    P = Fixture(); P[3].FloorHalfWidth = -1;
    Check(!IsValid(P), "negative width rejected");
    P = Fixture(); P[3].CenterY = NaN;
    Check(!IsValid(P), "nonfinite station rejected");
    P = Fixture(); P[7].X = 1e300;
    Check(!IsValid(P), "shader-unsafe enormous station rejected");
    P = {};
    for (int I = 0; I < StationCount; ++I) P[I] = {double(I), 0, 0, 10, 0, 0};
    Check(!IsValid(P), "empty zero-width cavity rejected");
    P = Fixture();
    Check(!ContainsLocal(P, {NaN, 5, 30}), "NaN sample does not clip");
    Check(!ContainsLocal(P, {250, Inf, 30}), "infinite sample does not clip");
    Check(!ContainsLocal(P, {250, 5, -Inf}), "infinite depth does not clip");
}

void MovingFrame()
{
    const Profile P = Fixture();
    Frame F;
    Check(IsValid(F), "identity frame accepted");
    Check(ContainsWorld(P, F, {250, 5, 30}), "world identity cavity");
    F.Origin = {1000, -2000, 300};
    // inverse ของ yaw +90 และ scale (2,3,4)
    F.InverseRows = {{{0, .5, 0}, {-1.0 / 3.0, 0, 0}, {0, 0, .25}}};
    Check(ContainsWorld(P, F, {985, -1500, 420}), "moving rotated scaled cavity");
    Check(!ContainsWorld(P, F, {985, -1500, 500}), "scaled crest still visible");
    F.InverseRows = {{{0, 0, -.5}, {0, 1.0 / 3.0, 0}, {.25, 0, 0}}};
    Check(ContainsWorld(P, F, {1120, -1985, -200}), "pitch rotates cavity with hull");
    F.InverseRows = {{{.5, 0, 0}, {0, 0, 1.0 / 3.0}, {0, -.25, 0}}};
    Check(ContainsWorld(P, F, {1500, -2120, 315}), "roll rotates cavity with hull");
    F.InverseRows = {{{0, 0, -.5}, {-1.0 / 3.0, 0, 0}, {0, .25, 0}}};
    Check(ContainsWorld(P, F, {985, -1880, -200}), "combined yaw pitch and nonuniform scale");
    F = {}; F.InverseRows[0] = {0, 0, 0};
    Check(!IsValid(F), "singular frame rejected");
    Check(!ContainsWorld(P, F, {250, 5, 30}), "singular frame does not clip");
    F = {}; F.InverseRows[0] = {-1, 0, 0};
    Check(!IsValid(F), "reflected frame rejected");
    F = {}; F.Origin.X = std::numeric_limits<double>::infinity();
    Check(!IsValid(F), "invalid origin rejected");
    F = {}; F.InverseRows[0].X = 1e300;
    Check(!ContainsWorld(P, F, {250, 5, 30}), "unsafe enormous matrix does not clip");
    F = {}; F.Origin.X = std::numeric_limits<double>::max();
    Check(!ContainsWorld(P, F, {-std::numeric_limits<double>::max(), 5, 30}), "finite subtraction overflow does not clip");
}

void MeasuredCurvedWall()
{
    Profile P = Fixture();
    const std::array<double, 6> Heights{{17, 30.8914274, 39.1000062, 44.4587886, 47.7911353, 49.4}};
    const std::array<double, 6> Widths{{21.63, 30.90, 39.14, 45.32, 49.44, 51.50}};
    for (Station& S : P)
    {
        S.CenterY = 0;
        S.FloorZ = 17;
        S.RimZ = 49.4;
        S.FloorHalfWidth = 19.63;
        S.RimHalfWidth = 49.5;
        S.HeightKnotCount = 6;
        for (int I = 0; I < 6; ++I)
        {
            // ข้อมูล literal จากหน้าตัดจริง X=30; inset 2 cm ไม่คำนวณ expected ผ่าน helper
            S.HeightKnots[I] = {(Heights[I] - 17) / 32.4, Widths[I] - 2};
        }
    }
    Check(IsValid(P), "measured curved section accepted");
    Check(ContainsLocal(P, {250, 28.89, 30.8914274}), "measured curved wall keeps dry interior");
    Check(!ContainsLocal(P, {250, 28.91, 30.8914274}), "curved wall does not use overcut straight chord");
    Check(!ContainsLocal(P, {250, 30.91, 30.8914274}), "outside actual liner remains water");
    Check(ContainsLocal(P, {250, -28.89, 30.8914274}), "curved profile opposite side");
    for (int I = 0; I < 5; ++I)
    {
        const double Z = (Heights[I] + Heights[I + 1]) / 2;
        const double Width = (Widths[I] + Widths[I + 1]) / 2 - 2;
        Check(ContainsLocal(P, {250, Width - .01, Z}), "curved segment midpoint interior");
        Check(!ContainsLocal(P, {250, Width + .01, Z}), "curved segment midpoint exterior");
    }
    auto Bad = P;
    Bad[3].HeightKnots[2].HeightFraction = Bad[3].HeightKnots[1].HeightFraction;
    Check(!IsValid(Bad), "duplicate height knots rejected");
    Bad = P; Bad[3].HeightKnotCount = 9;
    Check(!IsValid(Bad), "excess height knots rejected before indexing");
    Bad = P; Bad[3].HeightKnots[1].HalfWidth = -1;
    Check(!IsValid(Bad), "negative curve width rejected");
    Bad = P; Bad[3].HeightKnots[0].HeightFraction = .1;
    Check(!IsValid(Bad), "curve must start at floor");
    Bad = P; Bad[3].HeightKnots[5].HeightFraction = .9;
    Check(!IsValid(Bad), "curve must end at rim");
    Bad = P; Bad[3].HeightKnots[5].HalfWidth = 40;
    Check(!IsValid(Bad), "curve endpoints agree with station widths");
    Bad = P; Bad[3].HeightKnots[1].HeightFraction = std::numeric_limits<double>::quiet_NaN();
    Check(!IsValid(Bad), "nonfinite curve height rejected");
    Bad = P; Bad[3].HeightKnotCount = -1;
    Check(!IsValid(Bad), "negative knot count rejected");
    Bad = P; Bad[3].HeightKnotCount = 1;
    Check(!IsValid(Bad), "single knot cannot describe floor and rim");
}

void SlotOwnership()
{
    Slots S;
    Check(S.Acquire(0).Index == -1, "null owner rejected");
    std::array<Handle, SlotCount> Leases;
    for (int I = 0; I < SlotCount; ++I)
    {
        Leases[I] = S.Acquire(I + 1);
        Check(Leases[I].Index == I, "free owner receives distinct slot");
        Check(!S.IsActive(I), "new slot inactive until complete payload");
        Check(S.SetActive(Leases[I], true), "valid owner activates slot");
        Check(S.IsActive(I), "active payload visible");
    }
    Check(S.Count() == SlotCount, "registry full after eight owners");
    Check(S.Acquire(99).Index == -1, "ninth cannot overwrite owner");
    Check(S.Acquire(1).Generation == Leases[0].Generation, "duplicate registration is idempotent");
    Handle Wrong = Leases[0]; Wrong.Owner = 99;
    Check(!S.Release(Wrong), "wrong owner cannot release another boat");
    Check(!S.SetActive(Wrong, false), "wrong owner cannot hide another boat");
    Check(S.Release(Leases[0]), "owner releases slot");
    Check(!S.IsActive(0), "release clears active before reuse");
    const Handle Next = S.Acquire(99);
    Check(Next.Index == 0, "released slot reused");
    Check(Next.Generation != Leases[0].Generation, "reuse invalidates stale generation");
    Check(!S.Release(Leases[0]), "stale handle cannot release reused slot");
    Check(!S.SetActive(Leases[0], true), "stale handle cannot activate reused slot");
    Check(S.SetActive(Next, true), "replacement activates");
    Check(S.SetActive(Next, false) && !S.IsActive(0), "explicit disable");
    Check(S.SetActive(Next, true) && S.IsActive(0), "explicit re-enable");
    S.Reset();
    Check(S.Count() == 0 && !S.IsActive(0), "world reset clears ownership and mask");
    const Handle AfterReset = S.Acquire(99);
    Check(AfterReset.Generation != Next.Generation, "reset does not resurrect old lease");
    Check(!S.Release(Next), "old world lease cannot release new one");

    Slots OtherWorld;
    const Handle OtherLease = OtherWorld.Acquire(99);
    Check(!OtherWorld.SetActive(AfterReset, true), "cross-registry lease cannot activate another world");
    Check(!S.Release(OtherLease), "cross-registry lease cannot release another world");
    Slots FreshWorld;
    const Handle FreshLease = FreshWorld.Acquire(99);
    Check(!FreshWorld.Release(OtherLease), "fresh registries do not share identity");
    Check(FreshWorld.SetActive(FreshLease, true), "fresh registry owner can still activate");
}
}

int main()
{
    CavityBoundaries();
    FailVisible();
    MovingFrame();
    MeasuredCurvedWall();
    SlotOwnership();
    std::cout << "MASK_CHECKS=" << Checks << " FAILURES=" << Failures << '\n';
    return Failures ? 1 : 0;
}

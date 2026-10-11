#pragma once

#include <array>
#include <atomic>
#include <cmath>
#include <cstdint>
#include <limits>

namespace BoatInteriorMask
{
constexpr int StationCount = 8;
constexpr int SlotCount = 8;
constexpr int MaxHeightKnots = 8;

struct Vector
{
    double X = 0, Y = 0, Z = 0;
};

struct WidthKnot
{
    double HeightFraction = 0;
    double HalfWidth = 0;
};

struct Station
{
    double X = 0, CenterY = 0, FloorZ = 0, RimZ = 0;
    double FloorHalfWidth = 0, RimHalfWidth = 0;
    int HeightKnotCount = 0;
    std::array<WidthKnot, MaxHeightKnots> HeightKnots{};
};

using Profile = std::array<Station, StationCount>;

struct Frame
{
    Vector Origin;
    std::array<Vector, 3> InverseRows{{{1, 0, 0}, {0, 1, 0}, {0, 0, 1}}};
};

inline bool IsFinite(Vector V)
{
    return std::isfinite(V.X) && std::isfinite(V.Y) && std::isfinite(V.Z);
}

inline bool IsValid(const Profile& P)
{
    bool HasVolume = false;
    for (int I = 0; I < StationCount; ++I)
    {
        const Station& S = P[I];
        for (double Value : {S.X, S.CenterY, S.FloorZ, S.RimZ,
                            S.FloorHalfWidth, S.RimHalfWidth})
        {
            if (!std::isfinite(Value) || std::abs(Value) > 1000000.0) return false;
        }
        if (S.RimZ - S.FloorZ < 0.001 || S.FloorHalfWidth < 0 || S.RimHalfWidth < 0
            || (I > 0 && S.X - P[I - 1].X < 0.001)) return false;
        if (S.HeightKnotCount < 0 || S.HeightKnotCount == 1 || S.HeightKnotCount > MaxHeightKnots) return false;
        if (S.HeightKnotCount > 0)
        {
            if (S.HeightKnots[0].HeightFraction != 0
                || S.HeightKnots[S.HeightKnotCount - 1].HeightFraction != 1
                || std::abs(S.HeightKnots[0].HalfWidth - S.FloorHalfWidth) > 1e-6
                || std::abs(S.HeightKnots[S.HeightKnotCount - 1].HalfWidth - S.RimHalfWidth) > 1e-6) return false;
            for (int K = 0; K < S.HeightKnotCount; ++K)
            {
                const WidthKnot& Knot = S.HeightKnots[K];
                if (!std::isfinite(Knot.HeightFraction) || !std::isfinite(Knot.HalfWidth)
                    || Knot.HeightFraction < 0 || Knot.HeightFraction > 1
                    || Knot.HalfWidth < 0 || Knot.HalfWidth > 1000000
                    || (K > 0 && Knot.HeightFraction - S.HeightKnots[K - 1].HeightFraction < 1e-6)) return false;
                HasVolume |= Knot.HalfWidth > 0;
            }
        }
        HasVolume |= S.FloorHalfWidth > 0 || S.RimHalfWidth > 0;
    }
    return HasVolume;
}

inline bool IsValid(const Frame& F)
{
    if (!IsFinite(F.Origin)) return false;
    for (const Vector& Row : F.InverseRows)
    {
        if (!IsFinite(Row) || std::abs(Row.X) > 1000000.0
            || std::abs(Row.Y) > 1000000.0 || std::abs(Row.Z) > 1000000.0) return false;
    }
    const auto& A = F.InverseRows[0];
    const auto& B = F.InverseRows[1];
    const auto& C = F.InverseRows[2];
    const double Determinant = A.X * (B.Y * C.Z - B.Z * C.Y)
        - A.Y * (B.X * C.Z - B.Z * C.X) + A.Z * (B.X * C.Y - B.Y * C.X);
    // matrix ตรวจ singular/reflection ได้; adapter Unreal ต้องตรวจ scale แต่ละแกน > 0 ด้วย
    return std::isfinite(Determinant) && Determinant > 1e-12;
}

inline bool ContainsLocal(const Profile& P, Vector V)
{
    if (!IsValid(P) || !IsFinite(V) || V.X < P.front().X || V.X > P.back().X) return false;
    for (int I = 0; I < StationCount - 1; ++I)
    {
        const Station& A = P[I];
        const Station& B = P[I + 1];
        if (V.X > B.X) continue;
        const double T = (V.X - A.X) / (B.X - A.X);
        const auto Lerp = [T](double From, double To) { return From + T * (To - From); };
        const double Floor = Lerp(A.FloorZ, B.FloorZ);
        const double Rim = Lerp(A.RimZ, B.RimZ);
        // ขอบบนเปิดไว้เสมอ: คลื่นที่ล้นขอบเรือไม่ถูกซ่อน และน้ำใต้พื้นก็ไม่ถูกตัด
        if (V.Z < Floor || V.Z >= Rim) return false;
        const double Height = (V.Z - Floor) / (Rim - Floor);
        const auto WidthAt = [Height](const Station& S)
        {
            if (S.HeightKnotCount == 0)
            {
                return S.FloorHalfWidth + Height * (S.RimHalfWidth - S.FloorHalfWidth);
            }
            // ใช้เส้นหักตามผนังจริงแทน chord เดียว ซึ่งตัดล้ำผนังโค้งกลางลำได้หลายเซนติเมตร
            // Profile ถูก validate ก่อน loop นี้ จึงไม่มีคู่ knot ซ้ำหรือ denominator เป็นศูนย์
            for (int K = 0; K < S.HeightKnotCount - 1; ++K)
            {
                const WidthKnot& From = S.HeightKnots[K];
                const WidthKnot& To = S.HeightKnots[K + 1];
                if (Height > To.HeightFraction) continue;
                const double U = (Height - From.HeightFraction) / (To.HeightFraction - From.HeightFraction);
                return From.HalfWidth + U * (To.HalfWidth - From.HalfWidth);
            }
            return S.RimHalfWidth;
        };
        const double Width = Lerp(WidthAt(A), WidthAt(B));
        return std::abs(V.Y - Lerp(A.CenterY, B.CenterY)) <= Width;
    }
    return false;
}

inline bool ContainsWorld(const Profile& P, const Frame& F, Vector V)
{
    if (!IsValid(F) || !IsFinite(V)) return false;
    const Vector Delta{V.X - F.Origin.X, V.Y - F.Origin.Y, V.Z - F.Origin.Z};
    if (!IsFinite(Delta)) return false;
    const auto Dot = [Delta](Vector Row)
    {
        return Row.X * Delta.X + Row.Y * Delta.Y + Row.Z * Delta.Z;
    };
    return ContainsLocal(P, {Dot(F.InverseRows[0]), Dot(F.InverseRows[1]), Dot(F.InverseRows[2])});
}

struct Handle
{
    int Index = -1;
    std::uint64_t Generation = 0;
    std::uint64_t Owner = 0;
    std::uint64_t Registry = 0;
};

inline std::uint64_t AllocateRegistryIdentity()
{
    static std::atomic<std::uint64_t> Next{1};
    std::uint64_t Candidate = Next.load(std::memory_order_relaxed);
    while (Candidate != std::numeric_limits<std::uint64_t>::max())
    {
        if (Next.compare_exchange_weak(Candidate, Candidate + 1, std::memory_order_relaxed)) return Candidate;
    }
    return 0;
}

class Slots
{
public:
    Slots() : Identity(AllocateRegistryIdentity()) {}
    Slots(const Slots&) = delete;
    Slots& operator=(const Slots&) = delete;
    Slots(Slots&&) = delete;
    Slots& operator=(Slots&&) = delete;

    // เรียกบน game thread เท่านั้น; owner เป็น ID ที่ adapter ผูกกับ weak UObject ไม่ใช่ global actor index
    Handle Acquire(std::uint64_t Owner)
    {
        if (!Owner || !Identity) return {};
        for (int I = 0; I < SlotCount; ++I)
        {
            if (Entries[I].Owner == Owner) return {I, Entries[I].Generation, Owner, Identity};
        }
        for (int I = 0; I < SlotCount; ++I)
        {
            if (!Entries[I].Owner)
            {
                if (Generation == std::numeric_limits<std::uint64_t>::max()) return {};
                Entries[I] = {Owner, ++Generation, false};
                return {I, Generation, Owner, Identity};
            }
        }
        return {};
    }

    bool Release(Handle H)
    {
        if (!Matches(H)) return false;
        Entries[H.Index] = {};
        return true;
    }

    bool SetActive(Handle H, bool Active)
    {
        if (!Matches(H)) return false;
        Entries[H.Index].Active = Active;
        return true;
    }

    bool IsActive(int Index) const
    {
        return Index >= 0 && Index < SlotCount && Entries[Index].Active;
    }

    int Count() const
    {
        int Result = 0;
        for (const Entry& E : Entries) Result += E.Owner != 0;
        return Result;
    }

    void Reset()
    {
        // ไม่ย้อน generation ตอนเปลี่ยน World/คืน slot เพื่อไม่ให้ handle เก่ากลับมาตรงกับเจ้าของใหม่
        Entries = {};
    }

private:
    struct Entry
    {
        std::uint64_t Owner = 0;
        std::uint64_t Generation = 0;
        bool Active = false;
    };
    std::array<Entry, SlotCount> Entries{};
    std::uint64_t Generation = 0;
    // แต่ละ registry/World ต้องมี identity ใหม่ แม้ใช้ owner/index เดิมหลังทำลาย World
    const std::uint64_t Identity;

    bool Matches(Handle H) const
    {
        return H.Registry == Identity && Identity != 0
            && H.Index >= 0 && H.Index < SlotCount && H.Owner != 0
            && Entries[H.Index].Owner == H.Owner && Entries[H.Index].Generation == H.Generation;
    }
};
}

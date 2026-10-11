#pragma once

#include "BoatInteriorMaskMath.h"
#include <algorithm>
#include <optional>
#include <map>
#include <tuple>
#include <vector>

namespace BoatMaskMesh
{
using BoatInteriorMask::Vector;
struct Triangle { Vector A, B, C; };
using Mesh = std::vector<Triangle>;

// เครื่องมือ survey สำหรับ liner ชิ้นเดียวที่มีโพรงอยู่รอบ centerline เท่านั้น
// ผล ray แบบสุ่มจุดไม่ใช่หลักฐานว่าปริมาตร mask ที่ interpolate อยู่ภายใน mesh ทุกจุด
inline bool IsClosedConnected(const Mesh& M)
{
    using Key = std::tuple<double, double, double>;
    std::map<Key, int> Vertices;
    std::map<std::pair<int,int>, std::pair<int,int>> Edges;
    std::vector<std::vector<int>> Neighbors;
    const auto Index = [&Vertices, &Neighbors](Vector V)
    {
        const Key K{V.X, V.Y, V.Z};
        const auto Existing = Vertices.find(K);
        if (Existing != Vertices.end()) return Existing->second;
        const int I = static_cast<int>(Vertices.size());
        Vertices.emplace(K, I); Neighbors.emplace_back(); return I;
    };
    for (const Triangle& T : M)
    {
        if (!BoatInteriorMask::IsFinite(T.A) || !BoatInteriorMask::IsFinite(T.B)
            || !BoatInteriorMask::IsFinite(T.C)) return false;
        const int V[3]{Index(T.A), Index(T.B), Index(T.C)};
        if (V[0] == V[1] || V[1] == V[2] || V[0] == V[2]) return false;
        for (int I = 0; I < 3; ++I)
        {
            const int A = V[I], B = V[(I + 1) % 3];
            auto& E = Edges[{std::min(A,B), std::max(A,B)}];
            ++E.first; E.second += A < B ? 1 : -1;
            Neighbors[A].push_back(B); Neighbors[B].push_back(A);
        }
    }
    if (Vertices.empty()) return false;
    for (const auto& E : Edges) if (E.second.first != 2 || E.second.second != 0) return false;
    std::vector<bool> Seen(Vertices.size(), false);
    std::vector<int> Queue{0}; Seen[0] = true;
    for (std::size_t I = 0; I < Queue.size(); ++I)
    {
        for (int V : Neighbors[Queue[I]]) if (!Seen[V]) { Seen[V] = true; Queue.push_back(V); }
    }
    return Queue.size() == Vertices.size();
}

inline bool CoplanarOverlap(const Triangle& T, double X, double Z)
{
    if (!std::isfinite(X) || !std::isfinite(Z)) return false;
    const double D = (T.B.Z - T.C.Z) * (T.A.X - T.C.X)
        + (T.C.X - T.B.X) * (T.A.Z - T.C.Z);
    if (!std::isfinite(D) || std::abs(D) >= 1e-10) return false;
    const Vector V[3]{T.A, T.B, T.C};
    for (int I = 0; I < 3; ++I)
    {
        const Vector A = V[I], B = V[(I + 1) % 3];
        const double DX = B.X - A.X, DZ = B.Z - A.Z;
        const double QX = X - A.X, QZ = Z - A.Z;
        const double LengthSq = DX * DX + DZ * DZ;
        if (LengthSq < 1e-12) { if (QX * QX + QZ * QZ < 1e-12) return true; continue; }
        const double Along = QX * DX + QZ * DZ;
        const double Tolerance = 1e-8 * std::max(1.0, std::sqrt(LengthSq));
        if (std::abs(QX * DZ - QZ * DX) <= Tolerance && Along >= -Tolerance
            && Along <= LengthSq + Tolerance) return true;
    }
    return false;
}

inline std::optional<double> ProjectedIntersection(
    const Triangle& T, double X, double Second, int OutputAxis)
{
    if (!std::isfinite(X) || !std::isfinite(Second)
        || !BoatInteriorMask::IsFinite(T.A) || !BoatInteriorMask::IsFinite(T.B)
        || !BoatInteriorMask::IsFinite(T.C) || (OutputAxis != 1 && OutputAxis != 2)) return {};
    const auto V = [OutputAxis](Vector P) { return OutputAxis == 2 ? P.Y : P.Z; };
    const double Denominator = (V(T.B) - V(T.C)) * (T.A.X - T.C.X)
        + (T.C.X - T.B.X) * (V(T.A) - V(T.C));
    if (!std::isfinite(Denominator) || std::abs(Denominator) < 1e-10) return {};
    const double A = ((V(T.B) - V(T.C)) * (X - T.C.X)
        + (T.C.X - T.B.X) * (Second - V(T.C))) / Denominator;
    const double B = ((V(T.C) - V(T.A)) * (X - T.C.X)
        + (T.A.X - T.C.X) * (Second - V(T.C))) / Denominator;
    const double C = 1.0 - A - B;
    if (!std::isfinite(A) || !std::isfinite(B) || !std::isfinite(C)
        || A < -1e-8 || B < -1e-8 || C < -1e-8) return {};
    const auto Out = [OutputAxis](Vector P) { return OutputAxis == 2 ? P.Z : P.Y; };
    const double Result = A * Out(T.A) + B * Out(T.B) + C * Out(T.C);
    return std::isfinite(Result) ? std::optional<double>(Result) : std::nullopt;
}

inline std::optional<double> FloorAt(const Mesh& M, double X)
{
    std::optional<double> Highest;
    for (const Triangle& T : M)
    {
        const auto Z = ProjectedIntersection(T, X, 0, 2);
        if (Z && (!Highest || *Z > *Highest)) Highest = Z;
    }
    return Highest;
}

inline std::optional<double> RimAt(const Mesh& M, double X)
{
    if (!std::isfinite(X)) return {};
    std::optional<double> Positive, Negative;
    for (const Triangle& T : M)
    {
        const Vector V[3]{T.A, T.B, T.C};
        for (int I = 0; I < 3; ++I)
        {
            const Vector A = V[I], B = V[(I + 1) % 3];
            if (!BoatInteriorMask::IsFinite(A) || !BoatInteriorMask::IsFinite(B)) continue;
            const auto Add = [&Positive, &Negative](double Y, double Z)
            {
                if (Y > 1e-8 && (!Positive || Z > *Positive)) Positive = Z;
                if (Y < -1e-8 && (!Negative || Z > *Negative)) Negative = Z;
            };
            if (std::abs(A.X - X) < 1e-8) Add(A.Y, A.Z);
            if (X < std::min(A.X, B.X) || X > std::max(A.X, B.X) || std::abs(B.X - A.X) < 1e-10) continue;
            const double U = (X - A.X) / (B.X - A.X);
            Add(A.Y + U * (B.Y - A.Y), A.Z + U * (B.Z - A.Z));
        }
    }
    return Positive && Negative ? std::optional<double>(std::min(*Positive, *Negative)) : std::nullopt;
}

inline std::optional<double> HalfWidthAt(const Mesh& M, double X, double Z)
{
    std::optional<double> Positive, Negative;
    for (const Triangle& T : M)
    {
        // ผิวที่ ray วิ่งทับมีหลายคำตอบ จึงไม่เลือกผิวด้านนอกที่ไกลกว่าแล้วอ้างว่าเป็นช่องว่าง
        if (CoplanarOverlap(T, X, Z)) return {};
        const auto Y = ProjectedIntersection(T, X, Z, 1);
        if (!Y) continue;
        if (*Y > 1e-8 && (!Positive || *Y < *Positive)) Positive = Y;
        if (*Y < -1e-8 && (!Negative || -*Y < *Negative)) Negative = -*Y;
    }
    // ใช้ผนังที่ใกล้ centerline ที่สุดทั้งสองฝั่ง ไม่ใช้ bounding box หรือผิว solidify ด้านนอก
    return Positive && Negative ? std::optional<double>(std::min(*Positive, *Negative)) : std::nullopt;
}
}

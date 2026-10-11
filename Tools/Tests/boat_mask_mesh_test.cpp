#include "BoatMaskMesh.h"
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>

using namespace BoatMaskMesh;
namespace
{
int Checks = 0, Failures = 0;
void Check(bool Pass, const char* Name)
{
    ++Checks;
    if (!Pass) { ++Failures; std::cout << "FAIL: " << Name << '\n'; }
}
bool Near(std::optional<double> Value, double Expected)
{
    return Value && std::abs(*Value - Expected) < 1e-6;
}
void Quad(Mesh& M, Vector A, Vector B, Vector C, Vector D)
{
    M.push_back({A, B, C}); M.push_back({A, C, D});
}
void GeometryTests()
{
    const Triangle T{{0,0,0}, {10,0,10}, {0,10,20}};
    Check(Near(ProjectedIntersection(T, 2, 3, 2), 8), "vertical ray interpolates sloped triangle");
    Check(Near(ProjectedIntersection(T, 2, 8, 1), 3), "horizontal ray interpolates triangle");
    Check(!ProjectedIntersection(T, 9, 9, 2), "ray outside triangle has no intersection");
    Check(Near(ProjectedIntersection(T, 0, 0, 2), 0), "triangle vertex is included");
    Check(!ProjectedIntersection({{0,0,0},{0,0,1},{0,0,2}}, 0, 0, 2), "degenerate projection ignored");
    Check(!ProjectedIntersection(T, std::numeric_limits<double>::quiet_NaN(), 0, 2), "invalid ray rejected");
    Mesh Box;
    Quad(Box, {-10,-5,0}, {10,-5,0}, {10,5,0}, {-10,5,0});
    Quad(Box, {-10,-5,0}, {10,-5,0}, {10,-5,10}, {-10,-5,10});
    Quad(Box, {-10,5,0}, {10,5,0}, {10,5,10}, {-10,5,10});
    Check(Near(FloorAt(Box, 0), 0), "center floor measured from triangles");
    Check(Near(FloorAt(Box, 2.5), 0), "floor between authored stations measured");
    Check(Near(RimAt(Box, 0), 10), "open rim measured");
    Check(Near(HalfWidthAt(Box, 0, 5), 5), "both cavity walls measured");
    Check(!HalfWidthAt(Box, 0, 11), "above rim has no closed wall interval");
    Check(!FloorAt(Box, 11), "outside longitudinal extent rejected");
    // ชั้น solidify ด้านนอกห้ามทำให้โพรงกว้างขึ้นหรือพื้นต่ำลง
    Quad(Box, {-10,-6,-1}, {10,-6,-1}, {10,6,-1}, {-10,6,-1});
    Quad(Box, {-10,-6,-1}, {10,-6,-1}, {10,-6,10}, {-10,-6,10});
    Quad(Box, {-10,6,-1}, {10,6,-1}, {10,6,10}, {-10,6,10});
    Check(Near(FloorAt(Box, 0), 0), "highest central surface excludes outer bottom skin");
    Check(Near(HalfWidthAt(Box, 0, 5), 5), "nearest walls exclude outer side skin");
    Mesh Asymmetric;
    Quad(Asymmetric, {-10,-5,0}, {10,-5,0}, {10,-5,6}, {-10,-5,6});
    Quad(Asymmetric, {-10,5,0}, {10,5,0}, {10,5,10}, {-10,5,10});
    Check(Near(RimAt(Asymmetric, 0), 6), "lower enclosing rim controls overflow height");
    Check(!HalfWidthAt(Asymmetric, 0, 8), "unpaired walls above lower rim rejected");
    Mesh OneWall;
    Quad(OneWall, {-10,5,0}, {10,5,0}, {10,5,10}, {-10,5,10});
    Check(!HalfWidthAt(OneWall, 0, 5), "open opposite side cannot provide paired walls");
    Quad(Box, {-10,3,5}, {10,3,5}, {10,4,5}, {-10,4,5});
    Check(!HalfWidthAt(Box, 0, 5), "coplanar inner shelf is ambiguous rather than skipped");
    Mesh Tetra{{{0,0,0},{10,0,0},{0,10,0}}, {{0,0,0},{0,0,10},{10,0,0}},
        {{0,0,0},{0,10,0},{0,0,10}}, {{10,0,0},{0,0,10},{0,10,0}}};
    Check(IsClosedConnected(Tetra), "closed connected oriented surface accepted for survey");
    Mesh Disconnected = Tetra;
    for (Triangle Tri : Tetra) {
        Tri.A.X += 100; Tri.B.X += 100; Tri.C.X += 100; Disconnected.push_back(Tri);
    }
    Check(!IsClosedConnected(Disconnected), "disconnected surfaces rejected for whole-liner survey");
    Tetra.pop_back();
    Check(!IsClosedConnected(Tetra), "open mesh rejected for whole-liner survey");
}
}

int main(int Argc, char** Argv)
{
    GeometryTests();
    if (Argc == 3 && Failures == 0)
    {
        std::ifstream Input(Argv[1]);
        std::size_t VCount = 0, TCount = 0;
        Input >> VCount >> TCount;
        if (!Input || VCount == 0 || VCount > 100000 || TCount == 0 || TCount > 200000) return 2;
        std::vector<Vector> Vertices(VCount);
        for (Vector& V : Vertices)
        {
            Input >> V.X >> V.Y >> V.Z;
            if (!Input || !BoatInteriorMask::IsFinite(V)) return 2;
        }
        Mesh Hull;
        for (std::size_t I = 0; I < TCount; ++I)
        {
            std::size_t A, B, C;
            Input >> A >> B >> C;
            if (!Input || A >= VCount || B >= VCount || C >= VCount) return 2;
            Hull.push_back({Vertices[A], Vertices[B], Vertices[C]});
        }
        Check(IsClosedConnected(Hull), "real liner is closed connected with consistent edge orientation");
        if (Failures) { std::cout << "MESH_CHECKS=" << Checks << " FAILURES=" << Failures << '\n'; return 1; }
        std::ofstream Report(Argv[2]);
        if (!Report) return 2;
        Report << std::setprecision(12) << "{\"sampling\":\"Centered single-liner triangle ray survey, 1 cm X grid; not full-volume containment\",\"closedConnectedSurface\":true,\"sections\":[";
        int SectionCount = 0;
        double SmallestWidth = 1e9, LargestWidth = 0;
        for (double X = -230; X <= 301; X += 1)
        {
            const auto Floor = FloorAt(Hull, X);
            const auto Rim = RimAt(Hull, X);
            if (!Floor || !Rim || *Rim - *Floor < 2) { Check(false, "real cockpit section has floor and rim"); continue; }
            if (SectionCount++) Report << ',';
            Report << "{\"xCm\":" << X << ",\"floorZcm\":" << *Floor << ",\"rimZcm\":" << *Rim << ",\"widthSamples\":[";
            for (int H = 0; H < 8; ++H)
            {
                // ไม่ cast ตรงพื้น/ขอบ เพื่อหลีกเลี่ยง coplanar seam และไม่รวมผิวด้านนอก
                const double Z = *Floor + 1.0 + H / 7.0 * (*Rim - *Floor - 2.0);
                const auto Width = HalfWidthAt(Hull, X, Z);
                Check(Width.has_value() && *Width > 0, "real cockpit has paired inner walls");
                if (H) Report << ',';
                Report << "{\"zCm\":" << Z << ",\"halfWidthCm\":";
                if (Width) {
                    Report << *Width;
                    SmallestWidth = std::min(SmallestWidth, *Width);
                    LargestWidth = std::max(LargestWidth, *Width);
                } else Report << "null";
                Report << '}';
            }
            Report << "]}";
        }
        Report << "],\"sectionCount\":" << SectionCount << ",\"minHalfWidthCm\":" << SmallestWidth
            << ",\"maxHalfWidthCm\":" << LargestWidth << ",\"failures\":" << Failures << '}';
        if (!Report) return 2;
        Check(SectionCount == 532, "full selected cockpit extent sampled");
    }
    std::cout << "MESH_CHECKS=" << Checks << " FAILURES=" << Failures << '\n';
    return Failures ? 1 : 0;
}

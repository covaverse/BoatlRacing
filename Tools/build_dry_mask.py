"""Generate a closed rendering mask from the existing measured liner survey."""
import collections
import json
import struct
from pathlib import Path

root = Path(__file__).resolve().parents[1]
survey = json.loads((root / 'Saved/Automation/WaterMaskMath/hull-survey.json').read_text())
assert survey['failures'] == 0 and survey['closedConnectedSurface']
sections = survey['sections']
vertices, triangles = [], []
# ponytail: measured 1 cm stations/eight heights; refine the source survey for sub-centimeter clearance.
for section in sections:
    samples = section['widthSamples']
    assert len(samples) == 8 and all(p['halfWidthCm'] > 0 for p in samples)
    vertices.extend((section['xCm'], p['halfWidthCm'], p['zCm']) for p in samples)
    vertices.extend((section['xCm'], -p['halfWidthCm'], p['zCm']) for p in reversed(samples))
for i in range(len(sections) - 1):
    for j in range(16):
        a, b = i * 16 + j, i * 16 + (j + 1) % 16
        triangles.extend(((a, b, b + 16), (a, b + 16, a + 16)))
for i in (0, len(sections) - 1):
    offset = i * 16
    for j in range(7):
        a, b, c, d = (offset + j, offset + j + 1, offset + 14 - j, offset + 15 - j)
        faces = ((a, b, c), (a, c, d))
        triangles.extend(tuple(reversed(f)) if i == 0 else f for f in faces)
edges = collections.Counter(tuple(sorted((f[j], f[(j + 1) % 3])))
                            for f in triangles for j in range(3))
assert set(edges.values()) == {2}, 'Mask must be closed and manifold'
assert len(vertices) - len(edges) + len(triangles) == 2
volume = sum(sum(vertices[f[0]][j] * (
    vertices[f[1]][(j + 1) % 3] * vertices[f[2]][(j + 2) % 3] -
    vertices[f[1]][(j + 2) % 3] * vertices[f[2]][(j + 1) % 3]) for j in range(3))
             for f in triangles) / 6
assert volume > 0, volume
path = root / 'SourceAssets/Physics/SM_BoatDryCavity.obj'
path.write_text('# Measured dry liner volume; centimeters, boat coordinates.\no SM_BoatDryCavity\n' +
                ''.join('v %.6f %.6f %.6f\n' % v for v in vertices) +
                ''.join('f %d %d %d\n' % tuple(i + 1 for i in f) for f in triangles))
print('BOAT_DRY_MASK_MANIFOLD_PASS', len(vertices), len(triangles), volume)
pixels = bytearray()
for row in range(8):
    for section in sections:
        samples = section['widthSamples']
        width, floor, rim = samples[row]['halfWidthCm'], samples[0]['zCm'], samples[-1]['zCm']
        assert all(0 <= v < 64 for v in (width, floor, rim))
        pixels.extend(round(v / 64 * 255) for v in (rim, floor, width))
        pixels.append(255)
header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, len(sections), 8, 32, 0x28)
(path.parent / 'T_BoatDryProfile.tga').write_bytes(header + pixels)
assert len(header) == 18 and len(pixels) == 532 * 8 * 4
print('BOAT_DRY_PROFILE_TEXTURE_PASS', 532, 8)

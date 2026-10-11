"""Bake the exterior hull waterline in boat coordinates; run with local Python/numpy."""
import json
import struct
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def hull_triangles():
    raw = (ROOT / 'SourceAssets/ThaiLongtail/thai_racing_longtail_runtime_2k.glb').read_bytes()
    magic, version, length, size, kind = struct.unpack_from('<5I', raw)
    assert magic == 0x46546C67 and version == 2 and length == len(raw) and kind == 0x4E4F534A
    doc = json.loads(raw[20:20 + size])
    offset = 28 + size
    assert struct.unpack_from('<I', raw, offset - 4)[0] == 0x004E4942
    nodes = [i for i, n in enumerate(doc['nodes']) if n.get('name') == 'Hull | main black shell']
    assert len(nodes) == 1
    node = doc['nodes'][nodes[0]]
    current, visited = nodes[0], set()
    while True:
        assert current not in visited, 'Cyclic hierarchy'
        visited.add(current)
        assert not any(k in doc['nodes'][current] for k in ('translation', 'rotation', 'scale', 'matrix')), 'Unhandled mesh transform'
        parents = [i for i, n in enumerate(doc['nodes']) if current in n.get('children', [])]
        if not parents:
            break
        assert len(parents) == 1
        current = parents[0]

    def accessor(index):
        assert 0 <= index < len(doc['accessors'])
        a = doc['accessors'][index]
        assert 0 <= a['bufferView'] < len(doc['bufferViews']) and 'sparse' not in a
        v = doc['bufferViews'][a['bufferView']]
        assert v['buffer'] == 0
        dtype = np.dtype({5126: '<f4', 5125: '<u4', 5123: '<u2', 5121: 'u1'}[a['componentType']])
        cols = {'VEC3': 3, 'SCALAR': 1}[a['type']]
        stride = v.get('byteStride', dtype.itemsize * cols)
        start = a.get('byteOffset', 0)
        assert start >= 0 and stride >= dtype.itemsize * cols
        assert start + (a['count'] - 1) * stride + cols * dtype.itemsize <= v['byteLength']
        assert v.get('byteOffset', 0) >= 0 and offset + v.get('byteOffset', 0) + v['byteLength'] <= len(raw)
        return np.ndarray((a['count'], cols), dtype, raw, offset + v.get('byteOffset', 0) + start,
                          strides=(stride, dtype.itemsize)).copy()

    triangles = []
    for p in doc['meshes'][node['mesh']]['primitives']:
        assert p.get('mode', 4) == 4
        vertices = accessor(p['attributes']['POSITION']).astype(float)
        vertices = vertices[:, [0, 2, 1]] * [100, -100, 100]
        indices = accessor(p['indices']).reshape(-1, 3)
        assert indices.max() < len(vertices) and np.isfinite(vertices).all()
        triangles.extend(vertices[indices])
    return np.array(triangles)


def bake(triangles):
    # ponytail: symmetric single hull, 1 cm grid; use separate side channels for asymmetric boats.
    widths = np.zeros((128, 640))
    valid = np.zeros_like(widths, dtype=bool)
    for tri in triangles:
        a, b, c = tri[:, [0, 2]]
        det = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(det) < 1e-8:
            continue
        lo = np.maximum(np.ceil(np.min(tri[:, [0, 2]], axis=0) + [319.5, 15.5]).astype(int), 0)
        hi = np.minimum(np.floor(np.max(tri[:, [0, 2]], axis=0) + [319.5, 15.5]).astype(int), [639, 127])
        xx, zz = np.meshgrid(np.arange(lo[0], hi[0] + 1), np.arange(lo[1], hi[1] + 1))
        dx, dz = xx - 319.5 - a[0], zz - 15.5 - a[1]
        u = (dx * (c[1] - a[1]) - dz * (c[0] - a[0])) / det
        v = ((b[0] - a[0]) * dz - (b[1] - a[1]) * dx) / det
        hit = (u >= -1e-7) & (v >= -1e-7) & (u + v <= 1 + 1e-7)
        y = abs(tri[0, 1] + u * (tri[1, 1] - tri[0, 1]) + v * (tri[2, 1] - tri[0, 1]))
        widths[zz[hit], xx[hit]] = np.maximum(widths[zz[hit], xx[hit]], y[hit])
        valid[zz[hit], xx[hit]] = True
    assert valid.any() and widths.max() < 64
    pixels = np.zeros((128, 640, 4), dtype=np.uint8)
    pixels[:, :, 2] = np.round(widths / 64 * 255).astype(np.uint8)
    pixels[:, :, 1] = valid * 255
    pixels[:, :, 3] = 255
    return pixels


if __name__ == '__main__':
    triangles = hull_triangles()
    pixels = bake(triangles)
    # Independent ray/triangle measurement catches axis, packing, and wrong-shell regressions.
    for x, z in ((-219.5, 25.5), (-199.5, 25.5), (0.5, 10.5), (200.5, 30.5)):
        hits = []
        for tri in triangles:
            matrix = np.vstack((tri[:, 0], tri[:, 2], np.ones(3)))
            if abs(np.linalg.det(matrix)) < 1e-8:
                continue
            weights = np.linalg.solve(matrix, [x, z, 1])
            if min(weights) >= -1e-7:
                hits.append(abs(weights @ tri[:, 1]))
        assert hits
        measured = pixels[int(z + 16), int(x + 320), 2] * (64 / 255)
        assert abs(measured - max(hits)) <= 64 / 510 + 1e-5
    target = ROOT / 'SourceAssets/Physics/T_BoatOuterProfile.tga'
    header = struct.pack('<BBBHHBHHHHBB', 0, 0, 2, 0, 0, 0, 0, 0, 640, 128, 32, 0x28)
    target.write_bytes(header + pixels.tobytes())
    print('OUTER_HULL_PROFILE_PASS', len(triangles), str(target))

"""Stage only the garden-facing ramp-wall repair, preserving other asset bytes."""
import argparse
from collections import Counter
import copy
import json
from pathlib import Path
import re
import types

import numpy as np
import belltower_compact_obj as C
import belltower_detail as D
import belltower_map as B
import belltower_stage_wall_edges as Patch
import belltower_wall_cleanup as Cleanup
from belltower_safe_imports import span
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
FACE = [(-1850, -1200, -48), (-1850, -1000, -48),
        (-1850, -1000, 28), (-1850, -1200, 28)]


def plain(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def polygon_model(polygons):
    model = K.Model()
    for polygon in polygons:
        model.polygon('rubble', polygon)
    return model


def geometry_checks(legacy):
    before = polygon_model(legacy.visible_pieces(FACE))
    after = polygon_model(Cleanup.visible_pieces(FACE))
    assert len(after.polygons['rubble']) == 1
    assert np.array_equal(after.polygons['rubble'][0][0], FACE)
    old_area = sum(legacy.polygon_area(p) for p, _ in before.polygons['rubble'])
    new_area = sum(Cleanup.polygon_area(p) for p, _ in after.polygons['rubble'])
    assert new_area == 200 * 76 and new_area > old_area + 4000
    # The opposite face must still follow the rising road.
    road_face = [(-1862, -1000, -48), (-1862, -1200, -48),
                 (-1862, -1200, 28), (-1862, -1000, 28)]
    a, b = legacy.visible_pieces(road_face), Cleanup.visible_pieces(road_face)
    assert len(a) == len(b) and all(np.array_equal(x, y) for x, y in zip(a, b))
    buried = [(e, n, -60 if z == -48 else -50) for e, n, z in FACE]
    assert not Cleanup.visible_pieces(buried)
    # Check the entire current town-wall builder, including authored props:
    # only this garden face may differ, and no collision is changed.
    original = K.Model()
    B.town_walls(original, trim_buried=False)
    old_town, new_town = copy.deepcopy(original), copy.deepcopy(original)
    legacy.trim_model(old_town, {})
    Cleanup.trim_model(new_town, {})
    old_geo, new_geo = Patch.geometry(old_town), Patch.geometry(new_town)
    old_target, new_target = Patch.geometry(before), Patch.geometry(after)
    assert old_geo-new_geo == old_target-new_target
    assert new_geo-old_geo == new_target-old_target
    for attr in ('boxes', 'hulls', 'props'):
        assert plain(getattr(old_town, attr)) == plain(getattr(new_town, attr))
    return before, after, old_area, new_area


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--baseline', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    Patch.OUT, Patch.STAGE = out, out / 'stage'
    assert not (Patch.STAGE/'manifest.json').exists(), 'Use a fresh staging directory'
    legacy = types.ModuleType('baseline_wall_cleanup')
    exec(compile(args.baseline.read_text(), str(args.baseline), 'exec'), legacy.__dict__)
    before, after, old_area, new_area = geometry_checks(legacy)
    report = {'revision': 'garden-ramp-wall-gap-v1', 'files': {},
              'source_sha256': {}, 'protected_sha256': {},
              'original_collision_exact': True,
              'all_other_town_wall_geometry_exact': True,
              'road_side_slope_preserved': True, 'buried_garden_faces_removed': True,
              'new_scene_objects': 0, 'new_materials': 0,
              'garden_face_area_before': old_area, 'garden_face_area_after': new_area,
              'scene_sha256': Patch.sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
              'models': {}}
    for relative in ('Tools/belltower_wall_cleanup.py', 'Tools/belltower_stage_ramp_gap.py',
                     'Tools/belltower_map.py', 'Tools/map_kit.py'):
        report['source_sha256'][relative] = Patch.sha(ROOT/relative)
    for side in ('west', 'east'):
        canonical = ROOT/f'Assets/models/maps/belltower/belltower_{side}.obj'
        vmdl = canonical.with_suffix('.vmdl')
        report['protected_sha256'][vmdl.relative_to(ROOT).as_posix()] = Patch.sha(vmdl)
        for path in canonical.parent.glob(f'belltower_{side}*hull*.obj'):
            report['protected_sha256'][path.relative_to(ROOT).as_posix()] = Patch.sha(path)
        old = before if side == 'west' else before.mirrored()
        new = after if side == 'west' else after.mirrored()
        new.tile_overrides.update(D.TILES)
        piece = out/f'replacement-{side}.obj'
        K.write_obj(piece, new, f'belltower_{side}')
        lookup, polygons = Patch.polygon_options(old)
        wanted = lookup.keys()
        row, found = Patch.patch(canonical, wanted, piece)
        Patch.check_coverage(found, lookup, polygons)
        assert row and row['removed_triangles'] == 3 and row['appended_triangles'] == 2
        report['files'][canonical.relative_to(ROOT).as_posix()] = row
        text = vmdl.read_text()
        a, b = span(text, '_class = "RenderMeshList"')
        imports = re.findall(r'filename\s*=\s*"([^"]+\.obj)"', text[a:b])
        runtime_found = Counter()
        changed = []
        for resource in imports:
            if not resource.endswith('_rubble.obj'):
                continue
            path = ROOT/'Assets'/resource
            row, matched = Patch.patch(path, wanted, piece)
            runtime_found.update(matched)
            if row:
                changed.append(resource)
                assert row['removed_triangles'] == 3 and row['appended_triangles'] == 2
                report['files'][path.relative_to(ROOT).as_posix()] = row
        assert runtime_found == found and len(changed) == 1
        # Replacement UVs and normals at existing corners must match the
        # original face; extrapolation to the restored lower corner is planar.
        tables = C.tables(canonical)
        replacement = C.tables(piece)
        old_attributes = {}
        paint = None
        for line in canonical.open('rb'):
            if line.startswith(b'usemtl '):
                paint = line.split()[1]
            elif line.startswith(b'f ') and paint == b'rubble':
                tokens = C.face_tokens(line, {k: len(v)-1 for k, v in tables.items()})
                key = (paint, frozenset(tables[b'v'][t[0]][2:].strip() for t in tokens))
                if key in wanted:
                    for v, uv, normal in tokens:
                        old_attributes[tables[b'v'][v][2:].strip()] = (tables[b'vt'][uv].strip(), tables[b'vn'][normal].strip())
        for index in range(1, len(replacement[b'v'])):
            point = replacement[b'v'][index][2:].strip()
            if point in old_attributes:
                assert old_attributes[point] == (replacement[b'vt'][index].strip(), replacement[b'vn'][1].strip())
        report['models'][side] = {'runtime_piece': changed[0],
                                  'removed_triangles': 3, 'replacement_triangles': 2,
                                  'unchanged_existing_corner_uvs_and_normals': True,
                                  'physics_and_vmdl_byte_identical': True}
    report['protected_sha256']['Assets/materials/belltower/rubble.vmat'] = Patch.sha(ROOT/'Assets/materials/belltower/rubble.vmat')
    (Patch.STAGE/'manifest.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()

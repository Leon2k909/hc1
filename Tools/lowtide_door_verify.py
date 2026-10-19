"""Check exported shed-door coverage, grip clearance and reproducibility.

This validates the offline mesh candidate, not native rendering or performance.
"""
import json
from pathlib import Path

import numpy as np

import map_kit as K
import lowtide_map as L
import lowtide_door_construction as D
import lowtide_window_construction as W
import lowtide_window_software as R

OUT = K.ROOT/'output/lowtide/quality-pass/door-construction'


def ray_hits(triangles, origins, direction, maximum=100):
    direction = np.asarray(direction, float)
    a = triangles[:, 0]
    e1, e2 = triangles[:, 1]-a, triangles[:, 2]-a
    h = np.cross(direction, e2)
    determinant = np.sum(e1*h, axis=1)
    good = abs(determinant) > 1e-10
    reciprocal = np.divide(1, determinant, out=np.zeros_like(determinant), where=good)
    answer = []
    for start in range(0, len(origins), 64):
        s = origins[start:start+64, None, :]-a
        u = np.sum(s*h, axis=2)*reciprocal
        q = np.cross(s, e1)
        v = np.sum(q*direction, axis=2)*reciprocal
        t = np.sum(q*e2, axis=2)*reciprocal
        hit = good & (u >= -1e-8) & (v >= -1e-8) & (u+v <= 1+1e-8) & (t >= 0) & (t <= maximum)
        answer.extend(np.min(np.where(hit, t, np.inf), axis=1))
    return np.asarray(answer)


def verify():
    manifest = json.loads((OUT/'manifest.json').read_text())
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['generator_sources'].items())
    mapping = D.mapping()
    rows = manifest['selected_layout']['lowtide_east']
    old, new = D.geometry(rows, L, mapping)
    reproduction = OUT/'reproduction'
    reproduction.mkdir(exist_ok=True)
    repeated = []
    for name, model in (('lowtide_east', new), ('lowtide_west', new.mirrored(L.WEST_PAINTS))):
        L.configure(model)
        path = reproduction/f'{name}-new.obj'
        K.write_obj(path, model, name)
        assert path.read_bytes() == (OUT/path.name).read_bytes(), name
        repeated.append(name)
    total_coverage = total_clearance = total_grips = total_keeper_clearance = 0
    checked = []
    for name, mirrored in (('lowtide_east', False), ('lowtide_west', True)):
        exported, paints = R.read_obj(OUT/f'{name}-new.obj')
        p = exported[..., :3].copy()
        geometric = np.cross(p[:, 1]-p[:, 0], p[:, 2]-p[:, 0])
        assert np.all(np.sum(geometric*exported[:, 0, 5:], axis=1) > 1e-8)
        if mirrored: p[..., 0] *= -1
        for row in rows:
            wall, opening, _ = W.unpack(row, L)
            depth, sign, outward = L.wall_out(wall)
            along = wall.point(1, 0, 0)-wall.point(0, 0, 0)
            basis = np.column_stack((along, outward, (0., 0., 1.)))
            origin = wall.point(opening.r0, depth-sign*8, opening.z0)
            local = (p-origin)@basis
            width, height = opening.r1-opening.r0, opening.z1-opening.z0
            inside = np.all((local >= (-.13, -2.01, -.01)) &
                            (local <= (width+.13, 2.03, height+.01)), axis=(1, 2))
            triangles = local[inside]
            assert len(triangles) > 1000, (name, row, 'Missing door geometry')
            # Both general coverage and exact board-seam samples must hit timber.
            x = list(np.linspace(.003, width-.003, 41))
            for a, b in ((0, width*.5-.055), (width*.5+.055, width)):
                count = max(2, round((b-a)/D.D.BOARD_WIDTH))
                x.extend(np.linspace(a, b, count+1)[1:-1])
            x.extend([width*.5-.04, width*.5, width*.5+.04])
            xx, zz = np.meshgrid(x, np.linspace(.003, height-.003, 29))
            origins = np.column_stack((xx.ravel(), np.full(xx.size, 3.), zz.ravel()))
            hits = ray_hits(triangles, origins, (0, -1, 0), 5.01)
            assert np.isfinite(hits).all(), (name, row, 'See-through board seam')
            total_coverage += len(origins)
            grip_z = min(43., height*.43)
            for centre in (width*.5-3.2, width*.5+3.2):
                yy, zz = np.meshgrid((.75, 1., 1.25), np.linspace(grip_z-1.5, grip_z+1.5, 9))
                origins = np.column_stack((np.full(yy.size, centre-.55), yy.ravel(), zz.ravel()))
                assert not np.isfinite(ray_hits(triangles, origins, (1, 0, 0), 1.10)).any(), 'Grip opening blocked'
                total_clearance += len(origins)
                origins = np.column_stack((np.full(9, centre), np.full(9, 3.), np.linspace(grip_z-1.5, grip_z+1.5, 9)))
                hits = ray_hits(triangles, origins, (0, -1, 0), 1.3)
                assert np.isfinite(hits).all(), 'Grip front missing'
                total_grips += len(origins)
            latch_z = grip_z-7.5
            yy, zz = np.meshgrid((.4, .55, .75), (latch_z-.74, latch_z+.74))
            origins = np.column_stack((np.full(yy.size, width*.5+2.45-.6), yy.ravel(), zz.ravel()))
            assert not np.isfinite(ray_hits(triangles, origins, (1, 0, 0), 1.2)).any(), 'Staple throat closed'
            total_keeper_clearance += len(origins)
            checked.append(dict(model=name, axis=wall.axis, outward=wall.outward,
                                opening=row['opening'], exported_triangles=int(inside.sum())))
    assert all(D.sha(K.ROOT/p) == h for p, h in manifest['protected'].items())
    report = dict(status='offline_mesh_checks_passed', revision=manifest['revision'],
                  manifest_sha256=D.sha(OUT/'manifest.json'), verifier_sha256=D.sha(__file__),
                  coverage_rays=total_coverage, clear_grip_rays=total_clearance,
                  solid_grip_rays=total_grips, clear_staple_rays=total_keeper_clearance,
                  doors=checked, byte_identical_reproductions=repeated,
                  protected_live_files_unchanged=len(manifest['protected']),
                  native_compile='not_run', native_visual_review='not_run', native_performance='not_measured')
    (OUT/'verification.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k != 'doors'}, indent=2))


if __name__ == '__main__':
    verify()

"""Stage a bounded canopy-density study, with byte-identical geometry controls."""
import hashlib
import json
import os
from pathlib import Path

os.environ.setdefault('BELLTOWER_SKIP_WMI', '1')

import numpy as np
import belltower_quality_forest as F


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/belltower/quality/forest-distribution-v1'
CACHE = ROOT / 'output/belltower/quality/parcel-v4-forest/crowns.npy'
SECTORS = tuple((x, y) for x in range(-4, 0) for y in (-1, 0))
ACCEPTED = 'models/maps/belltower/forest/parcel-v4'
PRIVATE = 'models/maps/belltower/forest/distribution-v1'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash01(x, y, salt):
    # Independent of the accepted seed, which was itself used for budget sorting.
    with np.errstate(over='ignore'):
        value = np.asarray(x, dtype=np.int64).astype(np.uint64) * np.uint64(0x9E3779B185EBCA87)
        value ^= np.asarray(y, dtype=np.int64).astype(np.uint64) * np.uint64(0xC2B2AE3D27D4EB4F)
        value ^= np.uint64(salt)
        value = (value ^ (value >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        value = (value ^ (value >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        value ^= value >> np.uint64(31)
    return (value >> np.uint64(11)).astype(np.float64) / 2**53


def smooth(value):
    value = np.clip(value, 0, 1)
    return value * value * (3 - 2 * value)


def noise(e, n, scale, salt):
    x, y = e / scale, n / scale
    ix, iy = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
    tx, ty = smooth(x - ix), smooth(y - iy)
    a = hash01(ix, iy, salt) * (1 - tx) + hash01(ix + 1, iy, salt) * tx
    b = hash01(ix, iy + 1, salt) * (1 - tx) + hash01(ix + 1, iy + 1, salt) * tx
    return a * (1 - ty) + b * ty


def retention(e, n):
    field = .65 * noise(e, n, 900, 0x61F07) + .35 * noise(e, n, 370, 0xB4123)
    clustered = .5 + .5 * smooth((field - .3) / .4)
    # The native study replaces a bounded west-facing strip. Return to accepted
    # distribution at their outer boundary instead of introducing a trial seam.
    edge = np.minimum.reduce((e + 48000, -e, n + 12000, 12000 - n))
    envelope = smooth(edge / 2500)
    return 1 - (1 - clustered) * envelope


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    accepted = json.loads((ROOT / 'output/belltower/quality/parcel-v4-forest/manifest.json').read_text())
    assert sha(ROOT / 'Tools/belltower_quality_forest.py') == accepted['generator_sha256']
    assert sha(ROOT / 'Sources/Belltower/landscape/forest.json') == accepted['source_group_sha256']
    assert sha(ROOT / 'Assets/shaders/belltower_forest.shader') == accepted['shader_sha256']
    assert sha(ROOT / 'Sources/Belltower/generated/forest-trees-v1.png') == accepted['atlas_sha256']
    crowns = np.load(CACHE)
    assert crowns.shape == (320000, 12) and np.isfinite(crowns).all()
    sector_ids = np.floor(crowns[:, :2] / F.SECTOR).astype(int)
    files, overrides, counts = [], [], []
    selected_indices, kept_indices = [], []
    for x, y in SECTORS:
        ids = np.flatnonzero(np.all(sector_ids == (x, y), axis=1))
        source = crowns[ids]
        assert len(source)
        e, n = source[:, 0], source[:, 1]
        probability = retention(e, n)
        keep = hash01(np.floor(e / F.GRID).astype(int), np.floor(n / F.GRID).astype(int), 0xF1304D) < probability
        retained = source[keep]
        assert 0 < len(retained) < len(source)
        assert np.array_equal(retained, crowns[ids[keep]])
        selected_indices.extend(ids.tolist())
        kept_indices.extend(ids[keep].tolist())
        name = f'belltower_forest_{x+8:02}_{y+8:02}'
        paths = {}
        for label, data in (('control', source), ('clumped', retained)):
            F.RESOURCE = f'{PRIVATE}/{label}'
            F.MATERIAL = 'materials/belltower/forest/forest_trees.vmat'
            triangles = F.write_sector(STAGE, name, data)
            assert triangles == len(data) * 2
            for suffix in ('obj', 'mtl', 'vmdl'):
                relative = f'{F.RESOURCE}/{name}.{suffix}'
                path = STAGE / 'Assets' / relative
                live = ROOT / 'Assets' / relative
                assert not live.exists() or sha(live) == sha(path), 'Use a new revision for different installed geometry'
                files.append(dict(path=relative, source=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
            paths[label] = f'{F.RESOURCE}/{name}.vmdl'
        original_obj = ROOT / 'Assets' / ACCEPTED / (name + '.obj')
        control_obj = STAGE / 'Assets' / PRIVATE / 'control' / (name + '.obj')
        assert sha(original_obj) == sha(control_obj), f'Control geometry differs: {name}'
        overrides.append(dict(original=f'{ACCEPTED}/{name}.vmdl', **paths))
        counts.append(dict(sector=[x, y], original=len(source), candidate=len(retained),
                           retained_fraction=float(keep.mean()), control_obj_exact=True,
                           expected_retention_min=float(probability.min()), expected_retention_mean=float(probability.mean())))
    np.save(STAGE / 'selected-indices.npy', np.asarray(selected_indices, dtype=np.int32))
    np.save(STAGE / 'retained-indices.npy', np.asarray(kept_indices, dtype=np.int32))
    # Explicitly verify that every region edge reaches unchanged density.
    probe = np.linspace(-48000, 0, 129)
    for e, n in ((probe, np.full_like(probe, -12000)), (probe, np.full_like(probe, 12000)),
                 (np.full_like(probe, -48000), probe), (np.zeros_like(probe), probe)):
        assert np.all(retention(e, n) == 1)
    inputs = [Path(__file__), CACHE, ROOT / 'Tools/belltower_quality_forest.py',
              ROOT / 'Sources/Belltower/landscape/forest.json', ROOT / 'Assets/scenes/maps/Belltower/belltower.scene',
              ROOT / 'Assets/shaders/belltower_forest.shader', ROOT / 'Assets/materials/belltower/forest/forest_trees.vmat',
              ROOT / 'Sources/Belltower/generated/forest-trees-v1.png']
    manifest = dict(revision='forest-distribution-v1', files=files, model_overrides=overrides, sectors=counts,
                    source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                    changed_sectors=len(SECTORS), unchanged_sectors=88-len(SECTORS), original_cards=len(selected_indices), candidate_cards=len(kept_indices),
                    positions_heights_sizes_uvs_and_material_unchanged_for_retained_cards=True,
                    candidate_is_exact_subset=True, trial_boundary_retention_one=True,
                    new_colliders=0, source_pixels_changed=False, accepted_assets_written=False, native_verified=False,
                    appearance_hypothesis='Correlated density gaps may break the uniform crown pattern without moving trees or shortening the accepted distance fade.',
                    limitations=['Only a bounded near-ridge study, not a full-forest replacement.',
                                 'Underlying painted canopy is unchanged; it may still carry repetition.',
                                 'Native appearance, culling and performance remain unverified.'])
    (STAGE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(staged_files=len(files), sectors=counts, original_cards=len(selected_indices),
                          candidate_cards=len(kept_indices), accepted_assets_written=False)))


if __name__ == '__main__':
    main()

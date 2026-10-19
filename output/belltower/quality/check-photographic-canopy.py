"""Check ordering, tile continuity and unchanged planted trees in offline trials."""
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
QUALITY = ROOT/'output/belltower/quality'
sys.path.insert(0, str(ROOT/'Tools'))
import belltower_photographic_canopy as C
import numpy as np

C.numba.set_num_threads(2)
crowns = C.T.swatch_crowns()
size, span = 256, 1600.
step = span/(size-1)


def render(painter, inputs, width=size, e0=0.):
    top, cov = np.zeros((size, width)), np.zeros((size, width))
    colour = np.zeros((size, width, 3))
    cid = np.full((size, width), -1, np.int64)
    painter(inputs, e0, span, step, step, step, top, colour, cov, cid, C.V._GRADIENTS)
    shadow = np.zeros_like(top)
    C.P._shadows(inputs, e0, span, step, step, step, top, cid, shadow)
    shaded = (colour+C.P.WOOD_FLOOR*(1-cov[..., None]))*(1-shadow[..., None]*(1-C.P.SHADOW_TINT))
    assert np.isfinite(shaded).all() and np.isfinite(top).all()
    assert cov.min() >= 0 and cov.max() <= 1
    return shaded, top, cov


def compare(a, b):
    return [float(np.max(np.abs(x-y))) for x, y in zip(a, b)]


order = np.random.default_rng(1907).permutation(len(crowns))
base = render(C.photographic_tops, crowns)
permuted = render(C.photographic_tops, crowns[order])
permutation_error = compare(base, permuted)
assert max(permutation_error) < 1e-8, permutation_error
left = render(C.photographic_tops, crowns, size//2)
right = render(C.photographic_tops, crowns, size//2, size//2*step)
tiled = [np.concatenate((a, b), axis=1) for a, b in zip(left, right)]
tile_error = compare(base, tiled)
assert max(tile_error) < 1e-8, tile_error

planted = crowns.copy()
planted[:, 6] = C.P.OLIVE
planted_error = compare(render(C.photographic_tops, planted), render(C.ACCEPTED_TOPS, planted))
assert max(planted_error) == 0, planted_error

species = (C.P.OAK, C.P.HOLM, C.P.BEECH, C.P.WILLOW)
for index, species_id in enumerate(species):
    crowns[index::4, 6] = species_id
all_species = render(C.photographic_tops, crowns)
all_species_error = compare(all_species, render(C.photographic_tops, crowns[order]))
assert max(all_species_error) < 1e-8, all_species_error

previous_path = QUALITY/'canopy-photo-v1-diagnostic/painter-before.py'
spec = importlib.util.spec_from_file_location('canopy_before_layering', previous_path)
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
old_error = compare(render(previous.photographic_tops, crowns), render(previous.photographic_tops, crowns[order]))
assert old_error[0] > 1e-3, 'The regression must distinguish the original order-dependent painter.'

atlas_hash = hashlib.sha256(C.ATLAS.read_bytes()).hexdigest()
assert atlas_hash == '626406fbe52bdcb13581241206f9ae0632b7db704659bb614ee976f0e1214701'
report = {'state':'offline checks passed; engine validation pending',
          'max_errors_rgb_top_coverage':{'permutation':permutation_error, 'tiles':tile_error,
                                       'planted_trees':planted_error, 'four_species':all_species_error,
                                       'before_ordering_fix':old_error},
          'original_atlas_sha256':atlas_hash,
          'sources':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in (Path(C.__file__), Path(C.T.__file__), Path(C.P.__file__))}}
(QUALITY/'canopy-photo-v2-checks.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)

"""Focused regression checks for this one relocated procedural crate group."""
import json
import sys
import types
from collections import Counter
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'Tools'))
import belltower_map as B
import belltower_market_crates_v3 as M
import map_kit as K

variants = Counter()
for seed in range(128):
    old_rng = np.random.default_rng(seed)
    new_rng = np.random.default_rng(seed)
    old_sizes, new_sizes = [], []
    def old_crate(model, at, size=40., yaw=0., z=0.):
        old_sizes.append(size)
        return z+size
    original = types.FunctionType(B.crates.__code__, {**B.crates.__globals__, 'crate': old_crate},
                                  argdefs=B.crates.__defaults__)
    original(K.Model(), M.OLD_ANCHOR, 10., old_rng)
    model = K.Model()
    M.stack(model, new_rng, B.Place, B.WOOD, builder=lambda model, p, size: new_sizes.append(size))
    assert old_sizes == new_sizes
    assert old_rng.bit_generator.state == new_rng.bit_generator.state
    assert len(model.boxes) == len(new_sizes)
    variants[len(new_sizes)] += 1

result = {'rng_preserved_seeds': 128, 'crate_count_variants': dict(variants),
          'subsequent_map_prop_random_draws_unchanged': True}
(Path(__file__).parent/'source-validation.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps(result))

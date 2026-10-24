"""Read the six crate placements without changing shared assets."""
import json
from pathlib import Path
import re
import sys
sys.path.insert(0, str(Path('Tools').resolve()))
import belltower_stage_market_crates as S

manifest = json.loads(Path('output/belltower/crate-placement-v1/revision5/manifest.json').read_text())
models = {}
for kind in ['old', 'new']:
    model = S.K.Model()
    for row in manifest[kind]:
        S.Crates.build(model, S.frame(row), row['size'])
    models[kind] = model
report = {}
for side in ['west', 'east']:
    vmdl = Path(f'Assets/models/maps/belltower/belltower_{side}.vmdl')
    source = vmdl.read_text()
    imports = [Path('Assets')/p for p in re.findall(r'filename = "([^"]+\.obj)"', source)
               if '/compiler-safe/' in p and any(x in p for x in ['furniture_wood', 'iron_black', 'endgrain'])]
    report[side] = {}
    for kind, model in models.items():
        wanted = S.geometry(model if side == 'west' else model.mirrored())
        found, _ = S.patch_obj(vmdl.with_suffix('.obj'), wanted, None, set())
        bounded = S.Counter()
        for path in imports:
            seen, _ = S.patch_obj(path, wanted, None, set())
            bounded.update(seen)
        report[side][kind] = {'canonical': sum(found.values()), 'bounded': sum(bounded.values()),
                              'expected': sum(wanted.values())}
    report[side]['collider_origins'] = [line.strip() for line in source.splitlines()
        if 'origin = [' in line and any(S.K.vec3(r['after']) in line or S.K.vec3(r['before']) in line
        for r in manifest['physics_changes'][side])]
print(json.dumps(report, indent=2))

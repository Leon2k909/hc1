from pathlib import Path
from array import array
from collections import Counter
import json
import math

out = Path(__file__).resolve().parent
report = {}
for side in ('east', 'west'):
    path = Path('Assets/models/maps/belltower/belltower_' + side + '.obj')
    counts = Counter()
    invalid = []
    materials = Counter()
    for number, line in enumerate(path.open('rb'), 1):
        kind = line.split(b' ', 1)[0]
        if kind in (b'v', b'vt', b'vn'):
            counts[kind.decode()] += 1
            if not all(math.isfinite(float(x)) for x in line.split()[1:]):
                invalid.append({'line': number, 'reason': 'nonfinite vector'})
    used = {k: bytearray(counts[k] + 1) for k in ('v', 'vt', 'vn')}
    material = None
    for number, line in enumerate(path.open('rb'), 1):
        if line.startswith(b'usemtl '):
            material = line.split()[1].decode()
        elif line.startswith(b'f '):
            counts['faces'] += 1
            materials[material] += 1
            for token in line.split()[1:]:
                values = token.split(b'/')
                for key, text in zip(('v', 'vt', 'vn'), values):
                    if not text:
                        continue
                    index = int(text)
                    if index < 0:
                        index += counts[key] + 1
                    if not 1 <= index <= counts[key]:
                        invalid.append({'line': number, 'reason': 'out of range', 'kind': key, 'index': index})
                    else:
                        used[key][index] = 1
    report[side] = {'path': str(path), 'counts': dict(counts),
        'unused': {k: counts[k] - sum(mask) for k, mask in used.items()},
        'invalid_count': len(invalid), 'invalid_examples': invalid[:10], 'materials': materials}
    print(json.dumps(report[side]), flush=True)
(out / 'obj-analysis.json').write_text(json.dumps(report, indent=2))

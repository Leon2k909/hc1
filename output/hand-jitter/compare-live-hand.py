import json, math
from pathlib import Path

folder = Path(__file__).parent
for name in ('before', 'after'):
    samples = json.loads((folder / f'hand-jitter-{name}.json').read_text())
    positions = [[float(n) for n in s['Left'].split(',')] for s in samples]
    steps = [math.dist(a,b) for a,b in zip(positions,positions[1:])]
    print(name, 'max left-hand jump in inches', round(max(steps), 8),
          'IK weight', sorted(set(s.get('HandIkWeight', 1) for s in samples)),
          'yaw range', (min(s['Yaw'] for s in samples), max(s['Yaw'] for s in samples)),
          'bob range', (min(s['Bob'] for s in samples), max(s['Bob'] for s in samples)))
    print('clothing mismatch', max(s['ClothingError'] for s in samples))
    stable = samples[15:]
    positions = [[float(n) for n in s['Left'].split(',')] for s in stable]
    steps = [math.dist(a,b) for a,b in zip(positions,positions[1:])]
    print('after initial animation/hotload settle:', max(steps), 'clothing mismatch', max(s['ClothingError'] for s in stable))

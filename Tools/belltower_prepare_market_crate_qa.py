"""Prepare read-only crate placement probes and temporary restored native captures."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import belltower_market_crates_v3 as M

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/crates-v3-20261021'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', choices=['before', 'after'], default='before')
    parser.add_argument('--view', choices=['wide', 'lid', 'detail', 'original'])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.view:
        original = ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt'
        helper = OUT/'capture.cs.txt'
        text = original.read_text().replace('output/belltower/fountain-ornaments-v2/capture-request.json',
                                           'output/belltower/crates-v3-20261021/capture-request.json')
        text = text.replace('Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt',
                            'output/belltower/crates-v3-20261021/capture.cs.txt')
        if helper.exists(): assert helper.read_text() == text
        else: helper.write_text(text)
        eye, target, fov = {
            'wide': ((1440, -1400, 155), (1148, -1415, 30), 75),
            'lid': ((1218, -1470, 110), (1127, -1470, 27), 72),
            'detail': ((1260, -1565, 140), (1174, -1476, 55), 64),
            'original': ((1273.32043, -1266.479, 98.6655121), (1186.64, -1324.46, 25), 72),
        }[args.view]
        dx, dy, dz = np.subtract(target, eye)
        angles = (-math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)), 0)
        request = {'directory': 'market-crates-v3-'+args.phase, 'name': args.view,
                   'position': ','.join(map(str, eye)), 'angles': ','.join(map(str, angles)),
                   'width': 1600, 'height': 1200, 'fov': fov, 'exposure': 1.,
                   # Synchronous camera changes are restored before the script
                   # yields, so no other editor user's camera can be overwritten.
                   'settle_ms': 0,
                   'expected_scene_sha256': hashlib.sha256((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest()}
        (OUT/'capture-request.json').write_text(json.dumps(request, indent=2)+'\n')
        print(json.dumps(request))
    else:
        calls = []; labels = []
        for side in ('east', 'west'):
            for index, (origin, x, size) in enumerate(M.OLD_ROWS):
                yaw = math.degrees(math.atan2(x[1], x[0]))
                new, angle = M.location(index, yaw)
                for label, p in [('old', origin), ('new', new)]:
                    e, n, z = p
                    world_y = -e if side == 'west' else e
                    labels.append({'side': side, 'crate': index, 'site': label, 'world': [n, world_y, 0]})
                    calls.append({'name': 'scene_trace', 'arguments': {'from': f'{n},{world_y},100', 'to': f'{n},{world_y},-8'}})
        (OUT/'trace-args.json').write_text(json.dumps({'calls': calls})+'\n')
        (OUT/'trace-labels.json').write_text(json.dumps(labels, indent=2)+'\n')
        print('Prepared 12 floor/obstruction probes.')


if __name__ == '__main__': main()

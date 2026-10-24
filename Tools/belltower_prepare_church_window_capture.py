"""Prepare the native facade review without using the fountain's request files."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/church-windows-v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True)
    parser.add_argument('--view', choices=['facade', 'detail', 'inside'], default='facade')
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    template = (ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt').read_text()
    helper = ROOT/'Sources/Belltower/editor/capture-church-windows-v1.cs.txt'
    text = template.replace('output/belltower/fountain-ornaments-v2/capture-request.json', 'output/belltower/church-windows-v1/capture-request.json')
    text = text.replace('Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt', 'Sources/Belltower/editor/capture-church-windows-v1.cs.txt')
    if helper.exists(): assert helper.read_text() == text
    else: helper.write_text(text)
    position, target, fov = {
        'facade': ((-60, -25, 201), (-400, 0, 181), 58),
        'detail': ((-285, -54, 246), (-402, 0, 237), 58),
        'inside': ((-540, 15, 215), (-407, 0, 225), 70),
    }[args.view]
    d = [b-a for a, b in zip(position, target)]
    angles = (-math.degrees(math.atan2(d[2], math.hypot(*d[:2]))), math.degrees(math.atan2(d[1], d[0])), 0)
    scene = ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
    request = {'directory': 'church-windows-v1-'+args.phase, 'name': args.view, 'width': 1600, 'height': 1200,
               'fov': fov, 'exposure': 1., 'settle_ms': 3500, 'position': ','.join(map(str, position)),
               'angles': ','.join(map(str, angles)), 'expected_scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(request, indent=2)+'\n')
    print(json.dumps(request))


if __name__ == '__main__': main()

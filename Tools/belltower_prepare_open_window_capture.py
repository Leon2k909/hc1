"""Prepare repeatable native views of the usable town windows."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/open-windows-v1'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True)
    parser.add_argument('--view', choices=['hall', 'bakery', 'bakery-covered', 'bakery-inside', 'inn', 'tavern', 'inside'], default='hall')
    parser.add_argument('--live', action='store_true', help='Render the saved editor scene without moving a live viewport.')
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    template = (ROOT/'Sources/Belltower/editor/capture-church-windows-v1.cs.txt').read_text()
    helper = ROOT/'Sources/Belltower/editor/capture-open-windows-v1.cs.txt'
    text = template.replace('church-windows-v1/capture-request.json', 'open-windows-v1/capture-request.json')
    text = text.replace('capture-church-windows-v1.cs.txt', 'capture-open-windows-v1.cs.txt')
    if helper.exists():
        assert helper.read_text() == text
    else:
        helper.write_text(text)
    position, target, fov = {
        'hall': ((1230, 440, 266), (1100, 385, 252), 65),
        'bakery': ((1230, 1110, 100), (1100, 1170, 71), 72),
        'bakery-covered': ((1180, 1155, 57), (1100, 1170, 72), 78),
        'bakery-inside': ((1030, 1130, 76), (1100, 1170, 71), 85),
        'inn': ((50, 1230, 234), (-100, 1170, 219), 65),
        'tavern': ((50, -1230, 234), (-100, -1170, 219), 65),
        'inside': ((989, 420, 247), (1100, 385, 252), 75),
    }[args.view]
    delta = [b-a for a, b in zip(position, target)]
    angles = (-math.degrees(math.atan2(delta[2], math.hypot(*delta[:2]))),
              math.degrees(math.atan2(delta[1], delta[0])), 0)
    scene = ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
    request = {'directory': 'open-windows-v1-'+args.phase, 'name': args.view,
               'width': 1600, 'height': 1200, 'fov': fov, 'exposure': 1., 'settle_ms': 0 if args.live else 3500,
               'position': ','.join(map(str, position)), 'angles': ','.join(map(str, angles)),
               'expected_scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(request, indent=2)+'\n')
    print(json.dumps(request))


if __name__ == '__main__':
    main()

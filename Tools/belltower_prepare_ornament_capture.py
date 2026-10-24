"""Prepare a bounded native fountain capture with the established restoration checks."""
import argparse
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/fountain-ornaments-v2'
HELPER = ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--phase', required=True)
    parser.add_argument('--view', choices=['lion', 'lily', 'overview'], required=True)
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    original = (ROOT/'Sources/Belltower/editor/capture-art-trials-oct19.cs.txt').read_text().splitlines(keepends=True)
    source = original[:39]
    source += ['var surfaceSlots=0; var forestSlots=0; var forestVariant="accepted";\n',
               'var trialManifests=new System.Collections.Generic.Dictionary<string,string>();\n']
    source += original[74:82]
    source += ['var materials=new System.Collections.Generic.HashSet<Material>();\n']
    source += original[87:131]
    source += original[166:]
    text = ''.join(source).replace('output/belltower/quality/art-preview-oct19.json',
                                  'output/belltower/fountain-ornaments-v2/capture-request.json')
    text = text.replace('Sources/Belltower/editor/capture-art-trials-oct19.cs.txt',
                        'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt')
    if HELPER.exists():
        assert HELPER.read_text() == text, 'Shared capture helper changed.'
    else:
        HELPER.write_text(text)
    position, target, fov = {
        'lion': ((95, -90, 57), (130, -32, 47), 42),
        'lily': ((113, -80, 94), (130, -28, 89), 42),
        'overview': ((-220, -370, 186), (130, 0, 110), 58),
    }[args.view]
    delta = [b-a for a, b in zip(position, target)]
    angles = (-math.degrees(math.atan2(delta[2], math.hypot(*delta[:2]))), math.degrees(math.atan2(delta[1], delta[0])), 0)
    scene = ROOT/'Assets/scenes/maps/Belltower/belltower.scene'
    request = {'directory': 'fountain-ornaments-v2-'+args.phase, 'name': args.view,
               'width': 1600, 'height': 1200, 'fov': fov, 'exposure': 1., 'settle_ms': 3500,
               'position': ','.join(map(str, position)), 'angles': ','.join(map(str, angles)),
               'expected_scene_sha256': hashlib.sha256(scene.read_bytes()).hexdigest()}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT/'capture-request.json').write_text(json.dumps(request, indent=2)+'\n')
    print(json.dumps(request))


if __name__ == '__main__':
    main()

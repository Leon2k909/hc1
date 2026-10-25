"""Prepare a synchronous native shop-awning capture and restore the viewport."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import numpy as np
import map_kit as K

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'output/belltower/shop-awning-cloth-v1'
HELPER = ROOT/'Sources/Belltower/editor/capture-shop-awning-cloth-v1.cs.txt'


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--phase', required=True)
    parser.add_argument('--view', choices=['oblique', 'below', 'mirrored', 'side'], required=True)
    args = parser.parse_args()
    assert all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-' for c in args.phase)
    source = (ROOT/'Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt').read_text()
    source = source.replace('output/belltower/fountain-ornaments-v2/capture-request.json',
                            'output/belltower/shop-awning-cloth-v1/capture-request.json')
    source = source.replace('Sources/Belltower/editor/capture-fountain-ornaments-v2.cs.txt',
                            'Sources/Belltower/editor/capture-shop-awning-cloth-v1.cs.txt')
    # No camera pose survives an await. A few synchronous frames let this fixed
    # camera's exposure history settle without moving the interactive viewport.
    source = source.replace('camera.RenderToBitmap(bitmap, false);',
                            'for (var frame = 0; frame < 4; frame++) camera.RenderToBitmap(bitmap, false);')
    if HELPER.exists(): assert HELPER.read_text() == source
    else: HELPER.write_text(source)
    manifest = json.loads((OUT/'revision2/stage/manifest.json').read_text())
    rows = manifest['placements_west']
    candidates = [r for r in rows if r['paint'] == 'canvas_red' and r['name'] is None]
    row = (candidates or [r for r in rows if r['paint'] == 'canvas_red'])[0]
    along = np.array((1., 0., 0.)) if row['axis'] == 'e' else np.array((0., 1., 0.))
    out = np.array((0., row['sign'], 0.)) if row['axis'] == 'e' else np.array((row['sign'], 0., 0.))
    r, depth = (row['r0']+row['r1'])/2, row['depth']
    centre = np.array((r, depth, row['z'])) if row['axis'] == 'e' else np.array((depth, r, row['z']))
    target = centre+out*row['reach']*.60+np.array((0., 0., -row['reach']*.45*.60-2))
    position = target+out*100+along*55+np.array((0., 0., 50))
    if args.view == 'below': position = target+out*118+along*28+np.array((0., 0., -44))
    if args.view == 'side': position = target+out*35+along*102+np.array((0., 0., 42))
    if args.view == 'mirrored': target[0] *= -1; position[0] *= -1
    position, target = K.to_world(position), K.to_world(target)
    delta = target-position
    angles = (-math.degrees(math.atan2(delta[2], math.hypot(*delta[:2]))), math.degrees(math.atan2(delta[1], delta[0])), 0.)
    request = {'directory': 'shop-awning-cloth-v1-'+args.phase, 'name': args.view, 'exposure': 1.,
               'width': 1600, 'height': 1200, 'fov': 65., 'settle_ms': 0,
               'position': ','.join(map(str, position)), 'angles': ','.join(map(str, angles)),
               'expected_scene_sha256': hashlib.sha256((ROOT/'Assets/scenes/maps/Belltower/belltower.scene').read_bytes()).hexdigest()}
    (OUT/'capture-request.json').write_text(json.dumps(request, indent=2)+'\n')
    print(json.dumps({'view': args.view, 'awning': row, 'request': request}))


if __name__ == '__main__': main()

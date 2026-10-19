"""Capture one native decal study at a time while preserving the shared session."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VIEWS = {
    'ground-edge': ((-1313.323, 379.7965, 64), (-1393.323, 379.7965, 26), 90),
    'ground-edge-close': ((-1313.323, 379.7965, 38), (-1393.323, 379.7965, 1), 65),
    'ground-edge-sunlit': ((-1936.32457, 627.60665, 64), (-1856.32457, 627.60665, 26), 90),
    'ground-edge-sunlit-close': ((-1936.32457, 627.60665, 38), (-1856.32457, 627.60665, 1), 65),
    'ground-edge-east-street': ((1313.323, 379.7965, 64), (1393.323, 379.7965, 26), 90),
    'ground-edge-east-street-close': ((1313.323, 379.7965, 38), (1393.323, 379.7965, 1), 65),
    'ground-edge-east-wall': ((1936.32457, 627.60665, 64), (1856.32457, 627.60665, 26), 90),
    'ground-edge-east-wall-close': ((1936.32457, 627.60665, 38), (1856.32457, 627.60665, 1), 65),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--views', nargs='+', choices=VIEWS, required=True)
    parser.add_argument('--trial', action='store_true')
    parser.add_argument('--mix', type=float, default=.5)
    parser.add_argument('--all-placements', action='store_true')
    args = parser.parse_args()
    if not math.isfinite(args.mix) or not 0 <= args.mix <= 1:
        parser.error('--mix must be finite and between zero and one')
    for view in args.views:
        eye, target, fov = VIEWS[view]
        position = (eye[1], -eye[0], eye[2])
        destination = (target[1], -target[0], target[2])
        dx, dy, dz = (b - a for a, b in zip(position, destination))
        angles = (-math.degrees(math.atan2(dz, math.hypot(dx, dy))), math.degrees(math.atan2(dy, dx)), 0)
        config = dict(directory=args.directory, name=view, position=position, angles=','.join(map(str, angles)),
                      fov=fov, trial=args.trial, mix=args.mix, all_placements=args.all_placements)
        (ROOT / 'output/belltower/quality/ground-edge-v2/capture.json').write_text(json.dumps(config, indent=2) + '\n')
        subprocess.run([sys.executable, '-X', 'utf8', 'output/knife-throw/editor_check.py', '--pid', str(args.pid),
                        '--script', 'Sources/Belltower/editor/capture-ground-decals.cs.txt', '--output-dir',
                        'output/belltower/quality/' + args.directory, '--timeout', '60', '--cleanup-exchange', '--direct-call'],
                       cwd=ROOT, check=True)
        folder = ROOT / 'output/belltower/quality' / args.directory
        result = json.loads((folder / f'{view}-camera.json').read_text())
        restored = json.loads((folder / f'{view}-restore.json').read_text())
        expected = (116 if args.all_placements else 2) if args.trial else 0
        assert result['TrialDecals'] == restored['DecalsRemoved'] == expected
        assert result['GamePreserved'] and result['SelectedDocumentPreserved'] and not result['SceneHasUnsavedChanges']
        assert restored['ObjectsRestored'] and restored['ToneRestored']
        assert result['NativeExposure'] == dict(MinExposure=2, MaxExposure=2, Compensation=0)
        print(json.dumps(dict(view=view, decals=expected, restored=True)), flush=True)


if __name__ == '__main__':
    main()

"""Sequential hidden-document comparison with a fixed material and exposure."""
import argparse
import json
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]
VIEWS = {'west-ridge': 80, 'west-ridge-detail': 35}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--directory', required=True)
    parser.add_argument('--variant', choices=('accepted', 'control', 'clumped'), required=True)
    parser.add_argument('--views', nargs='+', choices=VIEWS, required=True)
    args = parser.parse_args()
    for view in args.views:
        config = dict(directory=args.directory, name=view, position='125,250,64', angles='-3.37,90,0', fov=VIEWS[view],
                      width=1920, height=1080, forest_coverage_trial=True, forest_coverage_strength=0,
                      sync_main_postprocess=True, distribution_variant=args.variant,
                      look_trial=dict(minimum_exposure=2, maximum_exposure=2, compensation=0, mode='ACES'))
        (ROOT / 'output/belltower/quality/forest-distribution-v1/capture.json').write_text(json.dumps(config, indent=2) + '\n')
        subprocess.run([sys.executable, '-X', 'utf8', 'output/knife-throw/editor_check.py', '--pid', str(args.pid),
                        '--script', 'Sources/Belltower/editor/capture-forest-distribution.cs.txt', '--output-dir',
                        'output/belltower/quality/' + args.directory, '--timeout', '60', '--cleanup-exchange', '--direct-call'],
                       cwd=ROOT, check=True)
        folder = ROOT / 'output/belltower/quality' / args.directory
        metadata = json.loads((folder / f'{view}-camera.json').read_text())
        assert metadata['GamePreserved'] and metadata['SelectedDocumentPreserved'] and not metadata['SceneHasUnsavedChanges']
        assert metadata['TrialForestCoverageSlots'] == 88 and metadata['ForestCoverageParameters']['StrengthOverride'] == 0
        assert json.loads((folder / f'{view}-restore.json').read_text()) == dict(MaterialsRestored=True, Slots=88)
        assert json.loads((folder / f'{view}-look-restore.json').read_text()) == dict(ToneRestored=True)
        assert json.loads((folder / f'{view}-distribution-restore.json').read_text()) == dict(ModelsRestored=True, Models=0 if args.variant == 'accepted' else 8)
        print(json.dumps(dict(view=view, variant=args.variant, original_state_restored=True)), flush=True)


if __name__ == '__main__':
    main()

"""Publish the checked placement-only patch when the s&box editor is closed.

An open editor requires the native route instead. No editor is launched here.
Every target is backed up and checked for concurrent changes before replacement.
"""
import argparse
import csv
import inspect
import io
import json
import os
from pathlib import Path
import shutil
import subprocess

import veridant_parts as P
from veridant_lamp_placement import MOVES
from veridant_stage_lamp_placement import ROOT, OUT, sha


def no_editor():
    result = subprocess.run(['tasklist', '/FO', 'CSV', '/NH'], check=True,
                            capture_output=True, text=True)
    editors = [row[:2] for row in csv.reader(io.StringIO(result.stdout))
               if row and row[0].lower() in ('sbox-dev.exe', 'sbox.exe')]
    assert not editors, f'Editor started; use native publication instead: {editors}'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    args = parser.parse_args()
    stage = OUT / args.stage
    manifest = json.loads((stage / 'manifest.json').read_text())
    validation = json.loads((OUT / 'validation-staged.json').read_text())
    assert validation['lamps_moved'] == len(MOVES) and not validation['failures']
    hook = inspect.getsource(P.lantern_post)
    assert 'b = v( *placed_base( name, base ) )' in hook
    no_editor()
    allowed = {'Assets/scenes/maps/Veridant/veridant.scene',
               'Assets/models/maps/veridant/lounger-v2/veridant_buildings-base.obj',
               'Assets/models/maps/veridant/chair-v2/dress-base.obj',
               'Assets/models/maps/veridant/veridant_buildings_hulls_metal.obj',
               'Assets/models/maps/veridant/veridant_dress_hulls_metal.obj'}
    assert set(manifest['files']) == allowed
    for p, item in manifest['files'].items():
        assert sha(ROOT / item['source']) == item['after']
        assert sha(ROOT / item['backup']) == item['before']
        assert sha(ROOT / p) in (item['before'], item['after']), ('Shared target changed', p)
    for p, digest in manifest['protected_sha256'].items():
        assert sha(ROOT / p) == digest, ('Shared protected file changed', p)
    imported = []
    for p, item in manifest['files'].items():
        destination = ROOT / p
        if sha(destination) == item['after']:
            continue
        no_editor()
        assert sha(destination) == item['before'], ('Shared target changed', p)
        incoming = destination.with_name(destination.name + '.lamp-incoming')
        try:
            shutil.copyfile(ROOT / item['source'], incoming)
            assert sha(incoming) == item['after']
            os.replace(incoming, destination)
        finally:
            incoming.unlink(missing_ok=True)
        imported.append(p)
    for p, item in manifest['files'].items():
        assert sha(ROOT / p) == item['after'], p
    for p, digest in manifest['protected_sha256'].items():
        assert sha(ROOT / p) == digest, p
    result = {'revision': manifest['revision'], 'stage': args.stage,
              'publication': 'Guarded atomic file replacements while the editor was closed.',
              'lamps_moved': len(MOVES), 'old_design_retained': True,
              'collision_hulls_moved': 2 * len(MOVES), 'point_lights_moved': len(MOVES),
              'unrelated_files_preserved': True, 'imported_files': imported,
              'source_hook_sha256': sha(ROOT / 'Tools/veridant_parts.py'),
              'native_visual_check': 'Pending: editor is closed.'}
    (OUT / 'installed.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()

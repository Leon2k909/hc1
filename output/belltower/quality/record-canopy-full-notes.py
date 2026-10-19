"""Append the verified full-resolution staging state to the project notes."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[3]
stage = ROOT/'output/belltower/quality/canopy-photo-v2-full'
report = json.loads((stage/'offline-review.json').read_text())
assert report['published_trial_assets'] == 0 and not report['native_verified']
assert all(zone['terrain_normal_unchanged'] for zone in report['zones'])
path = ROOT/'CLAUDE.md'
before = path.read_bytes()
text = before.decode('utf-8')
anchor = '    the accepted landscape generator, live textures, tree placement and scene are unchanged.'
assert text.count(anchor) == 1
addition = '''
    The complete 4096px candidate is now in `canopy-photo-v2-full/`. All four normal maps match the accepted files
    exactly, and zone A's colour/kind maps are also identical. `offline-review.json` records the full-size review,
    source checks and pixel comparisons; the broad far-field woodland patterns still need improvement.
    `belltower_quality_canopy.py` stages eight colour/kind textures and two material copies under a separate
    `materials/belltower/vista/canopy-photo-v2/` resource path. It preserves every other material setting and all
    accepted inputs. `import-canopy-trial.cs.txt` validates sources, dependencies and the allowlist, imports only
    missing or identical trial files, and supports inspected partial resumption. It has not run natively yet.
    Compile both trial materials, then run `verify-canopy-trial.cs.txt` to check all loaded texture dimensions.
    The capture helper's `--canopy-trial` temporarily overrides the vista and existing woodland materials together,
    prewarms 4096px colour maps for both baseline and candidate, and restores exact renderer snapshots afterward.
    Its import, resource verification and new material-override branch still require native validation. Review
    matching valley, west-ridge and terrace views before changing any accepted landscape input or manifest.'''
text = text.replace(anchor, anchor+addition)
incoming = path.with_name('CLAUDE.belltower-canopy-full.tmp')
assert not incoming.exists()
incoming.write_text(text, encoding='utf-8', newline='')
assert path.read_bytes() == before, 'Concurrent CLAUDE edit; inspect before replacing.'
incoming.replace(path)
print('Recorded full-resolution staging and pending native checks.')

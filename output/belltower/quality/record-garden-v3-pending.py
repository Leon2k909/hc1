"""Save the completed offline wheelbarrow staging and update only its project notes."""
import hashlib
import json
import os
from pathlib import Path

quality=Path('output/belltower/quality')
checkpoint_path=quality/'garden-v3-checkpoint.json'
checkpoint=json.loads(checkpoint_path.read_text())
preview=quality/'garden-v3-studio/wheelbarrow.png'
checkpoint['offline_review']={
    'image':preview.as_posix(),
    'sha256':hashlib.sha256(preview.read_bytes()).hexdigest(),
    'finding':'Clear basin, chassis below it, four underside mounts, rear supports and feet visually checked in the offline studio render.',
    'native_review_complete':False,
}
checkpoint['editor_window']='User asked to wait for the other AI. Orion is running in the shared editor; Cerro Blanco has deferred reflection captures. No garden-v3 assets published.'
checkpoint_path.write_text(json.dumps(checkpoint,indent=2)+'\n')

path=Path('CLAUDE.md')
original=path.read_bytes()
text=original.decode('utf-8')
newline='\r\n' if '\r\n' in text else '\n'
text=text.replace('\r\n','\n')
anchor='    known play session; inspect hashes and the locking process before resuming any interrupted publication.\n'
addition='''    Garden v3 is staged only: its wheelbarrow chassis stays below the basin, with four mounts and lowered braces.
    The old generator is preserved in `garden-v3-before/source/`. The basin regression check catches 138 intruding
    samples in v2 and none in v3. All 11 geometry cases, three shed trim checks and 94 gameplay checks pass;
    collision and shared RNG state are unchanged. Each staged half has 996,387 triangles, 264 more than v2.
    `garden-v3-studio/wheelbarrow.png` is an offline construction render; it has been reviewed but is not an engine
    screenshot. `garden-v3-checkpoint.json` and `models/garden-v3/native-import.json` bind the two staged OBJ files
    to installed v2. The import request selects v3; the accepted manifest still records installed v2. Wait for the
    next coordinated window, then compile and capture the wheelbarrow and terrace before recording acceptance.
'''
assert text.count(anchor)==1 and 'Garden v3 is staged only:' not in text
text=text.replace(anchor,anchor+addition)
anchor2='    separated fixed-exposure comparison in the next coordinated window. No look changes have been saved.\n'
addition2='''    `capture-camera-state.json` confirms separate main and editor cameras with valid native tone-map systems.
    The staged capture helper records `NativeExposureAfterRender`; `--sync-main-postprocess` is an opt-in diagnostic
    that updates both cameras and restores the main camera's prior exposure values. This new branch has not run
    natively yet. `aces-fixed-low` and `aces-fixed-high` use 0.35 and 2.0 bounds to make the next comparison decisive.
'''
assert text.count(anchor2)==1
text=text.replace(anchor2,anchor2+addition2)
incoming=path.with_name('CLAUDE.belltower-pending-incoming')
incoming.write_bytes(text.replace('\n',newline).encode('utf-8'))
assert path.read_bytes()==original,'Concurrent shared-document edit; inspect before replacing'
os.replace(incoming,path)
print('Recorded offline v3 review and pending native verification; updated only Belltower notes.')

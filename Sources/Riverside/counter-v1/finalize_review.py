from pathlib import Path
import json,hashlib
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];OUT=REVIEW/'output/riverside/counter-v1'
files=['in-game-front-before.png','in-game-front-after.png']
audit=dict(final_pair=files,hashes={p:hashlib.sha256((OUT/p).read_bytes()).hexdigest() for p in files},actual_play_verified_by='runtime-review.json',notes='The later wider-angle capture completed both aisle images before an external scene change interrupted the last operator-side after capture. The final comparison uses the completed matching aisle pair. The original successful play check, material checks and unchanged resource hashes remain valid. The mismatched operator-side before image is excluded.',no_additional_editor_mutations=True)
(OUT/'capture-audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
rejected=OUT/'in-game-back-before.png'
if rejected.exists():rejected.rename(OUT/'interrupted-back-before.png')
# Normalize only this task's installed documentation, which Windows wrote using its locale encoding.
paths=[ROOT/'docs/notes/riverside-ice-cabinet-v1-20261104.md',ROOT/'docs/notes/riverside-register-v1-20261104.md',ROOT/'Sources/Riverside/register-v1/README.md',Path('C:/sbox-projects/hc1/register-review/Sources/Riverside/register-v1/README.md')]
for path in paths:
    raw=path.read_bytes()
    try:text=raw.decode('utf-8')
    except UnicodeDecodeError:text=raw.decode('cp1252')
    if path.name=='README.md':
        text=text.replace('# Lucky Stop cash register v1 — review candidate','# Lucky Stop cash register v1 — installed 2026-11-04')
        text=text.replace("The original saved scene and public store ModelDoc remain unchanged by this candidate. Installation awaits approval under CLAUDE.md's graphics-upgrade rule.","User approved installation. The public store ModelDoc imports the register, preserving the ice cabinet and drinks fridge. The saved scene and physics section remain unchanged.")
    if path.name=='riverside-ice-cabinet-v1-20261104.md':
        text+='\nThe subsequent cash-register installation merged switch distances into five public LOD groups (0/10/20/25/45). Current store/drinks masks are 31 and ice masks are 3/12/16; the three cabinet meshes and their geometry remain unchanged. Earlier installation receipts describe the three-group baseline at the time the cabinet was installed.\n'
    path.write_text(text,encoding='utf-8')
readme=REVIEW/'Sources/Riverside/counter-v1/README.md'
text=readme.read_text(encoding='utf-8')
text+='\nThe final comparison uses the completed matching aisle pair. A later operator-side recapture was interrupted by an external scene switch after the aisle pair completed; see `capture-audit.json`. The mismatched operator before image is excluded. The editor is now in a separate Belltower play session, which this task leaves untouched. The latest repeatable capture script records only the aisle pair.\n'
readme.write_text(text,encoding='utf-8')
print(json.dumps(audit,indent=2))

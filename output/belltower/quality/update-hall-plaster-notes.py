from pathlib import Path
import os

path=Path('CLAUDE.md')
before=path.read_bytes()
text=before.decode('utf-8')
start=text.index('## Belltower (')
end=text.index('\n## ',start+1)
section=text[start:end]
newline='\r\n' if '\r\n' in section else '\n'
section=section.replace('\r\n','\n')
replacements={
    'the centre has 163,416.':'the centre has 246,560 after the hall joinery and deck pass.',
    '5,460 probes; 4,800 active':'5,460 probes; 4,804 active in v8',
    'The accepted daylight bake lives in `Assets/lighting/belltower/daylight-v7/`. Its six `.vtex_c` textures have no\n    uncompiled source; the narrow `.gitignore` exception is intentional.':
    'The saved scene uses daylight-v8 indirect light and the three accepted daylight-v7 reflections. These\n    `.vtex_c` textures have no uncompiled source; the narrow `.gitignore` exceptions are intentional. A fresh\n    indirect-light bake for the installed hall joinery and worn plaster is still pending.',
    'camera exposure and restores the selected document, view and game state. Use saved-scene captures for final':
    'camera exposure and preserves the selected document and game state while restoring its camera transform.\n    It uses the persistent document\'s hidden `editor_camera` directly, without selecting its tab. Mark material\n    textures used at mip size 2048 and all three indirect-light textures at their full dimension before a short\n    streaming wait; then mark the DDGI system dirty and update its volume buffer synchronously. Hidden documents\n    do not tick normally: missing prewarm can produce black shadows or blurred textures in offscreen captures.\n    Do not disable global texture streaming for this capture. Use saved-scene captures for final'
}
for old,new in replacements.items():
    assert section.count(old)==1,old
    section=section.replace(old,new)
anchor='  - `belltower_window.shader` supplies reflected glass'
assert section.count(anchor)==1
addition='''  - `belltower_interiors.py` replaces the hall's box furniture with pegged trestles, separate eased boards,
    breadboard table ends, drawer fronts, recessed archive doors, and bronze fittings. Its oak floor and ceiling
    use staggered individual boards; the ceiling beams have softened edges. Both stair openings stay clear, and
    the deck vertices remain inside the original slabs. The centre retains its 403 collision boxes and 56 hulls.
    `hall-v2-deck-checks.json` records the bounds checks; `hall-plaster-native-results.json` records native imports
    and successful compiles. `council-hall-target-v1.png` and `.json` preserve the ImageGen design reference.
  - All eight exterior plaster colours now use `belltower_plaster.shader`. It blends the clean two-metre scan
    with original 1.5-metre `rough_plaster_broken` photographs using continuous warped sampling, broad wear patches
    and stronger weathering near the base. Coverage is 0.34; normal and roughness maps follow the same blend.
    The production material generator owns these definitions. The earlier triangular sampling trial was rejected
    for visible seams. `hall-plaster-streaming/` contains native captures with material and DDGI textures resident.
'''
section=section.replace(anchor,addition+anchor)
after=(text[:start]+section.replace('\n',newline)+text[end:]).encode('utf-8')
assert path.read_bytes()==before,'CLAUDE.md changed concurrently; rerun against the new version'
temporary=path.with_name(path.name+'.belltower-notes')
temporary.write_bytes(after)
os.replace(temporary,path)
print('Updated only the Belltower section; surrounding bytes preserved.')

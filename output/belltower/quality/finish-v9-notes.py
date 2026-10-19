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
 '4,804 active in v8':'4,806 active in v9',
 'The saved scene uses daylight-v8 indirect light':'The saved scene uses daylight-v9 indirect light',
 '    `.vtex_c` textures have no uncompiled source; the narrow `.gitignore` exceptions are intentional. A fresh\n    indirect-light bake for the installed hall joinery and worn plaster is still pending.':
 '    `.vtex_c` textures have no uncompiled source; the narrow `.gitignore` exceptions are intentional.',
 '    spacing reaches the upper hall; no extra local hall volume is used. Fresh saved-scene views and the menu image\n    are in `output/belltower/quality/saved-relief-v1/`. This bake includes the revised landscape, matching trees and\n    stone relief materials; both lighting passes and all three reflections completed before publication. Its source\n    manifest also records the local shaders and textures referenced by the town materials, including the height maps.':
 '    spacing reaches the upper hall; no extra local hall volume is used. Fresh saved-scene views and the menu image\n    are in `output/belltower/quality/hall-plaster-final/`. The v9 bake includes the revised hall joinery, timber decks\n    and worn plaster, and completed both lighting passes. It retains the v7 reflections. `daylight-v9-save/` verifies\n    that only the three indirect-light texture paths changed in the saved scene. The source manifest records local\n    geometry, shaders and textures, including the landscape and height maps.',
 '    asset compilation or resident-resource reloads; inspect progress before terminating an editor.':
 '    asset compilation or resident-resource reloads; inspect progress before terminating an editor. A later lobby\n    startup stall in PID 16792 was `BuildNetworkedFiles` / `LargeNetworkFiles.AddFile` hashing multiplayer assets on\n    the main thread. Disk reads kept advancing; it recovered after about seven minutes without a restart. The\n    stack, asset inventory and recovery record are in `startup-recovery/editor-stall-16792*`.'
}
for old,new in replacements.items():
    assert section.count(old)==1,old
    section=section.replace(old,new)
after=(text[:start]+section.replace('\n',newline)+text[end:]).encode('utf-8')
assert path.read_bytes()==before,'CLAUDE.md changed concurrently'
pending=path.with_name(path.name+'.belltower-notes')
pending.write_bytes(after)
os.replace(pending,path)
print('Recorded accepted v9 lighting and editor recovery; other sections preserved.')

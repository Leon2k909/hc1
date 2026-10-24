"""Read-only check of the installed gate surgery and native review evidence."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/'output/belltower/gate-v2/stage'
BASELINE=ROOT/'output/belltower/gate-v1/stage/before'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    manifest=json.loads((STAGE/'manifest.json').read_text())
    report={'revision':'town-gate-v2','native_editor_views':[], 'models':{}}
    for rel,record in manifest['files'].items():
        assert sha(ROOT/rel)==record['after'],rel
    for rel,expected in manifest['sources'].items():
        assert sha(ROOT/rel)==expected,rel
    for name,record in manifest['models'].items():
        rel=f'Assets/models/maps/belltower/{name}'
        old=(BASELINE/(rel+'.obj')).read_bytes().splitlines(keepends=True)
        new=(ROOT/(rel+'.obj')).read_bytes().splitlines(keepends=True)
        cut=next(i for i,line in enumerate(old) if line.startswith(b'usemtl '))
        start=next(i for i,line in enumerate(new) if line.startswith(b'usemtl '))
        drop=set(record['removed_face_lines'])
        assert len(drop)==48 and all(old[i].startswith(b'f ') for i in drop)
        kept=[line for i,line in enumerate(old[cut:],cut) if i not in drop]
        assert new[:cut]==old[:cut]
        assert new[start:start+len(kept)]==kept
        before=(BASELINE/(rel+'.vmdl')).read_bytes()
        after=(ROOT/(rel+'.vmdl')).read_bytes()
        added=[line for line in after.splitlines(keepends=True) if b'belltower_gate_iron' in line]
        assert len(added)==1 and after.replace(added[0],b'',1)==before
        compiled=ROOT/(rel+'.vmdl_c')
        assert compiled.is_file() and compiled.stat().st_size>0
        assert compiled.stat().st_mtime >= (ROOT/(rel+'.obj')).stat().st_mtime
        report['models'][name]={'other_obj_lines_byte_identical':True,'physics_byte_identical':True,
                                'removed_triangles':48,'added_triangles':record['added_triangles'],
                                'compiled_new_mesh':True}
    captures=ROOT/'output/belltower/quality/gate-v2-after'
    for name in ('front','angle','east-front'):
        evidence=json.loads((captures/(name+'-camera.json')).read_text())
        assert all(evidence['Restoration'].values())
        assert evidence['Capture']['ViewportSettledMilliseconds']==5000
        assert evidence['Capture']['SourceSceneSha256']==sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene')
        assert (captures/(name+'.png')).is_file()
        report['native_editor_views'].append((captures/(name+'.png')).relative_to(ROOT).as_posix())
    report.update({'saved_scene_unchanged':True,'new_game_objects':0,'new_colliders':0,
                   'new_materials':1,'native_play_test_performed':False})
    destination=ROOT/'output/belltower/gate-v2/verification.json'
    destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf8')
    print(json.dumps(report,indent=2))


if __name__=='__main__': main()

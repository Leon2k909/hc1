"""Install the scoped phone replacement only when the project editor is closed."""
from pathlib import Path
import json,hashlib,re,sys,subprocess,psutil
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=ROOT/'output/riverdale-emergency-phone-installed-20261031'
sys.path.insert(0,str(ROOT/'Tools'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def atomic(path,data):
    assert path.resolve().is_relative_to(ROOT) or path.resolve().is_relative_to(OUT.resolve())
    incoming=path.with_name(path.name+'.phone-incoming');incoming.write_bytes(data);incoming.replace(path)
    assert path.read_bytes()==data
def insert_group(raw,group):
    text=raw.decode('utf-8');scene=json.loads(text);world=next(o for o in scene['GameObjects'] if o.get('Name')=='Riverdale')
    assert not any(o.get('Name')=='Emergency Phones' for o in world['Children'])
    at=text.index('"Name": "Riverdale"');start=text.index('"Children": [',at)+len('"Children": ')
    depth=0;inside=False;escape=False;end=None
    for i in range(start,len(text)):
        ch=text[i]
        if inside:
            if escape:escape=False
            elif ch=='\\':escape=True
            elif ch=='"':inside=False
        elif ch=='"':inside=True
        elif ch=='[':depth+=1
        elif ch==']':
            depth-=1
            if depth==0:end=i;break
    assert end is not None
    head=text[:end].rstrip();closing=text[len(head):end];newline='\r\n' if '\r\n' in text else '\n'
    indent=re.search(r'\n( *)\{',text[start:end])[1]
    body=json.dumps(group,indent=2).replace('\n',newline+indent)
    updated=head+','+newline+indent+body+closing+text[end:]
    check=json.loads(updated);newworld=next(o for o in check['GameObjects'] if o.get('Name')=='Riverdale')
    assert newworld['Children'].pop()==group and check==scene
    return updated.encode('utf-8')
def main():
    assert not (HERE/'installed.json').exists(),'Already installed'
    assert not [p.pid for p in psutil.process_iter(['name']) if (p.info['name'] or '').lower() in ('sbox-dev.exe','sbox.exe')],'Use native editor installation while an editor is running'
    plan=json.loads((OUT/'plan.json').read_text())
    scene=ROOT/'Assets/scenes/maps/Riverdale/riverdale.scene'
    assert sha(scene)==plan['sceneSHA256'],'Saved scene changed; re-prepare'
    for item in plan['files']:assert sha(ROOT/item['path'])==item['before'],item['path']
    for name,h in plan['proposalSourceSHA256'].items():assert sha(ROOT/name)==h,name
    scene_data=insert_group(scene.read_bytes(),plan['group'])
    # Read each current generator just before patching; preserve other prop upgrades.
    hall=ROOT/'Tools/riverdale_hall.py';mapfile=ROOT/'Tools/riverdale_map.py'
    hall_old=hall.read_bytes();map_old=mapfile.read_bytes();h=hall_old.decode();m=map_old.decode()
    match=re.search(r'(?m)^def wall_phone\( d, fine, face, s, z \):[\s\S]*?(?=^def )',h);assert match
    replacement='def wall_phone( d, fine, face, s, z ):\n    """Approved shared phone, including its collider, authored by the scene group."""\n    import riverdale_emergency_phones as EMERGENCY_PHONES\n    EMERGENCY_PHONES.record( face.p( s, z - 7, 0.0 ), face.out )\n\n\n'
    h=h[:match.start()]+replacement+h[match.end():]
    marker='import riverdale_eyewash as EYEWASHES';assert m.count(marker)==1
    m=m.replace(marker,marker+'\nimport riverdale_emergency_phones as EMERGENCY_PHONES',1)
    marker='    world["Children"].append( EYEWASHES.scene_group( ids ) )';assert m.count(marker)==1
    m=m.replace(marker,marker+'\n    world["Children"].append( EMERGENCY_PHONES.scene_group( ids ) )',1)
    marker='def build():\n    """ Every model by name. """';assert m.count(marker)==1
    m=m.replace(marker,marker+'\n    EMERGENCY_PHONES.PLACED.clear()',1)
    compile(h,str(hall),'exec');compile(m,str(mapfile),'exec')
    for target,data in ((hall,hall_old),(mapfile,map_old)):
        backup=OUT/'before'/target.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True)
        if not backup.exists():backup.write_bytes(data)
    updates=[(ROOT/item['path'],(OUT/'stage'/item['path']).read_bytes()) for item in plan['files']]
    updates += [(scene,scene_data),(hall,h.encode()),(mapfile,m.encode())]
    done=[]
    try:
        assert hall.read_bytes()==hall_old and mapfile.read_bytes()==map_old
        for target,data in updates:
            atomic(target,data);done.append(target)
        result={**plan,'status':'approved-installed-in-saved-map','installedInMap':True,'userApproved':True,'installationRoute':'offline; editor not running',
            'nativeSharedAssetCompilationAndSevenCollisionChecks':'passed before installation',
            'nativePlacedSceneCheck':'pending next editor session','filesAfter':{str(p.relative_to(ROOT)).replace(chr(92),'/'):sha(p) for p,data in updates}}
        for p in (HERE/'installed.json',OUT/'installed.json'):atomic(p,(json.dumps(result,indent=2)+'\n').encode())
    except Exception:
        for target in reversed(done):
            backup=OUT/'before'/target.relative_to(ROOT)
            if backup.exists():atomic(target,backup.read_bytes())
        raise
    print(json.dumps(dict(installed=True,phones=8,removedTriangles=1008,sceneOnlyAddedPhoneGroup=True,editorOpened=False)))
if __name__=='__main__':main()

"""Create the four gunsmith resources and add missing selection points.

Existing bodygroup attachments and player selections are preserved.
"""
import json
from pathlib import Path
import uuid

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / 'Assets'
NAMESPACE = uuid.UUID('a0a6570b-a43b-4c58-bc5c-f7b2e856845d')


def guid(name):
    return str(uuid.uuid5(NAMESPACE, name))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2)+'\n', encoding='utf-8')


specs = [
    ('rifle_suppressor', 'HC1 Rifle Suppressor', 'Barrel', '-0.35,0,0'),
    ('compact_suppressor', 'HC1 Compact Suppressor', 'Barrel', '-0.35,0,0'),
    ('vertical_grip', 'HC1 Vertical Grip', 'Underbarrel', '-9.0,0,-1.3'),
    ('angled_grip', 'HC1 Angled Grip', 'Underbarrel', '-9.0,0,-1.3'),
]
for name, title, category, offset in specs:
    folder=ASSETS/'gunsmith/hc1'/name
    prefab=f'gunsmith/hc1/{name}/{name}.prefab'
    write(folder/f'{name}.prefab', {
        'RootObject': {
            '__guid':guid(name), 'Flags':0, 'Name':title,
            'Position':'0,0,0','Rotation':'0,0,0,1','Scale':'1,1,1',
            'Enabled':True,'NetworkMode':1,
            'Components':[
                {'__type':'Sandbox.ModelRenderer','__guid':guid(name+'/renderer'),'__enabled':True,
                 'Model':f'attachments/hc1/{name}/{name}.vmdl','Tint':'1,1,1,1'},
                {'__type':'Facepunch.Gunsmith.GunsmithSocketAttachment','__guid':guid(name+'/socket'),'__enabled':True,
                 'SocketName':'muzzle','SocketOffset':offset,'SocketAngles':'0,0,0',
                 'ModelSocketAngles':{
                     'weapons/swb/scarh/v_scarh.vmdl':'0,0,180',
                     'weapons/swb/scarh/v_scarh_gunsmith.vmdl':'0,0,180',
                     'weapons/swb/scarh/w_scarh.vmdl':'0,0,180',
                 }},
            ],
        }, 'ResourceVersion':2,'__version':2,
    })
    write(folder/f'{name}.gnsmth', {
        'Name':title,'Category':category,'MainPrefab':prefab,
        'EligibleEquipment':['weapons/m4a1/m4a1.equip','weapons/scarh/scarh.equip'],
        'RequiredLevel':0,'ModifyBodygroups':False,'Bodygroups':{},
        '__references':[],'__version':0,
    })


def walk(node):
    yield node
    for child in node.get('Children',[]):
        yield from walk(child)


for weapon in ['M4A1','ScarH']:
    for kind in ['vm','wm']:
        path=ASSETS/'Weapons'/weapon/f'{kind}_{weapon.lower()}.prefab'
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        root=data['RootObject']
        categories={c.get('Category') for node in walk(root) for c in node.get('Components',[])
                    if c.get('__type')=='Facepunch.Gunsmith.GunsmithAttachmentPoint'}
        changed=False
        for category,position in [('Barrel','18,0,7.4'),('Underbarrel','8.7,0,5.4')]:
            if category in categories:
                continue
            key=f'{weapon}/{kind}/{category}'
            root.setdefault('Children',[]).append({
                '__guid':guid(key),'Flags':0,'Name':f'{category} Attachment Point',
                'Position':position,'Rotation':'0,0,0,1','Scale':'1,1,1','Enabled':True,
                'Components':[{'__type':'Facepunch.Gunsmith.GunsmithAttachmentPoint',
                               '__guid':guid(key+'/component'),'Category':category}],
            })
            changed=True
        if changed:
            write(path,data)
            print('Added sockets:',path.relative_to(ROOT))

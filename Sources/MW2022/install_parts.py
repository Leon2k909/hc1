"""Create deterministic s&box resources for every physical M4 menu entry."""
import json,re,sys,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1];A=ROOT/'Assets'
sys.path.insert(0,str(ROOT/'Tools'))
import part_names
inventory=json.loads((HERE/'inventory.json').read_text())
models={m['source']:m for m in json.loads((HERE/'conversion.json').read_text())['models']}
def guid(s):return str(uuid.uuid5(uuid.NAMESPACE_URL,'hc1/mw2022/'+s))
def vec(v):return ','.join(f'{x:.6f}'for x in v)
def write(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    text=json.dumps(value,indent=2,ensure_ascii=False)+'\n'
    if not path.exists() or path.read_text(encoding='utf8')!=text:path.write_text(text,encoding='utf8')
mounts={'Barrel':(4.32,0,8.6257),'Stock':(-4.05,0,7.4147),'RearGrip':(-1.61,0,5.58),'Magazine':(3.12,0,4.55),'Muzzle':(17.62,0,7.4147),'Optic':(.25,0,8.73),'Underbarrel':(8.3,0,6.2),'Laser':(8.6,-1.22,7.4147),'Launcher':(4.7,0,6.18)}
installed=[]
for entry in inventory['attachments']:
    if not entry['model']:continue
    m=models[entry['model']];key=entry['key'];cat=entry['category'];category='Underbarrel'if cat=='Launcher'else cat
    name=entry['name'].replace('\ufffd','').replace("''",'"').replace('  ',' ')
    if cat=='Muzzle' and name in ('Breacher Device','Flash Guard','Monolithic Suppressor','Lightweight Suppressor'):name+=' '+re.search(r'(\d+)$',key)[1]
    rip_name=name
    name=part_names.name(key,name)  # ours: players never see the rip's CoD names
    bind=mounts[cat]
    choices={}
    for group in m['bodygroups']:
        if group['name']=='lens':choices['lens']=1
        if group['name']=='boolet':choices['boolet']=1
    scale=(.985,1,.987)if cat=='RearGrip'else (1,1,1)
    mount={'__type':'Facepunch.Gunsmith.GunsmithMw22Attachment','__guid':guid(key+'/mount'),'BindPosition':vec(bind),'PartScale':vec(scale),'PartAngles':'0,0,90'if cat=='Laser'else '0,0,0','BoneName':'magazine'if cat=='Magazine'else 'stock'if cat=='Stock'else 'weapon_root','BodygroupChoices':choices,'IsLauncher':cat=='Launcher'}
    if cat=='Barrel':
        bones={b['name']:b['head']for b in m['bones']}
        for field,bone in [('BarrelMuzzle','tag_silencer'),('BarrelFlash','tag_flash_attachment'),('BarrelGrip','tag_grip_attach'),('BarrelLaser','tag_laser_attach')]:
            mount[field]=vec([bind[i]+bones.get(bone,[0,0,0])[i]for i in range(3)])
    if cat=='Laser':
        mount['LaserEmitter']=vec(next(b['head'] for b in m['bones'] if b['name']=='tag_laser'))
        mount['LaserColor']='1,0.025,0.015,1' if key.endswith('03') else '0.08,1,0.12,1'
        mount['LaserWidth']=.025 if key.endswith('03') else .035
    path='gunsmith/m4a1/mw2022/'+key
    write(A/(path+'.prefab'),{'RootObject':{'__guid':guid(key+'/root'),'Name':name,'Enabled':True,'Position':'0,0,0','Rotation':'0,0,0,1','Scale':'1,1,1','Components':[{'__type':'Sandbox.ModelRenderer','__guid':guid(key+'/mesh'),'Model':m['vmdl'],'Tint':'1,1,1,1'},mount]},'ResourceVersion':2,'__version':2})
    part={'Name':name,'Category':category,'MainPrefab':{'_type':'gameobject','prefab':path+'.prefab'},'EligibleEquipment':['weapons/m4a1/m4a1.equip'],'RequiredLevel':0,'Description':'','ModifyBodygroups':False,'Bodygroups':{},'__references':[],'__version':0}
    if cat in ('Barrel','Underbarrel','Launcher','Magazine','Optic'):
        part['ModifyBodygroups']=True
        part['Bodygroups']={'Barrel':{'handguard_covers':1},'Underbarrel':{'foregrip':0},'Launcher':{'foregrip':0},'Magazine':{'magazine':2},'Optic':{'top_rail':3,'gasblock':1}}[cat]
        if cat=='Optic':part['ModelBodygroups']={'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':{'top_rail':1,'gasblock':1}}
        if cat=='Magazine':part['ModelBodygroups']={'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':{'magazine':1}}
        if cat=='Barrel':part['ModelBodygroups']={'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':{'handguard_covers':0}}
    if cat=='Muzzle':part['IsSuppressor']='silencer' in key
    if cat=='Magazine':
        part['MagazineCapacity']=int(re.search(r'(\d+) Round',rip_name)[1])if 'Round' in rip_name else 30
        part['ReloadTimeMultiplier']={15:.9,30:1,45:1.12,60:1.22}[part['MagazineCapacity']]
    if cat=='Optic':
        reticle=next((b['head']for b in m['bones']if b['name']=='tag_reticle_attach'),[0,0,1.3])
        part.update(OverrideAimOffset=True,OpticAimOffset=vec((-4,-reticle[1],10.12-bind[2]-reticle[2])),OpticMagnification=6 if 'scope_'in key else 2 if '2x_'in key and not key.endswith('holo')else 3 if any(s in key for s in ('4x_','hybrid','thermal'))else 1)
        if any(s in key for s in ('thermal','hybrid','scope_vz')):part['Description']='Fixed-magnification optic'
    if cat=='Laser':part['Description']=('Red' if key.endswith('03') else 'Green')+' aiming laser with a visible beam and surface hit dot.'
    if cat=='Launcher':part['Description']='40mm underbarrel launcher'
    write(A/(path+'.gnsmth'),part)
    installed.append(dict(key=key,name=name,category=category,path=path+'.gnsmth',model=m['vmdl']))

# Preserve complete source magazines, but hide the loose reload round in mounted use.
for m in models.values():
    group=next((g for g in m['bodygroups']if g['name']=='boolet'),None)
    if not group:continue
    p=A/m['vmdl'];text=p.read_text()
    if 'name = "boolet"' in text:continue
    bg='{ _class = "BodyGroupList" children = [ { _class = "BodyGroup" name = "boolet" children = [ { _class = "BodyGroupChoice" name = "rounds" meshes = [ "'+group['choices'][0]['mesh']+'" ] }, { _class = "BodyGroupChoice" name = "" meshes = [ "" ] } ] } ] },\n'
    text=text.replace('] } }\n',bg+'] } }\n')
    p.write_text(text)

# Laser has its own persisted slot, alongside the existing eight categories.
for prefix in ('vm','wm'):
    p=A/f'Weapons/M4A1/{prefix}_m4a1.prefab';j=json.loads(p.read_text());r=j['RootObject']
    def all_objects(o):
        yield o
        for c in o.get('Children',[]):yield from all_objects(c)
    if not any(c.get('Category')in (16,'Laser')for o in all_objects(r)for c in o.get('Components',[])if c['__type']=='Facepunch.Gunsmith.GunsmithAttachmentPoint'):
        r.setdefault('Children',[]).append({'__guid':guid(prefix+'/laser-point'),'Name':'Laser Attachment Point','Enabled':True,'Position':'9,-2,9','Rotation':'0,0,0,1','Scale':'1,1,1','Components':[{'__type':'Facepunch.Gunsmith.GunsmithAttachmentPoint','__guid':guid(prefix+'/laser-component'),'Category':'Laser'}]})
        write(p,j)
write(HERE/'installed.json',installed)
print('INSTALLED',len(installed),'physical attachment options')

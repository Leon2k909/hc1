"""Install the M4A1 replacement stock, barrel kit and independent muzzle slots."""
import json, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def guid(label): return str(uuid.uuid5(uuid.NAMESPACE_URL,'razed/m4a1/'+label))
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2)+'\n',encoding='utf8')
for name,title,category in [('precision_stock','Recon Stock','Stock'),('heavy_barrel','Recon Barrel Kit','Barrel')]:
    folder=ROOT/'Assets/gunsmith/m4a1'/name
    component={'__type':'Facepunch.Gunsmith.GunsmithStockAttachment','__guid':guid(name+'/mount'),'StaticMount':'-6.21926,0,7.4147',
        'WorldBodyReplacement':'attachments/m4a1/world_base/world_base.vmdl'} if category=='Stock' else {
        '__type':'Facepunch.Gunsmith.GunsmithSocketAttachment','__guid':guid(name+'/mount'),
        'SocketName':'muzzle','SocketOffset':'0,0,0','SocketAngles':'0,0,0',
        'ModelSocketOffsets':{'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':'-2.38281,0,0.20177'},
        'ModelVariants':{'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':'attachments/m4a1/heavy_barrel/heavy_barrel_world.vmdl'},
        'ModelScaleMultipliers':{'models/weapons/sbox_assault_m4a1/w_m4a1.vmdl':'1,1.32,1'}}
    prefab={'RootObject':{'__guid':guid(name+'/root'),'Flags':0,'Name':title,'Position':'0,0,0','Rotation':'0,0,0,1','Scale':'1,1,1','Enabled':True,'NetworkMode':1,
        'Components':[{'__type':'Sandbox.ModelRenderer','__guid':guid(name+'/renderer'),'Model':f'attachments/m4a1/{name}/{name}.vmdl','Tint':'1,1,1,1'},component]},'ResourceVersion':2,'__version':2}
    write(folder/f'{name}.prefab',prefab)
    write(folder/f'{name}.gnsmth',{'Name':title,'Category':category,'MainPrefab':{'_type':'gameobject','prefab':f'gunsmith/m4a1/{name}/{name}.prefab'},
        'EligibleEquipment':['weapons/m4a1/m4a1.equip'],'RequiredLevel':0,
        'ModifyBodygroups':category=='Barrel','Bodygroups':{'gasblock':1,'handguard_covers':0} if category=='Barrel' else {},
        'HiddenWeaponMaterials':['models/weapons/sbox_assault_m4a1/v_m4a1_handguard.vmat' if category=='Barrel' else 'models/weapons/sbox_assault_m4a1/v_m4a1_stock.vmat'],
        '__references':[],'__version':0})

for name,title in [('compact_suppressor','Compact Suppressor'),('rifle_suppressor','Rifle Suppressor')]:
    # Reuse the established mounts but keep M4 finish assets independent of HC1.
    prefab=json.loads((ROOT/f'Assets/gunsmith/hc1/{name}/{name}.prefab').read_text(encoding='utf8'))
    prefab['RootObject']['Name']='M4A1 '+title
    prefab['RootObject']['__guid']=guid(name+'/root')
    for index,component in enumerate(prefab['RootObject']['Components']):
        component['__guid']=guid(name+f'/component/{index}')
        if component['__type']=='Sandbox.ModelRenderer':component['Model']=f'attachments/m4a1/{name}/{name}.vmdl'
    write(ROOT/f'Assets/gunsmith/m4a1/muzzle/{name}.prefab',prefab)
    write(ROOT/f'Assets/gunsmith/m4a1/muzzle/{name}.gnsmth',{
        'Name':title,'Category':'Muzzle','IsSuppressor':True,
        'MainPrefab':{'_type':'gameobject','prefab':f'gunsmith/m4a1/muzzle/{name}.prefab'},
        'EligibleEquipment':['weapons/m4a1/m4a1.equip'],'RequiredLevel':0,'__references':[],'__version':0})

def walk(go):
    yield go
    for child in go.get('Children',[]): yield from walk(child)
for variant in ['vm','wm']:
    path=ROOT/f'Assets/Weapons/m4a1/{variant}_m4a1.prefab'
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    root=data['RootObject']
    for category,position in [('Stock','-9.5,0,6.5'),('Muzzle','18.6,0,5.8')]:
        if not any(c.get('__type')=='Facepunch.Gunsmith.GunsmithAttachmentPoint' and c.get('Category')==category for go in walk(root) for c in go.get('Components',[])):
            key=category.lower()
            root.setdefault('Children',[]).append({'__guid':guid(variant+f'/{key}_point'),'Flags':0,'Name':category+' Attachment Point',
                'Position':position,'Rotation':'0,0,0,1','Scale':'1,1,1','Enabled':True,
                'Components':[{'__type':'Facepunch.Gunsmith.GunsmithAttachmentPoint','__guid':guid(variant+f'/{key}_component'),'Category':category}]})
    for go in walk(root):
        if any(c.get('__type')=='Facepunch.Gunsmith.GunsmithAttachmentPoint' and c.get('Category')=='Barrel' for c in go.get('Components',[])):
            go['Position']='8.5,0,10.3'
    write(path,data)

path=ROOT/'Assets/Weapons/M4A1/weapon_m4a1.prefab'
data=json.loads(path.read_text(encoding='utf-8-sig'))
for go in walk(data['RootObject']):
    for c in go.get('Components',[]):
        if c.get('__type')=='Facepunch.Shootable':
            c['SuppressedShootSound']='sounds/swb/attachments/silencer/swb_rifle.silenced.fire.sound'
            c['SuppressedMuzzleFlashChance']=0
write(path,data)
print('M4A1 stock, barrel kit and independent suppressor slots installed')

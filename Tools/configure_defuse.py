"""Wire the original device into held, dropped, mounted and planted presentation."""
from pathlib import Path
import json, uuid
ROOT=Path(__file__).resolve().parents[1]
MODEL='weapons/c4/field_device_v2/field_device.vmdl'
def guid(): return str(uuid.uuid4())
def read(path): return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def save(path,data): (ROOT/path).write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')
def walk(o):
    yield o
    for child in o.get('Children',[]): yield from walk(child)

for filename in ['weapon_c4.prefab','mount_c4.prefab','planted_c4.prefab']:
    path='Assets/Weapons/C4/'+filename; data=read(path)
    for o in walk(data['RootObject']):
        for c in o.get('Components',[]):
            if c['__type'] in ('Sandbox.SkinnedModelRenderer', 'Sandbox.ModelRenderer'):
                c['Model']=MODEL;c['MaterialOverride']=None;c['UseAnimGraph']=False
            if c['__type']=='DefuseC4': c['PlantTime']=4.0
            if c['__type']=='TimedExplosive': c['BaseDefuseTime']=7.5;c['FastDefuseTime']=7.5
    save(path,data)

path='Assets/Weapons/C4/c4.equip';data=read(path)
data['WorldModel']=MODEL;data['Icon']='ui/items/field_device.svg';data['Description']='Carry to site A or B. Hold fire to arm the device.'
save(path,data)

path='Assets/Weapons/C4/vm_c4.prefab';data=read(path);root=data['RootObject']
vm=next(c for c in root['Components'] if c['__type']=='Facepunch.ViewModel')
renderer=next((c for c in root['Components'] if c['__type']=='Sandbox.SkinnedModelRenderer'),None)
if renderer:
    root['Components'].remove(renderer)
    device={'__guid':guid(),'Name':'Field Device','Enabled':True,'NetworkMode':0,'Components':[renderer]}
    root['Children'].append(device)
else: device=next(o for o in root['Children'] if o['Name']=='Field Device');renderer=device['Components'][0]
renderer['Model']=MODEL;renderer['MaterialOverride']=None;renderer['UseAnimGraph']=False
renderer['RenderOptions']={'GameLayer':False,'OverlayLayer':True,'BloomLayer':False,'AfterUILayer':False}
vm['ModelRenderer']['go']=device['__guid'];vm['MoveBobScale']=.35;vm['YawInertiaScale']=.6
armsObject=next(o for o in root['Children'] if o!=device)
arms=next(c for c in armsObject['Components'] if c['__type']=='Sandbox.SkinnedModelRenderer')
arms['BoneMergeTarget']=None;arms['UseAnimGraph']=False;arms['RenderOptions']=renderer['RenderOptions'];arms['RenderType']='Off'
root['Components']=[c for c in root['Components'] if c['__type']!='Facepunch.DefuseViewModel']
root['Components'].append({'__type':'Facepunch.DefuseViewModel','__guid':guid(),'Device':vm['ModelRenderer'],'Arms':vm['Arms']})
save(path,data)

# Loadout rounds, no purchase phase; score a defending win when attackers run out of time.
path='Assets/prefabs/game_modes/bomb_defusal.prefab';data=read(path)
objects=list(walk(data['RootObject']))
ctWin=next(o for o in objects if o['Name']=='Ts Eliminated')
ctState=next(c for c in ctWin['Components'] if c['__type']=='Sandbox.Events.StateComponent')
for o in objects:
    for c in o.get('Components',[]):
        if c['__type']=='Facepunch.GameMode': c['Description']='One life per round. Arm the device at A or B, or defend the sites and disarm it. First to six rounds wins.'
        if c['__type']=='Facepunch.DefaultEquipment': c['LoadoutsEnabled']=True
        if c['__type']=='Facepunch.EnableBuyMenu': c['__enabled']=False
        if c['__type']=='Facepunch.RoundLimit': c['MaxRounds']=12
        if c['__type']=='Facepunch.TeamEarlyWinCondition': c['TargetScore']=6
        if c['__type']=='Facepunch.RespawnPlayers': c['ForceNew']=True
        if c['__type']=='Facepunch.ShowStatusIcon': c['IconPath']='/ui/items/field_device.svg'
        if o['Name']=='Before Plant' and c['__type']=='Sandbox.Events.StateComponent':
            c['DefaultNextState']={'_type':'component','component_id':ctState['__guid'],'go':ctWin['__guid'],'component_type':'StateComponent'}
save(path,data)
print('Defuse and C4 prefabs configured')

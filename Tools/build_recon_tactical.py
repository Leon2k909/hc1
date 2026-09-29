"""Build the hand-launch variant and equipment prefabs from the existing recon aircraft."""
import json
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'Assets'
DEST = ASSETS / 'weapons/recon_drone'
DEST.mkdir(parents=True, exist_ok=True)
BASE = 'weapons/recon_drone'
MODEL = 'models/recon_drone'

def guid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'razed/recon-tactical/' + name))

def ref(name, kind, go):
    return {'_type': 'component', 'component_id': guid(name), 'go': guid(go), 'component_type': kind}

def component(name, kind, **props):
    return {'__type': kind, '__guid': guid(name), '__enabled': True, **props}

def obj(name, components=None, children=None, **props):
    return {'__guid': guid(name), 'Name': name, 'Enabled': True, 'NetworkMode': 0,
            'Components': components or [], 'Children': children or [], **props}

def prefab(name, root):
    (DEST / (name + '.prefab')).write_text(json.dumps({'RootObject': root, 'ResourceVersion': 2,
        '__references': [], '__version': 2}, indent=2) + '\n')

def renderer(name, model, overlay=False, skinned=False):
    return component(name, 'Sandbox.SkinnedModelRenderer' if skinned else 'Sandbox.ModelRenderer',
        Model=f'{MODEL}/{model}.vmdl', Tint='1,1,1,1', RenderType='Off' if overlay else 'On',
        RenderOptions={'GameLayer': not overlay, 'OverlayLayer': overlay}, UseAnimGraph=False)

# Same aircraft at a portable 49 cm wingspan, with matching held and deployed geometry.
for name in ('recon_drone', 'recon_propeller'):
    source = (ASSETS / MODEL / f'{name}.vmdl').read_text()
    (ASSETS / MODEL / f'{name}_handheld.vmdl').write_text(source.replace('import_scale = 1', 'import_scale = 0.09'))

def propeller(name, overlay=False):
    return obj(name, [renderer(name + '-renderer', 'recon_propeller_handheld', overlay)], Position='-5.94,0,0.54')

flight = obj('Recon Drone Airborne', [
    renderer('flight-renderer', 'recon_drone_handheld'),
    component('flight', 'Facepunch.ReconDroneFlight', FlightDuration=30, ScanRange=1600,
        Propeller={'_type': 'gameobject', 'go': guid('flight-propeller')})
], [propeller('flight-propeller')], NetworkMode=2, NetworkInterpolation=True, Tags='recon_drone')
prefab('recon_drone_airborne', flight)

wm = obj('Recon Drone World Model', [
    renderer('world-renderer', 'recon_drone_handheld', skinned=True),
    component('world', 'Facepunch.WorldModel', ModelRenderer=ref('world-renderer', 'SkinnedModelRenderer', 'Recon Drone World Model'))
], [propeller('world-propeller')], Position='2,0,2', Rotation='0,0,0,1')
prefab('wm_recon_drone', wm)

# Retain the proven throwable hand animation, without copying cached skeleton objects.
vm = json.loads((ASSETS / 'weapons/Throwable/M18_Smoke_Grenade/vm_smoke_grenade.prefab').read_text())['RootObject']
vm['Name'] = 'Recon Drone View Model'
vm['Children'] = vm['Children'][:1]
vm['Children'][0]['Name'] = 'Handheld recon drone'
vm['Children'][0]['Components'][0]['Model'] = f'{MODEL}/recon_drone_handheld.vmdl'
vm['Children'][0]['Children'] = [propeller('held-propeller', True)]
for c in vm['Components']:
    if c['__type'] == 'Facepunch.ThrowableViewModelGrip':
        c['ItemCenterHeight'] = -1.0
        c['ItemOffset'] = '1,0,0'
    if c['__type'] == 'Facepunch.ViewModel':
        c['MoveBobScale'] = 0.45
        c['YawInertiaScale'] = 0.7
# Remap all copied object/component identifiers consistently, including references.
text = json.dumps(vm)
def ids(node):
    if isinstance(node, dict):
        if '__guid' in node: yield node['__guid']
        for value in node.values(): yield from ids(value)
    elif isinstance(node, list):
        for value in node: yield from ids(value)
for old in set(ids(vm)):
    text = text.replace(old, guid('vm-' + old))
prefab('vm_recon_drone', json.loads(text))

prefab('weapon_recon_drone', obj('Recon Drone Equipment', [
    component('equipment', 'Facepunch.Equipment', Resource=f'{BASE}/recon_drone.equip',
        HoldType='HoldItem', Handedness='Right', UseCrosshair=True,
        DeploySound='sounds/guns/switch/weapon_switch.sound'),
    component('tags', 'Facepunch.TagBinder')
], [obj('Recon Drone Throw', [component('throw', 'Facepunch.ReconDroneThrowable',
    InputActions=['Attack1'], CookTime=0.2, ThrowPower=650,
    Prefab={'_type':'gameobject', 'prefab':f'{BASE}/recon_drone_airborne.prefab'})])]))

resource = {'Name':'Recon Drone', 'Description':'Hand-launch a camera drone that climbs and circles above the launch area. Spots visible nearby enemies for 30 seconds.',
    'Slot':'Tactical', 'Category':'None', 'Team':'Unassigned', 'CanOtherTeamPickUp':True,
    'DropOnDisconnect':False, 'Icon':'ui/weapons/recon_drone.svg', 'IsPurchasable':True,
    'Price':500, 'KillReward':0, 'WorldModel':f'{MODEL}/recon_drone_handheld.vmdl', '__version':0, '__references':[]}
for key, name in [('MainPrefab','weapon_recon_drone'),('ViewModelPrefab','vm_recon_drone'),('WorldModelPrefab','wm_recon_drone')]:
    resource[key] = {'_type':'gameobject', 'prefab':f'{BASE}/{name}.prefab'}
(DEST / 'recon_drone.equip').write_text(json.dumps(resource, indent=2) + '\n')

(ASSETS / 'ui/weapons/recon_drone.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 240 160">
<g fill="white"><path d="M116 14Q120 3 124 14L130 62 225 91 225 103 130 83 127 120 123 128 117 128 113 120 110 83 15 103 15 91 110 62Z"/>
<path d="M78 80H83V137L111 132V141L73 147 68 135 75 128Z M157 80H162L165 128 172 135 167 147 129 141V132L157 137Z"/>
<rect x="104" y="119" width="32" height="4" rx="2"/></g></svg>\n''')
print('Built handheld recon models, icon, equipment resource and four prefabs.')

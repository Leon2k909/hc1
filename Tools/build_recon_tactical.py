"""Build the hand-launched Recon Drone's equipment prefabs on the recon aircraft (Tools/build_recon_drone.py).

The drone is the real aircraft at its real size (a Raven-class hand-launched UAS, 1.37 m across), the same model the
UAV streak reward flies. It's held under the wing by the pod's belly, as one is held to launch.
"""
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

# The prop model's origin is its hub, which asset-info.json gives in the drone's own space (inches).
HUB = json.loads((ASSETS / MODEL / 'asset-info.json').read_text())['prop_hub_inches']
# Where the hand holds it: the pod's belly under the wing, 3.9 forward of the origin and 2.3 below it.
GRIP = (3.9, 0.0, -2.3)

def num(v):
    return f'{v + 0.0:g}'  # + 0.0 writes -0 as 0

def propeller(name, overlay=False):
    return obj(name, [renderer(name + '-renderer', 'recon_propeller', overlay)],
               Position=','.join(num(c) for c in HUB))

flight = obj('Recon Drone Airborne', [
    renderer('flight-renderer', 'recon_drone'),
    component('flight', 'Facepunch.ReconDroneFlight', FlightDuration=30, ScanRange=1600,
        Propeller={'_type': 'gameobject', 'go': guid('flight-propeller')})
], [propeller('flight-propeller')], NetworkMode=2, NetworkInterpolation=True, Tags='recon_drone')
prefab('recon_drone_airborne', flight)

wm = obj('Recon Drone World Model', [
    renderer('world-renderer', 'recon_drone', skinned=True),
    component('world', 'Facepunch.WorldModel', ModelRenderer=ref('world-renderer', 'SkinnedModelRenderer', 'Recon Drone World Model'))
], [propeller('world-propeller')], Position=','.join(num(-c) for c in GRIP), Rotation='0,0,0,1')
prefab('wm_recon_drone', wm)

# Retain the proven throwable hand animation, without copying cached skeleton objects.
vm = json.loads((ASSETS / 'weapons/Throwable/M18_Smoke_Grenade/vm_smoke_grenade.prefab').read_text())['RootObject']
vm['Name'] = 'Recon Drone View Model'
vm['Children'] = vm['Children'][:1]
vm['Children'][0]['Name'] = 'Handheld recon drone'
vm['Children'][0]['Components'][0]['Model'] = f'{MODEL}/recon_drone.vmdl'
vm['Children'][0]['Children'] = [propeller('held-propeller', True)]
for c in vm['Components']:
    if c['__type'] == 'Facepunch.ThrowableViewModelGrip':
        # The grip puts the item's origin at centre - up * ItemCenterHeight + ItemOffset (in the hand's frame), so
        # these put GRIP on the hand.
        c['ItemCenterHeight'] = GRIP[2]
        c['ItemOffset'] = f'{num(-GRIP[0])},{num(-GRIP[1])},0'
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
        DeploySound='sounds/guns/handling/draw_grenade.sound'),
    component('tags', 'Facepunch.TagBinder')
], [obj('Recon Drone Throw', [component('throw', 'Facepunch.ReconDroneThrowable',
    InputActions=['Attack1'], CookTime=0.2, ThrowPower=650,
    Prefab={'_type':'gameobject', 'prefab':f'{BASE}/recon_drone_airborne.prefab'})])]))

resource = {'Name':'Recon Drone', 'Description':'Hand-launch a camera drone that climbs and circles above the launch area. Spots visible nearby enemies for 30 seconds.',
    'Slot':'Tactical', 'Category':'None', 'Team':'Unassigned', 'CanOtherTeamPickUp':True,
    'DropOnDisconnect':False, 'Icon':'ui/weapons/recon_drone.svg', 'IsPurchasable':True,
    'Price':500, 'KillReward':0, 'WorldModel':f'{MODEL}/recon_drone.vmdl', '__version':0, '__references':[]}
for key, name in [('MainPrefab','weapon_recon_drone'),('ViewModelPrefab','vm_recon_drone'),('WorldModelPrefab','wm_recon_drone')]:
    resource[key] = {'_type':'gameobject', 'prefab':f'{BASE}/{name}.prefab'}
(DEST / 'recon_drone.equip').write_text(json.dumps(resource, indent=2) + '\n')

# The icon is the aircraft from above, nose up, to scale (153 px a metre): the pod, the straight wing with rounded
# tips, the pusher prop behind the wing, the boom and the tailplane. The viewBox frames it at about 40 % of the
# canvas, as the grenades' pictures are (the gunsmith draws equipment icons in a square twice their box).
(ASSETS / 'ui/weapons/recon_drone.svg').write_text('''<svg xmlns="http://www.w3.org/2000/svg" viewBox="-142.5 -187.5 525 525">
<g fill="white"><path d="M22 46H218Q225 46 225 52V63Q225 69 219 69L133 73.5H107L21 69Q15 69 15 63V52Q15 46 22 46Z"/>
<path d="M113.5 26Q113.5 10 120 10Q126.5 10 126.5 26V72Q126.5 77 122 79H118Q113.5 77 113.5 72Z"/>
<path d="M118.2 76H121.8L121.3 146H118.7Z"/>
<path d="M95 133H145Q147 133 147 136V144Q147 147 144 147H96Q93 147 93 144V136Q93 133 95 133Z"/>
<rect x="109" y="75.5" width="22" height="2.5" rx="1.2"/></g></svg>
''')
print("Built the recon drone's icon, equipment resource and four prefabs.")

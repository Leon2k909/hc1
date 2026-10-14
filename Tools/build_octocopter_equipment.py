"""Build the Recon Octocopter's equipment on the models Tools/build_recon_octocopter.py makes.

Writes to Assets/weapons/recon_octocopter/:
  - recon_octocopter_airborne.prefab: the aircraft (ReconOctocopter), its gimbal camera, its eight rotors (ReconRotor:
    the hub, the blades, and the disc they blur into) and its colliders;
  - vm_recon_octocopter.prefab: the ground station in both hands (TabletViewModel), on vm_c4's arms;
  - wm_recon_octocopter.prefab: the station in third person, the right hand on its right grip and the left hand's IK on
    its left one;
  - weapon_recon_octocopter.prefab: the Equipment, and the trigger that launches or links (ReconTabletLink);
  - recon_octocopter.equip, and the icon ui/weapons/recon_octocopter.svg (also the radar's).

Every guid is a uuid5 of a fixed name, so a rerun writes the same files. Positions are inches, from the models'
asset-info.json.
"""
import json
import math
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'Assets'
DEST = ASSETS / 'weapons/recon_octocopter'
DEST.mkdir(parents=True, exist_ok=True)
BASE = 'weapons/recon_octocopter'
MODEL = 'models/recon_octocopter'
INFO = json.loads((ASSETS / MODEL / 'asset-info.json').read_text(encoding='utf-8'))


def guid(name):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, 'razed/recon-octocopter/' + name))


def ref(name, kind, go):
    return {'_type': 'component', 'component_id': guid(name), 'go': guid(go), 'component_type': kind}


def component(name, kind, **props):
    return {'__type': kind, '__guid': guid(name), '__enabled': True, **props}


def obj(name, components=None, children=None, **props):
    return {'__guid': guid(name), 'Name': name, 'Enabled': True, 'NetworkMode': 0,
            'Components': components or [], 'Children': children or [], **props}


def prefab(name, root):
    (DEST / (name + '.prefab')).write_text(json.dumps({'RootObject': root, 'ResourceVersion': 2,
        '__references': [], '__version': 2}, indent=2) + '\n', encoding='utf-8')


def num(v):
    return f'{round(v, 4) + 0.0:g}'  # + 0.0 writes -0 as 0


def vec(v):
    return ','.join(num(c) for c in v)


def renderer(name, model, overlay=False, skinned=False, shadows=True):
    props = dict(Model=f'{MODEL}/{model}.vmdl', Tint='1,1,1,1', RenderType='Off' if overlay or not shadows else 'On',
                 RenderOptions={'GameLayer': not overlay, 'OverlayLayer': overlay}, UseAnimGraph=False)
    return component(name, 'Sandbox.SkinnedModelRenderer' if skinned else 'Sandbox.ModelRenderer', **props)


def box(name, centre, size):
    return component(name, 'Sandbox.BoxCollider', Center=vec(centre), Scale=vec(size), IsTrigger=False,
                     Static=False, Surface='surfaces/metal.sheet.surface')


# ---- The aircraft ------------------------------------------------------------------------------------------------

def rotor(index, hub):
    """A rotor at its hub: the hub always, the blades below the blur speed, the disc above it (ReconRotor turns them
    and tells the disc's shader how the prop lies and turns)."""
    name = f'Rotor {index + 1}'
    spin = hub['spin']
    blades = 'recon_octocopter_prop_ccw' if spin > 0 else 'recon_octocopter_prop_cw'
    # The discs cast no shadow: a spinning rotor's shadow is a faint blur, and eight of them are costly for nothing.
    return obj(name, [
        component(name + '-rotor', 'Facepunch.ReconRotor', Spin=spin,
                  Hub=ref(name + '-hub', 'ModelRenderer', name + ' Hub'),
                  Blades=ref(name + '-blades', 'ModelRenderer', name + ' Blades'),
                  Disc=ref(name + '-disc', 'ModelRenderer', name + ' Disc')),
    ], [
        obj(name + ' Hub', [renderer(name + '-hub', 'recon_octocopter_hub')]),
        obj(name + ' Blades', [renderer(name + '-blades', blades)]),
        obj(name + ' Disc', [renderer(name + '-disc', 'recon_octocopter_disc', shadows=False)]),
    ], Position=vec(hub['position']))


hull_c = INFO['hull_centre']
hull_h = INFO['hull_half_extents']
skid = INFO['skid_bottom']
rotor_r = INFO['rotor_radius']
colliders = [
    # The fuselage.
    box('collider-body', hull_c, [2 * h for h in hull_h]),
    # The landing gear and the gimbal under the nose, from the skids to the fuselage.
    box('collider-gear', (0.0, 0.0, (skid + hull_c[2] - hull_h[2]) / 2), (16.0, 26.0, hull_c[2] - hull_h[2] - skid)),
]
# Each coaxial pair of rotors and its arm's end: a square round the discs, 7 high to take both props.
seen = set()
for hub in INFO['hubs']:
    x, y, _ = hub['position']
    if (x, y) in seen:
        continue
    seen.add((x, y))
    colliders.append(box(f'collider-rotor-{len(seen)}', (x, y, 0.0), (2 * rotor_r, 2 * rotor_r, 7.0)))

airborne = obj('Recon Octocopter', [
    renderer('airframe', 'recon_octocopter'),
    component('octocopter', 'Facepunch.ReconOctocopter',
              Gimbal={'_type': 'gameobject', 'go': guid('Gimbal')},
              RotorSound='sounds/drones/octocopter_rotors.sound',
              SparksPrefab='prefabs/impact_fx/impact_sparks.prefab',
              LensOffset=vec(INFO['gimbal_lens'])),
    *colliders,
], [
    obj('Gimbal', [renderer('gimbal', 'recon_octocopter_gimbal')], Position=vec(INFO['gimbal_pivot'])),
    *[rotor(i, hub) for i, hub in enumerate(INFO['hubs'])],
], NetworkMode=2, NetworkInterpolation=True, Tags='recon_octocopter')
prefab('recon_octocopter_airborne', airborne)

# ---- The ground station, in first person -------------------------------------------------------------------------

vm = json.loads((ASSETS / 'weapons/C4/vm_c4.prefab').read_text(encoding='utf-8-sig'))['RootObject']
vm['Name'] = 'Recon Octocopter View Model'
for child in vm['Children']:
    if child['Name'] == 'Field Device':
        child['Name'] = 'Ground Station'
        child['Components'][0]['Model'] = f'{MODEL}/recon_tablet.vmdl'
for c in vm['Components']:
    if c['__type'] == 'Facepunch.DefuseViewModel':
        c['__type'] = 'Facepunch.TabletViewModel'
        c['__enabled'] = True
    if c['__type'] == 'Facepunch.ViewModel':
        c['MoveBobScale'] = 0.3
        c['YawInertiaScale'] = 0.5
text = json.dumps(vm)


def ids(node):
    if isinstance(node, dict):
        if '__guid' in node:
            yield node['__guid']
        for value in node.values():
            yield from ids(value)
    elif isinstance(node, list):
        for value in node:
            yield from ids(value)


# Fresh identifiers, references included, so the copy never shares one with vm_c4.
for old in set(ids(vm)):
    text = text.replace(old, guid('vm-' + old))
prefab('vm_recon_octocopter', json.loads(text))

# ---- The ground station, in third person -------------------------------------------------------------------------

# The hold frame is the hand's: +X forward from the fist, Z up. The station's screen faces its -X, towards the holder,
# so it's held as it's read: the right hand on the right grip, tipped back 30 degrees.
TILT = 30.0
s, c = math.sin(math.radians(TILT / 2)), math.cos(math.radians(TILT / 2))
rot = (0.0, s, 0.0, c)


def rotate_pitch(v, deg):
    a = math.radians(deg)
    x, y, z = v
    return (x * math.cos(a) + z * math.sin(a), y, -x * math.sin(a) + z * math.cos(a))


grip_r = INFO['tablet']['grip_right']
grip_l = INFO['tablet']['grip_left']
origin = tuple(-v for v in rotate_pitch(grip_r, TILT))
wm = obj('Recon Octocopter World Model', [
    renderer('world', 'recon_tablet', skinned=True),
    component('world-model', 'Facepunch.WorldModel',
              UseTabletPose=True,
              ModelRenderer=ref('world', 'SkinnedModelRenderer', 'Recon Octocopter World Model'),
              IkLeftHand={'_type': 'gameobject', 'go': guid('Left hand grip')}),
], [obj('Left hand grip', Position=vec(grip_l))], Position=vec(origin), Rotation=vec(rot))
prefab('wm_recon_octocopter', wm)

# ---- The equipment -----------------------------------------------------------------------------------------------

prefab('weapon_recon_octocopter', obj('Recon Octocopter Equipment', [
    component('equipment', 'Facepunch.Equipment', Resource=f'{BASE}/recon_octocopter.equip',
              HoldType='HoldItem', Handedness='Right', UseCrosshair=False,
              DeploySound='sounds/guns/handling/draw_grenade.sound'),
    component('tags', 'Facepunch.TagBinder'),
], [obj('Ground Station Link', [component('link', 'Facepunch.ReconTabletLink', InputActions=['Attack1'],
                                          LaunchDistance=70,
                                          Prefab={'_type': 'gameobject',
                                                  'prefab': f'{BASE}/recon_octocopter_airborne.prefab'})])]))

resource = {
    'Name': 'Recon Octocopter',
    'Description': 'Fly a camera drone from a tablet: a long zoom, and enemies in its picture are marked for your team.',
    'Slot': 'Tactical', 'Category': 'None', 'Team': 'Unassigned', 'CanOtherTeamPickUp': False,
    'DropOnDisconnect': False, 'Icon': 'ui/weapons/recon_octocopter.svg', 'IsPurchasable': True,
    'Price': 750, 'KillReward': 0, 'WorldModel': f'{MODEL}/recon_tablet.vmdl', '__version': 0, '__references': []}
for key, name in [('MainPrefab', 'weapon_recon_octocopter'), ('ViewModelPrefab', 'vm_recon_octocopter'),
                  ('WorldModelPrefab', 'wm_recon_octocopter')]:
    resource[key] = {'_type': 'gameobject', 'prefab': f'{BASE}/{name}.prefab'}
(DEST / 'recon_octocopter.equip').write_text(json.dumps(resource, indent=2) + '\n', encoding='utf-8')

# ---- The icon ----------------------------------------------------------------------------------------------------

# The aircraft from above, nose up, to scale (3 px an inch): the fuselage, four arms on the diagonals, each arm's end
# a coaxial pair of rotors drawn as its disc's rim. The viewBox frames it at about
# 40 % of the canvas, as the other equipment pictures are (the gunsmith draws them in a square twice their box).
S = 3.0


def svg_xy(x, y):
    # Drone +X (nose) is up the picture, +Y (left) is left.
    return (-y * S, -x * S)


hubs = sorted({(h['position'][0], h['position'][1]) for h in INFO['hubs']})
parts = []
for hx, hy in hubs:
    ax, ay = svg_xy(hx, hy)
    parts.append(f'<line x1="0" y1="0" x2="{num(ax)}" y2="{num(ay)}" stroke="white" stroke-width="9" stroke-linecap="round"/>')
    parts.append(f'<circle cx="{num(ax)}" cy="{num(ay)}" r="{num(rotor_r * S - 3)}" fill="none" stroke="white" stroke-width="6"/>')
    parts.append(f'<circle cx="{num(ax)}" cy="{num(ay)}" r="9" fill="white"/>')
bx, by = svg_xy(hull_c[0], hull_c[1])
bw, bh = 2 * hull_h[1] * S, 2 * hull_h[0] * S
parts.append(f'<rect x="{num(bx - bw / 2)}" y="{num(by - bh / 2)}" width="{num(bw)}" height="{num(bh)}" rx="14" fill="white"/>')
half = (max(abs(v) for xy in hubs for v in xy) + rotor_r) * S / 0.4  # the drawing is 40 % of the canvas
(ASSETS / 'ui/weapons/recon_octocopter.svg').write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{num(-half)} {num(-half)} {num(2 * half)} {num(2 * half)}">\n'
    + '\n'.join(parts) + '\n</svg>\n', encoding='utf-8')

print("Built the recon octocopter's icon, equipment resource and four prefabs.")

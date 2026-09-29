"""Configure the third-person carried device separately from its first-person rig."""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1] / 'Assets/Weapons/C4'
def read(name): return json.loads((root / name).read_text(encoding='utf-8-sig'))
def save(name, data): (root / name).write_text(json.dumps(data, indent=2) + '\n', encoding='utf-8')
weapon = read('weapon_c4.prefab')
obj = weapon['RootObject']
model = next((x for x in obj['Children'] if x['Name'] == 'Model'), None)
if model:
    obj['Children'].remove(model)
    renderer = model['Components'][0]
else:
    renderer = read('wm_c4.prefab')['RootObject']['Components'][0]
equip = next(c for c in obj['Components'] if c['__type'] == 'Facepunch.Equipment')
equip.pop('ModelRenderer', None)
obj['__properties']['Metadata']['WorldModel'] = 'weapons/c4/field_device/field_device.vmdl'
save('weapon_c4.prefab', weapon)
go = 'f6543942-f5aa-4a9e-8f81-bec8647ac704'
hand = '287b5d1d-bf2b-4eaf-a990-647f83d97401'
renderer['__guid'] = 'df5afce8-010b-4c76-a2ec-7c04ca063510'
world = {'RootObject': {
    '__guid': go, 'Name': 'wm_c4', 'Enabled': True, 'Position': '3,5,-1',
    'Components': [renderer, {
        '__type': 'Facepunch.WorldModel', '__guid': '4d056eae-0efc-48c7-a28c-be72d2760080',
        'ModelRenderer': {'_type': 'component', 'component_id': renderer['__guid'], 'go': go, 'component_type': 'SkinnedModelRenderer'},
        'IkLeftHand': {'_type': 'gameobject', 'go': hand}
    }],
    'Children': [{'__guid': hand, 'Name': 'Left hand grip', 'Enabled': True, 'Position': '-3,5,1'}]
}, 'ResourceVersion': 1, '__references': [], '__version': 1}
save('wm_c4.prefab', world)
resource = read('c4.equip')
resource['WorldModelPrefab'] = {'_type': 'gameobject', 'prefab': 'weapons/c4/wm_c4.prefab'}
save('c4.equip', resource)
save('c4_beep_light.prefab', {
    'RootObject': {
        '__guid': '496769ed-228f-4e30-ac66-3026d9faef10', 'Name': 'Device status pulse',
        'Enabled': True, 'NetworkMode': 2,
        'Components': [
            {'__type': 'Sandbox.PointLight', '__guid': '434fbe56-6140-4023-9118-8c9d96f06db1',
             'LightColor': '1,0.16,0.015,1', 'Radius': 28, 'Shadows': False, 'FogMode': 'Disabled'},
            {'__type': 'Facepunch.DestroyAfter', '__guid': '0e37cd8a-ed00-4736-8464-022de107157e', 'Time': .12}
        ]
    }, 'ResourceVersion': 1, '__references': [], '__version': 1
})
print('Carried third-person device configured')

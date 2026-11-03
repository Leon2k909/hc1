"""Two automatic middle-door assemblies, based on Collider's serialized door."""
from pathlib import Path
import copy,json,uuid
ROOT=Path(__file__).resolve().parents[1]
TEMPLATE=ROOT/'Sources/Ares/sliding-doors-v1/collider-door-template.json'
MODEL='models/maps/ares/sliding-doors-v1/ares_sliding_leaf.vmdl'
NS=uuid.UUID('cf436d94-97ff-46af-af20-432a9e5a8b9a')

def scene_objects():
    template=json.loads(TEMPLATE.read_text());meta=json.loads((ROOT/'Assets'/(MODEL+'.meta')).read_text());objects=[]
    for side,world_y in [('west',1116),('east',-1116)]:
        node=copy.deepcopy(template);mapping={}
        def collect(value):
            if isinstance(value,dict):
                if '__guid' in value:mapping[value['__guid']]=str(uuid.uuid5(NS,side+'/'+value['__guid']))
                for x in value.values():collect(x)
            elif isinstance(value,list):
                for x in value:collect(x)
        def remap(value):
            if isinstance(value,dict):return {k:remap(v) for k,v in value.items()}
            if isinstance(value,list):return [remap(v) for v in value]
            return mapping.get(value,value) if isinstance(value,str) else value
        collect(node);node=remap(node)
        node['Name']=f'Ares {side} automatic sliding door';node['Position']=f'0,{world_y},0'
        control=next(c for c in node['Components'] if c['__type']=='Facepunch.AutomaticSlidingDoor')
        control.update({'Width':224,'Height':176,'Travel':114,'LeftClosedPosition':'0,56,88','RightClosedPosition':'0,-56,88'})
        assert len(node['Children'])==2
        for child,offset in zip(node['Children'],(56,-56)):
            child['Position']=f'0,{offset},88';child['Scale']='1,1,1'
            for component in child['Components']:
                if component['__type'] in ('Sandbox.ModelRenderer','Sandbox.ModelCollider'):
                    component['Model']={'Id':meta['guid'],'Path':MODEL}
        assert control['LeftLeaf']['go']==node['Children'][0]['__guid']
        assert control['RightLeaf']['go']==node['Children'][1]['__guid']
        objects.append(node)
    # The small east control-room entrance uses the same moving leaves at human scale.
    objects.append(json.loads((ROOT/'Sources/Ares/control-room-door-v1/door.json').read_text()))
    return objects

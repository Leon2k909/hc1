"""Accepted standalone doorway pots; keep legacy planting IDs stable."""
import map_kit as K

MODEL='models/maps/belltower/terracotta-pot-v2/terracotta_pot.vmdl'

def place(model,centre):
    model.props.append(dict(path=MODEL,position=tuple(centre),yaw=0.,scale=(1.,1.,1.),name='Terracotta flowerpot',kind='doorway_pot'))

def group(ids,positions):
    children=[]
    for region,position in sorted(positions,key=lambda x:(x[0],tuple(x[1]))):
        key='doorway_pots/'+region+'/'+','.join(f'{v:.3f}' for v in position)
        children.append(K.game_object(ids,'Terracotta flowerpot',key,K.to_world(position),components=[
            K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Doorway flowerpots','doorway_pots',children=children)

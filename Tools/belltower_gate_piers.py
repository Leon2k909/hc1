import map_kit as K
MODEL='models/maps/belltower/gate-pier-v2/gate_pier.vmdl'
def place(model,centre,z):
    model.props.append(dict(path=MODEL,position=(*centre,z),yaw=0.,scale=(1.,1.,1.),name='Churchyard gate pier',kind='gate_pier'))
def group(ids,placements):
    children=[]
    for region,position in sorted(placements):
        key='gate_piers/'+region+'/'+','.join(f'{v:.3f}' for v in position)
        children.append(K.game_object(ids,'Churchyard gate pier',key,K.to_world(position),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Churchyard gate piers','gate_piers',children=children)

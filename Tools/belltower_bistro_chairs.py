"""Approved standalone cafe chairs with stable identities."""
import map_kit as K
MODEL='models/maps/belltower/bistro-chair-v2/bistro_chair.vmdl'
def place(model,centre,yaw,z=0.):
    model.props.append(dict(path=MODEL,position=(centre[0],centre[1],z),yaw=float(yaw),scale=(1.,1.,1.),name='Bistro chair',kind='bistro_chair',mirror_yaw_offset=180.))
def group(ids,placements):
    children=[]
    for region,position,yaw in sorted(placements,key=lambda p:(p[0],tuple(p[1]))):
        key='bistro_chairs/'+region+'/'+','.join(f'{v:.3f}' for v in position)
        children.append(K.game_object(ids,'Bistro chair',key,K.to_world(position),rotation=K.yaw_rotation(yaw),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Bistro chairs','bistro_chairs',children=children)

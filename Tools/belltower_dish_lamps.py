"""Approved standalone rolled-steel café tables with stable scene identities."""
import map_kit as K
MODEL='models/maps/belltower/dish-lamp-v2/wall_lantern.vmdl'

def place(model,centre,z=0.):
    model.props.append(dict(path=MODEL,position=(centre[0],centre[1],z),yaw=0.,scale=(1.,1.,1.),name='Suspended lamp',kind='dish_lamp'))

def group(ids,placements):
    children=[]
    for region,position in sorted(placements,key=lambda p:(p[0],tuple(p[1]))):
        key='dish_lamps/'+region+'/'+','.join(f'{v:.3f}' for v in position)
        children.append(K.game_object(ids,'Suspended lamp',key,K.to_world(position),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Suspended lamps','dish_lamps',children=children)

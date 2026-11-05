"""Approved hanging lanterns; the original design remains available separately."""
import map_kit as K
MODEL='models/maps/belltower/wall-lantern-v2/wall_lantern.vmdl'
ORIGINAL='models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl'

def matches(reach,scale):
    return abs(reach-15.)<1e-6 and abs(scale-.8)<1e-6

def place(model,anchor,yaw):
    model.props.append(dict(path=MODEL,position=tuple(anchor),yaw=float(yaw),scale=(1.,1.,1.),name='Wall lantern',kind='wall_lantern',mirror_yaw_offset=180.))

def group(ids,placements):
    children=[]
    for region,position,yaw in sorted(placements,key=lambda p:(p[0],tuple(p[1]))):
        key='wall_lanterns/'+region+'/'+','.join(f'{v:.3f}' for v in position)
        children.append(K.game_object(ids,'Wall lantern',key,K.to_world(position),rotation=K.yaw_rotation(yaw),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Wall lanterns','wall_lanterns',children=children)

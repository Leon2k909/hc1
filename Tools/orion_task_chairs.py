"""Orion reuses the dark padded Collider chair approved on 2026-10-29."""
import math
import map_kit as K
RESOURCE='models/props/collider/chair-trial-v1/after.vmdl'
SCALE=.82
def objects(ids,placements):
    out=[]
    for index,(position,facing) in enumerate(placements):
        key=f'operator_chair/{index}';yaw=(math.degrees(math.atan2(facing[1],facing[0]))+90)%360
        out.append(K.game_object(ids,'Operator Chair',key,K.to_world(position),K.yaw_rotation(yaw),scale=K.vec((SCALE,)*3),components=[
            K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',BodyGroups=18446744073709551615,Model=RESOURCE,RenderType='On',Tint='1,1,1,1')]))
    return out

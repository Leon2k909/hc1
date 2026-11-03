"""Approved Riverdale wall phones: shared model instances with matching collision."""
import math
import map_kit as K
MODEL='models/props/riverdale/emergency-phone-v1/after.vmdl'
PLACED=[]
def record(position,facing):
    # The model's front is local -X in engine coordinates, opposite its +X forward axis.
    yaw=(K.plan_yaw(facing)+180.)%360.
    item=(tuple(float(x) for x in K.to_world(position)),yaw)
    if item not in PLACED:PLACED.append(item)
def scene_group(ids,placed=None):
    children=[]
    for world,yaw in PLACED if placed is None else placed:
        key=f'emergency-phone/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}'
        children.append(K.game_object(ids,'Emergency Phone',key,world,rotation=K.yaw_rotation(yaw),tags='emergency-phone',components=[
            K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MODEL,RenderType='On',Tint='1,1,1,1',BodyGroups=18446744073709551615),
            K.component(ids,'Sandbox.ModelCollider',key+'/collider',Model=MODEL,Static=True),
        ]))
    return K.game_object(ids,'Emergency Phones','emergency-phones',children=children)

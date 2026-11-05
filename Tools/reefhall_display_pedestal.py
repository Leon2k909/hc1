"""Approved standalone display pedestal, restricted to the reviewed southwest rotunda tank."""
import math
import map_kit as K
MODEL='models/props/reefhall/display_pedestal_v1/pedestal.vmdl'
POSITION=(430*math.cos(math.radians(200)),430*math.sin(math.radians(200)),0.)
def matches(centre,size,z):
    return all(abs(float(a)-b)<.001 for a,b in zip(centre[:2],POSITION[:2])) and tuple(size)==(44,44) and abs(z)<.001
def scene_object(ids):
    return K.game_object(ids,'Rotunda Display Pedestal','aquarium/display_pedestal',K.to_world(POSITION),components=[
        K.component(ids,'Sandbox.ModelRenderer','aquarium/display_pedestal/renderer',BodyGroups=18446744073709551615,Model=MODEL,RenderType='On',Tint='1,1,1,1')])

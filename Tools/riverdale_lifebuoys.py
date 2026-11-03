"""Approved lifebuoy instances; shared materials and three native model LODs."""
import map_kit as K
MODEL = 'models/maps/riverdale/lifebuoy_v2/lifebuoy.vmdl'
STAND_OFF = .25  # Clear the wall's raised epoxy band.
PLACED = []

def placement(at, out):
    position = (at[0]+out[0]*STAND_OFF, at[1]+out[1]*STAND_OFF, at[2])
    return tuple(float(x) for x in K.to_world(position)), K.plan_yaw(out) % 360

def record(at, out):
    PLACED.append(placement(at, out))

def scene_group(ids, placed=None):
    children=[]
    for position,yaw in PLACED if placed is None else placed:
        key='lifebuoy/'+','.join(f'{x:.3f}' for x in position)
        children.append(K.game_object(ids,'Lifebuoy',key,position,K.angles_rotation(0,yaw),components=[
            K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',BodyGroups=18446744073709551615,
                        Model=MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Lifebuoys','lifebuoys',children=children)

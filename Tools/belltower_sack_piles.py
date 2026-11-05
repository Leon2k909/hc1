"""Approved bakery sack piles, preserving collision in the caller."""
import map_kit as K
MODEL='models/maps/belltower/sack-pile-v2/sack_pile.vmdl'
MIRROR='models/maps/belltower/sack-pile-v2/sack_pile_mirrored.vmdl'
def place(model,centre,yaw,z):
    model.props.append(dict(path=MODEL,position=(centre[0],centre[1],z),yaw=float(yaw),scale=(1.,1.,1.),name='Bakery sack pile',kind='sack_pile'))
def group(ids,placements):
    children=[]
    for region,position in sorted(placements):
        key='sack_piles/'+region
        children.append(K.game_object(ids,'Bakery sack pile',key,K.to_world(position),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=MIRROR if region=='east' else MODEL,RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Bakery sack piles','sack_piles',children=children)

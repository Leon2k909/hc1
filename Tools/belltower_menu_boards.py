"""Accepted freestanding menu boards; independent LODs and stable scene IDs."""
import map_kit as K
PREFIX='models/maps/belltower/menu-board-v2'
def path(picture):
    assert picture in ('chalkboard_a','chalkboard_b')
    return PREFIX+('/menu_board_b.vmdl' if picture=='chalkboard_b' else '/menu_board.vmdl')
def place(model,centre,yaw,picture,z=0.):
    model.props.append(dict(path=path(picture),position=(centre[0],centre[1],z),yaw=float(yaw),scale=(1.,1.,1.),name='Menu board',kind='menu_board',picture=picture))
def group(ids,placements):
    children=[]
    for region,position,yaw,picture in sorted(placements,key=lambda p:(p[0],tuple(p[1]))):
        key='menu_boards/'+region+'/'+','.join(f'{v:.3f}' for v in position)
        children.append(K.game_object(ids,'Menu board',key,K.to_world(position),rotation=K.yaw_rotation(yaw),components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',Model=path(picture),RenderType='On',Tint='1,1,1,1')]))
    return K.game_object(ids,'Menu boards','menu_boards',children=children)

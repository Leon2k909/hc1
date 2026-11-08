"""Approved recessed undercroft frontage and its two interior fixtures."""
import map_kit as K

def scene_object(ids):
    key='launch-deck/undercroft-facade'
    children=[K.game_object(ids,'Utility Room Ceiling Light',f'{key}/light/{i}',(926,y,90),components=[
        K.component(ids,'Sandbox.PointLight',f'{key}/light/{i}/component',Radius=90,LightColor='0.9,0.82,0.65,1',Shadows=True,Attenuation=1)]) for i,y in enumerate((380,130))]
    return K.game_object(ids,'Orion Undercroft Façade',key,components=[
        K.component(ids,'Sandbox.ModelRenderer',f'{key}/renderer',Model='models/props/orion/undercroft_facade_v1/facade.vmdl',BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')],children=children)

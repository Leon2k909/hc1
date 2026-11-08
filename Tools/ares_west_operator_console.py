"""Approved west control-room console; keep the original hall collision hull."""
import math
import map_kit as K
def scene_object(ids):
    return K.game_object(ids,'West Control Room Operator Console','hall/west-operator-console',(240,1074,0),rotation=f'0,0,{math.sin(math.pi/4)},{math.cos(math.pi/4)}',components=[
        K.component(ids,'Sandbox.ModelRenderer','hall/west-operator-console/renderer',Model='models/props/ares/west_operator_console_v1/after.vmdl',BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])

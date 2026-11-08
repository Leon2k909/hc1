"""Approved east core console; existing map collision is retained."""
import map_kit as K
MODEL='models/props/ares/control_console_native_v1/console.vmdl'
def scene_object(ids):
    return K.game_object(ids,'Core Process Console','core/process-console',(-440,-230,0),components=[
        K.component(ids,'Sandbox.ModelRenderer','core/process-console/renderer',Model=MODEL,BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])

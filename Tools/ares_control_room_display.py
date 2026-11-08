"""Approved GAS / COMPOSITION display; world-space geometry, no added collision."""
import map_kit as K
def scene_object(ids):
    return K.game_object(ids,'West Control Room Display','hall/west-control-room-display',(0,0,0),components=[
        K.component(ids,'Sandbox.ModelRenderer','hall/west-control-room-display/renderer',Model='models/props/ares/control_room_display_v1/display.vmdl',BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])

"""Approved T2 central front window frame; original pane stays in the lowland mesh."""
import map_kit as K
MODEL='models/props/riverside/sliding_window_v1/window.vmdl'
def scene_object(ids):
    return K.game_object(ids,'T2 Sliding Window Frame','t2/sliding_window',K.to_world((-820.,995.,76.)),components=[
        K.component(ids,'Sandbox.ModelRenderer','t2/sliding_window/renderer',BodyGroups=18446744073709551615,Model=MODEL,RenderType='On',Tint='1,1,1,1')])

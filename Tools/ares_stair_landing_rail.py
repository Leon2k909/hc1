"""Approved west main-stair landing railing; original hall collision is retained."""
import map_kit as K
def scene_object(ids):
    return K.game_object(ids,'West Stair Landing Rail','hall/west-stair-landing-rail',(0,0,0),components=[
        K.component(ids,'Sandbox.ModelRenderer','hall/west-stair-landing-rail/renderer',Model='models/props/ares/stair_landing_rail_v1/rail.vmdl',BodyGroups=18446744073709551615,RenderType='On',Tint='1,1,1,1')])

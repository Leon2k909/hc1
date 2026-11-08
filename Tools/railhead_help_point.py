"""Approved west platform help point; geometry is baked in map coordinates."""
import map_kit as K

def scene_object(ids):
    return K.game_object(ids, 'West Platform Help Point', 'station/west-platform-help-point', components=[
        K.component(ids, 'Sandbox.ModelRenderer', 'station/west-platform-help-point/renderer',
                    Model='models/props/railhead/help_point_v1/help_point.vmdl',
                    BodyGroups=18446744073709551615, RenderType='On', Tint='1,1,1,1')])

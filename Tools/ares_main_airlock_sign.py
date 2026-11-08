"""Approved main airlock lightbox; geometry is baked in map coordinates."""
import map_kit as K

def scene_object(ids):
    return K.game_object(ids, 'Main Airlock Lightbox', 'hall/main-airlock-lightbox', components=[
        K.component(ids, 'Sandbox.ModelRenderer', 'hall/main-airlock-lightbox/renderer',
                    Model='models/props/ares/main_airlock_sign_v1/sign.vmdl',
                    BodyGroups=18446744073709551615, RenderType='On', Tint='1,1,1,1')])

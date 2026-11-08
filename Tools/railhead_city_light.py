"""Approved east concourse City-Light case, with baked map coordinates."""
import map_kit as K

def scene_object(ids):
    return K.game_object(ids, 'East Concourse Poster Lightbox', 'station/east-concourse-lightbox', components=[
        K.component(ids, 'Sandbox.ModelRenderer', 'station/east-concourse-lightbox/renderer',
                    Model='models/props/railhead/city_light_v1/lightbox.vmdl',
                    BodyGroups=18446744073709551615, RenderType='On', Tint='1,1,1,1')])

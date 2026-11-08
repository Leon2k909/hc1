"""Approved central platform PA speaker, baked map coordinates."""
import map_kit as K

def scene_object(ids):
    return K.game_object(ids, 'Central Platform PA Speaker', 'station/central-pa-speaker', components=[
        K.component(ids, 'Sandbox.ModelRenderer', 'station/central-pa-speaker/renderer',
                    Model='models/maps/railhead/pa-speaker-v2/pa_speaker.vmdl',
                    BodyGroups=18446744073709551615, RenderType='On', Tint='1,1,1,1')])

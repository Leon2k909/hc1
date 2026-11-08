"""Approved court sand bin; shared model uses baked map coordinates."""
import map_kit as K

def scene_object(ids):
    return K.game_object(ids, 'Court Sand Bin', 'yard/court-sand-bin', components=[
        K.component(ids, 'Sandbox.ModelRenderer', 'yard/court-sand-bin/renderer',
                    Model='models/maps/riverdale/sand-bin-v1/sand_bin.vmdl',
                    BodyGroups=18446744073709551615, RenderType='On', Tint='1,1,1,1')])

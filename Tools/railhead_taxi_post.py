"""Approved east taxi-rank head post; model geometry uses baked map coordinates."""
import map_kit as K

def scene_object(ids):
    return K.game_object(ids, 'East Taxi Rank Head Post', 'station/east-taxi-rank-head', components=[
        K.component(ids, 'Sandbox.ModelRenderer', 'station/east-taxi-rank-head/renderer',
                    Model='models/maps/railhead/taxi-post-v1/taxi_post.vmdl',
                    BodyGroups=18446744073709551615, RenderType='On', Tint='1,1,1,1')])

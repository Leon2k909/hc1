""" Belltower's church pews in the scene: one placed copy of pew_v2 where each old pew stood, a renderer only. belltower_map.church keeps their
old boxes as collision and draws nothing. See docs/notes and Sources/Belltower/props/pew-v2/. """
import map_kit as K

MODEL = "models/props/belltower/pew_v2/pew.vmdl"
ROWS = ( -440, -484, -528, -572, -700, -744 )   # each row's back, n
BLOCKS = ( ( -140.0, -40.0 ), ( 40.0, 140.0 ) )   # either side of the aisle, e
DEPTH = 18.0
FACING = ( 0.0, -1.0 )                            # towards the altar


def placements():
    """ Each pew's middle on the floor, in plan ( e, n, z ). """
    return [ ( ( e0 + e1 ) / 2, n - DEPTH / 2, 0.0 ) for n in ROWS for e0, e1 in BLOCKS ]


def scene_group( ids ):
    yaw = K.plan_yaw( FACING ) % 360.0
    objects = []
    for at in placements():
        world = tuple( float( x ) for x in K.to_world( at ) )
        key = f"pew/{world[0]:.1f},{world[1]:.1f}"
        objects.append( K.game_object( ids, "Pew", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Church Pews", "church-pews", children=objects )

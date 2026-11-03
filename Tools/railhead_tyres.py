""" Railhead's stacked tyres in the scene: a placed copy of tyre_v2 for each tyre the map's stacks have. railhead_dress_detail.tyre_stack keeps each stack's collision in the dress models and records
its tyres here, and draws nothing. tyre_stack_old still builds the old ones, for comparing. See Sources/Railhead/tyre-v2/. """
import map_kit as K

MODEL = "models/props/railhead/tyre_v2/tyre_{}.vmdl"
PLACED = []


def index_for( e, n, k ):
    """ Tyre k of the stack at plan ( e, n ): the same each run, and different from stack to stack. """
    return int( abs( e ) * 3 + abs( n ) * 7 ) + k


def record( position, index ):
    """ A tyre lying flat with its foot at plan ( e, n, z ). index picks its shape and turn, so a stack's tyres differ. """
    PLACED.append( ( K.to_world( position ).round( 3 ), "ab"[index % 2], round( ( index * 137.5 + 20.0 ) % 360.0, 3 ) ) )


def scene_group( placed=None ):
    from railhead_map import ids
    objects = []
    for at, shape, yaw in placed if placed is not None else PLACED:
        key = f"stacked-tyre/{at[0]:.1f},{at[1]:.1f},{at[2]:.1f}"
        objects.append( K.game_object( ids, "Tyre", key, tuple( float( x ) for x in at ), rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL.format( shape ), RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Stacked Tyres", "stacked-tyres", children=objects )

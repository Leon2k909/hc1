""" Veridant's lounge sofas in the scene: one placed copy of sofa_v2 for each sofa the map puts down, a renderer only. veridant_parts.sofa keeps each
one's old box as collision, records it here, and draws nothing. See docs/notes and Sources/Veridant/sofa-v2/. """
import map_kit as K

LENGTHS = ( 84, 96, 120 )
PLACED = []


def model_for( length ):
    return f"models/props/veridant/sofa_v2/sofa_{int( length )}.vmdl"


def record( position, facing, length ):
    """ A sofa at plan ( e, n, z ), facing plan heading ( de, dn ). There's a model for each length the map uses. """
    if int( length ) not in LENGTHS:
        raise ValueError( f"no sofa model {length} in long" )
    PLACED.append( ( tuple( float( x ) for x in K.to_world( position ) ), K.plan_yaw( facing ) % 360.0, int( length ) ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw, length in placed if placed is not None else PLACED:
        key = f"sofa/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Sofa", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model_for( length ), RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Sofas", "sofas", children=objects )

""" Riverdale's first aid cabinets in the scene: one placed copy of first_aid_v2 for each one the hall puts up, a renderer only, as the old boxes had no collision. riverdale_hall.first_aid
records each one here and draws nothing. See docs/notes and Sources/Riverdale/first-aid-v2/. """
import map_kit as K

MODEL = "models/maps/riverdale/first_aid_v2/first_aid.vmdl"
PLACED = []


def placement( position, out ):
    """ World position and yaw for a cabinet on a wall's face, its foot at plan ( e, n, z ), the wall looking along plan heading out. The model's +X comes out of the wall. """
    return tuple( float( x ) for x in K.to_world( position ) ), K.plan_yaw( out ) % 360.0


def record( position, out ):
    PLACED.append( placement( position, out ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw in placed if placed is not None else PLACED:
        key = f"first-aid/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "First Aid Cabinet", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "First Aid Cabinets", "first-aid-cabinets", children=objects )

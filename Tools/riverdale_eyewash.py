""" Riverdale's wall-mounted eye washes in the scene: one placed copy of eyewash_v2 for each one the hall puts up, a renderer only. riverdale_hall.eyewash records each one
here and draws only its sign, as the old ones had no collision. See docs/notes and Sources/Riverdale/eyewash_v2/. """
import map_kit as K

MODEL = "models/maps/riverdale/eyewash_v2/eyewash.vmdl"
STAND_OFF = 0.25    # The walls' epoxy band stands this far proud of the wall, and it would swallow the bracket's plate.
PLACED = []


def placement( position, out ):
    """ World position and yaw for an eye wash on a wall's face at plan ( e, n, z ), the wall looking along plan heading out. The model's +Y comes out of the wall. """
    return tuple( float( x ) for x in K.to_world( position ) ), K.plan_yaw( ( out[1], -out[0] ) ) % 360.0


def record( position, out ):
    PLACED.append( placement( position, out ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw in placed if placed is not None else PLACED:
        key = f"eyewash/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Eye Wash", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Eye Washes", "eyewashes", children=objects )

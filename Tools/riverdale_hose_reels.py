""" Riverdale's fire hose reel cabinets in the scene: one placed copy of hose_reel_v2 for each one the hall puts up, a renderer only. riverdale_hall.hose_cabinet records
each one here and draws nothing, as the old cabinets had no collision. See docs/notes and Sources/Riverdale/hose-reel-v2/. """
import map_kit as K

MODEL = "models/maps/riverdale/hose_reel_v2/hose_reel.vmdl"
PLACED = []


def placement( position, out ):
    """ World position and yaw for a cabinet on a wall's face at plan ( e, n, z ), z its bottom edge, the wall looking along plan heading out. The model's +X comes out of the wall. """
    return tuple( float( x ) for x in K.to_world( position ) ), K.plan_yaw( out ) % 360.0


def record( position, out ):
    PLACED.append( placement( position, out ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw in placed if placed is not None else PLACED:
        key = f"hose_reel/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Hose Reel", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Hose Reels", "hose_reels", children=objects )

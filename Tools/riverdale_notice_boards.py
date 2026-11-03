""" Riverdale's cork notice boards in the scene: one placed copy of notice_board_v2 for each one the hall puts up, a renderer only. riverdale_hall.notice_board records
each one here and draws nothing, as the old boards had no collision. See docs/notes and Sources/Riverdale/notice-board-v2/. """
import map_kit as K

MODEL = "models/maps/riverdale/notice_board_v2/notice_board.vmdl"
PLACED = []


def placement( position, out ):
    """ World position and yaw for a board on a wall's face at plan ( e, n, z ), z its bottom edge, the wall looking along plan heading out. The model's +X comes out of the wall. """
    return tuple( float( x ) for x in K.to_world( position ) ), K.plan_yaw( out ) % 360.0


def record( position, out ):
    PLACED.append( placement( position, out ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw in placed if placed is not None else PLACED:
        key = f"notice_board/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Notice Board", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Notice Boards", "notice_boards", children=objects )

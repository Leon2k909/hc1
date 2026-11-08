""" Riverdale's B1 control-room desk in the scene: one placed copy of b1_desk for the plain 72 x 40 x 30 in box the generator used to draw. A renderer only: the old box's collision
stays in the map's model (desk() adds the same box and records where the new model goes, drawing nothing). riverdale_map's b1() calls desk(). See Sources/Riverdale/b1-desk-v1/.
The old plain box was deleted on the user's approval (2026-11-06). """
import map_kit as K
import riverdale_parts as P

NEW_DESK = True
MODEL = "models/props/riverdale/b1_desk_v1/b1_desk.vmdl"
SIZE = ( 72.0, 40.0, 30.0 )
PLACED = []


def desk( m, e0, e1, n0, n1, z0, out=( 0, 1 ) ):
    """ In place of box( m, e0, e1, n0, n1, z0, z0 + 30, { "default": "rv_desk", "+z": "rv_dark" }, METAL ). The model's origin is the middle of its footprint on the floor and its +n
    side (drawers, kneehole) looks along plan heading out. """
    assert abs( ( e1 - e0 ) - SIZE[0] ) < 1e-6 and abs( ( n1 - n0 ) - SIZE[1] ) < 1e-6 and tuple( out ) == ( 0, 1 ), ( e1 - e0, n1 - n0, out )
    centre = ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z0 )
    PLACED.append( ( MODEL, tuple( float( x ) for x in K.to_world( centre ) ), K.plan_yaw( out ) % 360.0 ) )
    m.collision_box( ( e0, n0, z0 ), ( e1, n1, z0 + SIZE[2] ), P.METAL )


def scene_group( ids, placed=None ):
    objects = []
    for model, world, yaw in placed if placed is not None else PLACED:
        key = f"desks/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "B1 Desk", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Desks", "desks", children=objects )

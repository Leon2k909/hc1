""" Riverdale's locker banks in the scene: one placed copy of locker_bank_4 (52 in wide) or locker_bank_6 (80 in) for each plain 20 x 80 in slab the generator used to draw. A renderer only:
the slabs' collision boxes stay in the map's models (bank() adds the same box the old box() did and records where the new model goes, drawing nothing). riverdale_map's b1() and spawn_side()
call bank(). See Sources/Riverdale/locker-bank-v1/. The old plain boxes were deleted on the user's approval (2026-11-06). """
import map_kit as K
import riverdale_parts as P

NEW_LOCKERS = True
HEIGHT = 80.0
DEPTH = 20.0
MODELS = { 52: "models/props/riverdale/locker_bank_v1/locker_bank_4.vmdl", 80: "models/props/riverdale/locker_bank_v1/locker_bank_6.vmdl" }
PLACED = []


def placement( e0, e1, n0, n1, z0, out ):
    """ ( model path, world position, yaw ) for a bank filling plan e0..e1, n0..n1 from z0, its doors looking along plan heading out ( 0, 1 ) or ( 1, 0 ). The model's origin is the middle of its
    footprint on the floor and its +X, the doors' way, becomes out. """
    along_e = abs( out[1] ) > abs( out[0] )
    width, depth = ( e1 - e0, n1 - n0 ) if along_e else ( n1 - n0, e1 - e0 )
    assert abs( depth - DEPTH ) < 1e-6 and round( width ) in MODELS, ( width, depth )
    centre = ( ( e0 + e1 ) / 2, ( n0 + n1 ) / 2, z0 )
    return MODELS[round( width )], tuple( float( x ) for x in K.to_world( centre ) ), K.plan_yaw( out ) % 360.0


def bank( m, e0, e1, n0, n1, z0, out ):
    """ In place of box( m, e0, e1, n0, n1, z0, z0 + 80, "rv_steel", METAL ). """
    PLACED.append( placement( e0, e1, n0, n1, z0, out ) )
    m.collision_box( ( e0, n0, z0 ), ( e1, n1, z0 + HEIGHT ), P.METAL )


def scene_group( ids, placed=None ):
    objects = []
    for model, world, yaw in placed if placed is not None else PLACED:
        key = f"lockers/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Locker Bank", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Locker Banks", "locker-banks", children=objects )

""" Riverdale's spawn-yard guard hut doors in the scene: one placed copy of guard_hut_door for the P.door( ..., 36, 82, paint="rv_fc_door_blue", double=False, mount="surface" )
each guard hut used to draw. The huts themselves are the original concrete boxes (the user kept those and chose only the new door, 2026-11-07). A renderer only, as the old door
was (no collision). riverdale_map.guard_hut() calls door(). See Sources/Riverdale/guard-hut-door-v1/. """
import map_kit as K

NEW_DOOR = True
MODEL = "models/props/riverdale/guard_hut_door_v1/guard_hut_door.vmdl"
PLACED = []


def door( m, foot ):
    """ In place of P.door( m, foot, right, 36, 82, paint="rv_fc_door_blue", double=False, mount="surface" ) on a +n wall face: foot is the door's centre at the wall's foot. """
    del m
    PLACED.append( ( MODEL, tuple( float( x ) for x in K.to_world( tuple( float( c ) for c in foot ) ) ), 0.0 ) )


def scene_group( ids, placed=None ):
    objects = []
    for model, world, yaw in placed if placed is not None else PLACED:
        key = f"hut-doors/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Guard Hut Door", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Guard Hut Doors", "guard-hut-doors", children=objects )

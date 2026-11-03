""" Cerro Blanco's wall extinguishers in the scene: one placed copy of Railhead's extinguisher-v2 for each room that has one, a renderer only. cerroblanco_fitout.door_fittings
records each one here and draws nothing, as the old ones had no collision. See docs/notes and Sources/CerroBlanco/extinguisher-v2/. """
import map_kit as K

MODEL = "models/props/extinguisher-v2/extinguisher.vmdl"
# The new model is wider than the old one: these three would touch a painting's frame, so they stand 2 in along the wall. World x, y of the old spot on the wall, then the move.
BESIDE_ART = { ( 40.0, -498.0 ): ( -2.0, 0.0 ), ( 697.0, -1058.0 ): ( 0.0, 2.0 ), ( -1018.0, 972.0 ): ( 0.0, 2.0 ) }
PLACED = []


def record( position, facing ):
    """ An extinguisher with its foot at plan ( e, n, z ) on a wall's face, facing plan heading ( de, dn ). """
    world = [ float( x ) for x in K.to_world( position ) ]
    # Only the ground floor's: the same wall upstairs has no painting there.
    if world[2] < 100.0:
        move = BESIDE_ART.get( ( round( world[0], 1 ), round( world[1], 1 ) ), ( 0.0, 0.0 ) )
        world = [ world[0] + move[0], world[1] + move[1], world[2] ]
    PLACED.append( ( tuple( world ), K.plan_yaw( facing ) % 360.0 ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw in placed if placed is not None else PLACED:
        key = f"extinguisher/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Extinguisher", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Extinguishers", "extinguishers", children=objects )

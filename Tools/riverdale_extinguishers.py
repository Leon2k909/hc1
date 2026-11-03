""" Riverdale's wall extinguishers in the scene: one placed copy of Railhead's extinguisher-v2 for each one the hall puts up, a renderer only. riverdale_hall.extinguisher
records each one here and draws nothing, as the old ones had no collision. See docs/notes and Sources/Riverdale/extinguisher-v2/. """
import map_kit as K

MODEL = "models/props/extinguisher-v2/extinguisher.vmdl"
PLACED = []


def record( position, facing ):
    """ An extinguisher with its foot at plan ( e, n, z ) on a wall's face, facing plan heading ( de, dn ). """
    PLACED.append( ( tuple( float( x ) for x in K.to_world( position ) ), K.plan_yaw( facing ) % 360.0 ) )


def scene_group( ids, placed=None ):
    objects = []
    for world, yaw in placed if placed is not None else PLACED:
        key = f"extinguisher/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Extinguisher", key, world, rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Extinguishers", "extinguishers", children=objects )

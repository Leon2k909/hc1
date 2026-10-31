""" Cerro Blanco's garden boulders in the scene. The garden has six, and the user wanted all three shapes in use: two old stones stay in the dressing model
(faces and hull from cerroblanco_parts.boulder), and these four are placed copies of boulder_v2 with their own collision. See Sources/CerroBlanco/boulder-v2/. """
import map_kit as K

MODEL = "models/props/cerroblanco/boulder_v2/boulder_{}.vmdl"
# The garden's list of boulders in cerroblanco_map, by its index: shape, yaw and scale. The scale takes each stone to that spot's old height.
NEW = { 0: ( "a", 30.0, 0.93 ), 1: ( "b", 200.0, 1.0 ), 3: ( "b", 300.0, 0.76 ), 4: ( "a", 70.0, 0.67 ) }
PLACED = {}


def record( k, position ):
    """ Boulder k of the garden's list, at plan ( e, n, z ). """
    PLACED[k] = position


def scene_group( ids, placed=None ):
    objects = []
    for k, position in sorted( ( placed if placed is not None else PLACED ).items() ):
        shape, yaw, scale = NEW[k]
        model = MODEL.format( shape )
        key = f"garden-boulder/{k}"
        objects.append( K.game_object( ids, f"Boulder {k}", key, tuple( float( x ) for x in K.to_world( position ) ), rotation=K.angles_rotation( 0.0, yaw ),
                                       scale=f"{scale},{scale},{scale}", components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model, RenderType="On", Tint="1,1,1,1" ),
            K.component( ids, "Sandbox.ModelCollider", key + "/collider", IsTrigger=False, Model=model, Static=True ),
        ] ) )
    return K.game_object( ids, "Garden Boulders", "garden-boulders", children=objects )

""" Cerro Blanco's cafe chairs in the scene: one placed copy of cafe_chair_v2 for each chair cerroblanco_parts.cafe_chair is asked for, a renderer only. The chair's collision box stays in the
dressing model, where cafe_chair still puts it. See docs/notes and Sources/CerroBlanco/cafe-chair-v2/. """
import map_kit as K

MODEL = "models/maps/cerroblanco/cafe_chair_v2/chair.vmdl"
PLACED = []


def record( e, n, yaw, z=0.0 ):
    """ A chair at plan ( e, n, z ), facing plan yaw (cerroblanco_parts.turned's: its own +x is the plan direction at yaw from east). """
    PLACED.append( ( float( e ), float( n ), float( z ), float( yaw ) ) )


def scene_group( ids, placed=None ):
    objects = []
    for e, n, z, yaw in placed if placed is not None else PLACED:
        world = tuple( float( x ) for x in K.to_world( ( e, n, z ) ) )
        key = f"cafe-chair/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        # The model faces its +x; plan heading ( cos, sin ) is world ( sin, -cos ), so its world yaw is the plan's less 90.
        objects.append( K.game_object( ids, "Cafe Chair", key, world, rotation=K.angles_rotation( 0.0, ( yaw - 90.0 ) % 360.0 ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Cafe Chairs", "cafe-chairs", children=objects )

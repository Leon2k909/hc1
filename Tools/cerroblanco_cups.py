""" Cerro Blanco's cafe cups in the scene: two placed copies of cafe_cup_v2 on each cafe table cerroblanco_tables recorded, renderers only, where the fit-out used to draw a disc and a cone:
6 in from the table's middle at 70 degrees (the full cup) and 230 (the drunk one, with its spoon), each handle along the table's edge. See docs/notes and Sources/CerroBlanco/cafe-cup-v2/. """
import math

import map_kit as K

import cerroblanco_tables

FULL = "models/maps/cerroblanco/cafe_cup_v2/cup.vmdl"
DRUNK = "models/maps/cerroblanco/cafe_cup_v2/cup_empty.vmdl"
TOP = 29.5


def places( tables=None ):
    """ Plan ( e, n, z ), plan angle round its table and model for each cup. """
    out = []
    for e, n, z in tables if tables is not None else cerroblanco_tables.PLACED:
        for k, a in enumerate( ( 70.0, 230.0 ) ):
            out.append( ( e + 6 * math.cos( math.radians( a ) ), n + 6 * math.sin( math.radians( a ) ), z + TOP, a, FULL if k == 0 else DRUNK ) )
    return out


def scene_group( ids, tables=None ):
    objects = []
    for e, n, z, a, model in places( tables ):
        world = tuple( float( x ) for x in K.to_world( ( e, n, z ) ) )
        key = f"cafe-cup/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        # The handle is the model's +x; along the table's edge is plan heading a - 90, which is world yaw a - 180.
        objects.append( K.game_object( ids, "Cafe Cup", key, world, rotation=K.angles_rotation( 0.0, ( a - 180.0 ) % 360.0 ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Cafe Cups", "cafe-cups", children=objects )

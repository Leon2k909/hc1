""" Cerro Blanco's cafe tables in the scene: one placed copy of cafe_table_v2 for each table cerroblanco_parts.cafe_table is asked for, a renderer only. The table's collision box stays in the
dressing model, where cafe_table still puts it. A table with a parasol over it (cerroblanco_parasols) gets table_top, the top and its spider only, as the parasol's socket tube and base stand under
it; the rest get the whole table. See docs/notes and Sources/CerroBlanco/cafe-table-v2/. """
import map_kit as K

import cerroblanco_parasols

MODEL = "models/maps/cerroblanco/cafe_table_v2/table.vmdl"
TOP_ONLY = "models/maps/cerroblanco/cafe_table_v2/table_top.vmdl"
PLACED = []


def record( e, n, z=0.0 ):
    PLACED.append( ( float( e ), float( n ), float( z ) ) )


def under_parasol( e, n, parasols ):
    return any( abs( pe - e ) < 0.5 and abs( pn - n ) < 0.5 for pe, pn, _ in parasols )


def scene_group( ids, placed=None, parasols=None ):
    parasols = parasols if parasols is not None else cerroblanco_parasols.PLACED
    objects = []
    for e, n, z in placed if placed is not None else PLACED:
        world = tuple( float( x ) for x in K.to_world( ( e, n, z ) ) )
        key = f"cafe-table/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        model = TOP_ONLY if under_parasol( e, n, parasols ) else MODEL
        objects.append( K.game_object( ids, "Cafe Table", key, world, components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=model, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Cafe Tables", "cafe-tables", children=objects )

""" Cerro Blanco's courtyard parasols in the scene: one placed copy of parasol_v2 over each cafe table that cerroblanco_parts.parasol is asked for, a renderer only, as the old ones had no
collision (the table's own box stays in the dressing model). parasol records each one here and draws nothing. See docs/notes and Sources/CerroBlanco/parasol-v2/. """
import map_kit as K

MODEL = "models/maps/cerroblanco/parasol_v2/parasol.vmdl"
# The canopy is square, so each turns a quarter more than the last: the cleat, the strap and the base's lettering face different ways.
TURNS = ( 0.0, 90.0, 180.0, 270.0 )
PLACED = []


def record( e, n, z=0.0 ):
    PLACED.append( ( float( e ), float( n ), float( z ) ) )


def scene_group( ids, placed=None ):
    objects = []
    for k, ( e, n, z ) in enumerate( placed if placed is not None else PLACED ):
        world = tuple( float( x ) for x in K.to_world( ( e, n, z ) ) )
        key = f"parasol/{world[0]:.1f},{world[1]:.1f},{world[2]:.1f}"
        objects.append( K.game_object( ids, "Parasol", key, world, rotation=K.angles_rotation( 0.0, TURNS[k % len( TURNS )] ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Parasols", "courtyard-parasols", children=objects )

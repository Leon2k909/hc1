""" Railhead's two yard skips in the scene: Lowtide's welded open skip (Tools/lowtide_skip.py) as a model of its own, with its own collision round its open inside.
railhead_dress_detail.skip_bin records each one here and draws nothing. skip_bin_old still builds the old closed box, for comparing. See Sources/Railhead/skip/. """
import map_kit as K
import lowtide_skip as SKIP

FOLDER = "models/props/railhead/skip"
MODEL = f"{FOLDER}/skip.vmdl"
PLACED = []


def record( position ):
    """ A skip with its long side along n, standing at plan ( e, n, z ). """
    PLACED.append( K.to_world( position ).round( 3 ) )


def write_model():
    model = K.Model()
    SKIP.build( model, ( 0.0, 0.0, 0.0 ), "n" )
    SKIP.configure( model )
    return K.write_model( K.ASSETS / FOLDER, FOLDER, "skip", model )


def scene_group( placed=None ):
    from railhead_map import ids
    objects = []
    for at in placed if placed is not None else PLACED:
        key = f"yard-skip/{at[0]:.1f},{at[1]:.1f},{at[2]:.1f}"
        objects.append( K.game_object( ids, "Skip", key, tuple( float( x ) for x in at ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
            K.component( ids, "Sandbox.ModelCollider", key + "/collider", IsTrigger=False, Model=MODEL, Static=True ),
        ] ) )
    return K.game_object( ids, "Skips", "yard-skips", children=objects )

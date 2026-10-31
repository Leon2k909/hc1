""" Railhead's station bins in the scene: one placed copy of station_bin_v2 for each bin the map puts down. railhead_props.bin keeps each one's collision in
the dress models and records it here, and draws nothing. See docs/notes and Sources/Railhead/station-bin-v2/. """
import map_kit as K

MODEL = "models/props/railhead/station_bin_v2/bin.vmdl"
PLACED = []


def record( position, front ):
    """ A bin at plan ( e, n, z ) whose front faces plan heading ( de, dn ). """
    at = K.to_world( position ).round( 3 )
    yaw = round( K.plan_yaw( front ) % 360.0, 3 )
    PLACED.append( ( at, yaw ) )


def scene_group( placed=None ):
    from railhead_map import ids
    objects = []
    for at, yaw in placed if placed is not None else PLACED:
        key = f"station-bin/{at[0]:.1f},{at[1]:.1f},{at[2]:.1f}"
        objects.append( K.game_object( ids, "Station Bin", key, tuple( float( x ) for x in at ), rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Station Bins", "station-bins", children=objects )

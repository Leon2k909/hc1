""" Railhead's hand pallet trucks in the scene: a placed copy of pallet_truck_v2 for each one the map puts down. railhead_props.pallet_jack keeps its collision in the
dress models and records it here, and draws nothing. railhead_furniture.pallet_jack still builds the old one, for comparing. See Sources/Railhead/pallet-truck-v2/. """
import map_kit as K

MODEL = "models/props/railhead/pallet_truck_v2/truck.vmdl"
PLACED = []


def record( position, front ):
    """ A truck at plan ( e, n, z ) whose forks point along plan heading ( de, dn ). """
    PLACED.append( ( K.to_world( position ).round( 3 ), round( K.plan_yaw( front ) % 360.0, 3 ) ) )


def scene_group( placed=None ):
    from railhead_map import ids
    objects = []
    for at, yaw in placed if placed is not None else PLACED:
        key = f"pallet-truck/{at[0]:.1f},{at[1]:.1f},{at[2]:.1f}"
        objects.append( K.game_object( ids, "Pallet Truck", key, tuple( float( x ) for x in at ), rotation=K.angles_rotation( 0.0, yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", key + "/renderer", BodyGroups=18446744073709551615, Model=MODEL, RenderType="On", Tint="1,1,1,1" ),
        ] ) )
    return K.game_object( ids, "Pallet Trucks", "pallet-trucks", children=objects )

"""Reef Hall's straight stairs as standalone models (Sources/ReefHall/stairs-v1, 2026-11-06).

LOBBY draws the lobby's two flights (the Red-spawn side, north and south of the foyer) from models/props/reefhall/stairs_v1/
lobby_stair.vmdl and leaves the old flights' drawing (stone-slab boxes, brass strips, square-bar rails) out of the merged lobby
model. CONTROL does the same for the control room's flight (Blue-spawn side) from control_stair.vmdl.

The collision is the generator's own and is the same either way: `reefhall_map.stair( draw=False )` still adds the step boxes as
collision-only boxes and `stair_rail( draw=False )` still adds the rail hulls. Only the drawing moves into the models.

The flags are switched by Sources/ReefHall/stairs-v1/install.py when the models and the cut room OBJs are in place, so the
generator always matches what the live scene draws. Set a flag False and regenerate the room to draw the original flight again
(the room OBJs as they were are also in git history, and Sources/ReefHall/stairs-v1/revert.py puts them back byte for byte). """
import map_kit as K

LOBBY = True
CONTROL = True
ROTUNDA = True      # the Rotunda's two curved flights (Sources/ReefHall/rotunda-stairs-v1): switched on by its install.py
FILTER = True      # the filter hall's two steel flights (Sources/ReefHall/filter-stairs-v1): switched on by its install.py
OFFICE = True      # the control room office's two glass walls (Sources/ReefHall/office-partitions-v1): switched on by its install.py
OFFICE_MODEL = "models/props/reefhall/stairs_v1/office_partitions.vmdl"
FILTER_MODELS = { "A": "models/props/reefhall/stairs_v1/filter_stair_a.vmdl", "B": "models/props/reefhall/stairs_v1/filter_stair_b.vmdl" }
ROTUNDA_MODELS = { "NE": "models/props/reefhall/stairs_v1/rotunda_stair_ne.vmdl", "NW": "models/props/reefhall/stairs_v1/rotunda_stair_nw.vmdl" }
MODELS = "models/props/reefhall/stairs_v1"
LOBBY_MODEL = f"{MODELS}/lobby_stair.vmdl"
CONTROL_MODEL = f"{MODELS}/control_stair.vmdl"
LOBBY_FOOT_E = -2440.0                   # reefhall_map.LOBBY_STAIR's foot ( plan e ): both flights climb west to the balcony
LOBBY_N = 510.0                          # the north flight's centre line ( plan n ); the south flight is at -LOBBY_N
CONTROL_FOOT_E = 2666.0                  # reefhall_map.CONTROL_STAIR's foot ( the flight climbs west, to the gallery )
CONTROL_N = 835.0                        # the control flight's centre line
KEY = "aquarium/stairs"


def _renderer( ids, key, model ):
    return K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=model,
                        RenderType="On", Tint="1,1,1,1" )


def scene_objects( ids ):
    out = []
    if LOBBY:
        for tag, n in ( ( "N", LOBBY_N ), ( "S", -LOBBY_N ) ):
            key = f"{KEY}/lobby{tag}"
            out.append( K.game_object( ids, f"Lobby Stair {tag}", key, K.to_world( ( LOBBY_FOOT_E, n, 0.0 ) ),
                                       components=[ _renderer( ids, key, LOBBY_MODEL ) ] ) )
    if CONTROL:
        key = f"{KEY}/control"
        out.append( K.game_object( ids, "Control Stair", key, K.to_world( ( CONTROL_FOOT_E, CONTROL_N, 0.0 ) ),
                                   components=[ _renderer( ids, key, CONTROL_MODEL ) ] ) )
    if ROTUNDA:
        for tag, model in ROTUNDA_MODELS.items():       # both models are drawn in plan coordinates round the Rotunda's centre, the origin
            key = f"{KEY}/rotunda{tag}"
            out.append( K.game_object( ids, f"Rotunda Stair {tag}", key, K.to_world( ( 0.0, 0.0, 0.0 ) ),
                                       components=[ _renderer( ids, key, model ) ] ) )
    if OFFICE:
        key = f"{KEY}/office"
        out.append( K.game_object( ids, "Office Partitions", key, K.to_world( ( 0.0, 0.0, 0.0 ) ),
                                   components=[ _renderer( ids, key, OFFICE_MODEL ) ] ) )
    if FILTER:
        for tag, model in FILTER_MODELS.items():         # drawn in plan coordinates, so at the origin
            key = f"{KEY}/filter{tag}"
            out.append( K.game_object( ids, f"Filter Stair {tag}", key, K.to_world( ( 0.0, 0.0, 0.0 ) ),
                                       components=[ _renderer( ids, key, model ) ] ) )
    return out

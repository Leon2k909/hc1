"""The lobby balcony's glass railing as standalone models (Sources/ReefHall/lobby-rail-v1, 2026-11-06).

ENABLED draws the railing from models/props/reefhall/lobby_rail_v1 (seven sections of two bays along the north run, seven along
the south run) and leaves the original railing's drawing out of the merged lobby model. The railing's collision (the generator's
collision-only boxes in `reefhall_map.railing`) is the same either way. The user approved the new railing on 2026-11-06 and
the old backups and revert.py were then deleted; set ENABLED False and regenerate the lobby to draw the original railing again
(the original lobby OBJ is also in git history). """
import map_kit as K

ENABLED = True
SECTION = "models/props/reefhall/lobby_rail_v1/lobby_rail_section.vmdl"
SECTION_END = "models/props/reefhall/lobby_rail_v1/lobby_rail_section_end.vmdl"
RUN_E0, RUN_E1 = -2720.0, -1880.0        # reefhall_map.LOBBY_VOID's east edges ( plan e ): the north run's ends
RUN_N = 822.0                            # LOBBY_VOID's north edge + 2: the north run's line ( the south run is at -RUN_N )
Z = 208.0                                # reefhall_map.L1: the balcony floor
SECTION_LEN = 120.0
KEY = "aquarium/lobby_rail"


def scene_objects( ids ):
    if not ENABLED:
        return []
    count = int( round( ( RUN_E1 - RUN_E0 ) / SECTION_LEN ) )
    out = []
    for tag, n in ( ( "N", RUN_N ), ( "S", -RUN_N ) ):
        for j in range( count ):
            e = RUN_E1 - SECTION_LEN / 2 - SECTION_LEN * j          # the section's centre, walking west from the run's east end
            model = SECTION_END if j == count - 1 else SECTION
            key = f"{KEY}/{tag}{j}"
            out.append( K.game_object( ids, f"Lobby Rail {tag} {j}", key, K.to_world( ( e, n, Z ) ), components=[
                K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", BodyGroups=18446744073709551615, Model=model,
                             RenderType="On", Tint="1,1,1,1" ) ] ) )
    return out

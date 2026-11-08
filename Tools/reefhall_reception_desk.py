"""The lobby reception desk as a standalone model (Sources/ReefHall/reception-desk-v1, 2026-11-06).

ENABLED draws the desk from models/props/reefhall/reception_desk_v1 (one scene object round the lobby tank) and leaves
the original flat-faceted desk out of the merged lobby model. The desk's collision (the sixteen WOOD wedges in
`reefhall_map.lobby`) is the same either way. Set ENABLED False and run the generator, or run
Sources/ReefHall/reception-desk-v1/revert.py, to go back to the original desk. """
import map_kit as K

ENABLED = True
MODEL = "models/props/reefhall/reception_desk_v1/reception_desk.vmdl"
TANK = ( -2420.0, 0.0 )          # reefhall_map.LOBBY_TANK ( plan e, n ): the desk is built round this point, floor at z 0
NAME = "Lobby Reception Desk"
KEY = "aquarium/reception_desk"


def scene_objects( ids ):
    if not ENABLED:
        return []
    return [ K.game_object( ids, NAME, KEY, K.to_world( ( *TANK, 0.0 ) ), components=[
        K.component( ids, "Sandbox.ModelRenderer", f"{KEY}/renderer", BodyGroups=18446744073709551615, Model=MODEL,
                     RenderType="On", Tint="1,1,1,1" ) ] ) ]

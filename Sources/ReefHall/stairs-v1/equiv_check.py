"""Proves the generator's COLLISION does not depend on who draws the stairs.

Builds every Reef Hall room with the real generator (Tools/reefhall_map.build_rooms, seeded, nothing written) twice: once
with reefhall_stairs.LOBBY / CONTROL False (the original drawing) and once with them True (the standalone stair models
draw the flights, the generator keeps only the collision boxes and rail hulls). For every room it compares the collision
(every box and hull, rounded to 1e-5 in) and counts the polygons: the collision must be identical, and the triangles the
second build lacks must be exactly the old stairs' (the lobby's 1,552 and the control room's 700, by material).

    python equiv_check.py            writes equiv_check.json next to this file; exit code 1 if anything differs
"""
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np

ROOT = Path( r"C:\sbox-projects\hc1\forked-shooter-main" )
sys.path.insert( 0, str( ROOT / "Tools" ) )
import reefhall_map as R        # noqa: E402
import reefhall_stairs as RS    # noqa: E402

HERE = Path( __file__ ).resolve().parent
EXPECTED_REMOVED = {            # triangles by paint: what extract_old.py matched in the live room OBJs
    "lobby": { "rh_brass": 624, "rh_floor": 104, "rh_gunmetal": 240, "rh_steel": 64, "rh_wall_dark": 520 },
    "control": { "rh_brass": 312, "rh_floor": 52, "rh_gunmetal": 60, "rh_steel": 16, "rh_wall_dark": 260 },
}


def digest( rooms ):
    out = {}
    for name, model, _inside in rooms:
        boxes = [ ( np.round( np.asarray( c, float ), 5 ).tolist(), np.round( np.asarray( a, float ), 5 ).tolist(),
                    np.round( np.asarray( s, float ), 5 ).tolist(), str( surf ) ) for c, a, s, surf in model.boxes ]
        hulls = [ ( np.round( np.asarray( pts, float ), 5 ).tolist(), str( surf ) ) for pts, surf in model.hulls ]
        tris = { paint: sum( len( p ) - 2 for p, _ in items ) for paint, items in model.polygons.items() }
        out[name] = { "collision_sha256": hashlib.sha256( json.dumps( [ boxes, hulls ] ).encode() ).hexdigest(),
                      "boxes": len( boxes ), "hulls": len( hulls ), "triangles_by_paint": tris, "triangles": sum( tris.values() ) }
    return out


def build( lobby, control ):
    RS.LOBBY, RS.CONTROL = lobby, control
    t0 = time.time()
    rooms, _lights = R.build_rooms()
    result = digest( rooms )
    print( f"built with LOBBY={lobby} CONTROL={control}: {len( rooms )} rooms in {time.time() - t0:.0f} s", flush=True )
    return result


def main():
    before = build( False, False )
    after = build( True, True )
    report, bad = { "rooms": {} }, 0
    for name in before:
        b, a = before[name], after[name]
        same_collision = b["collision_sha256"] == a["collision_sha256"] and b["boxes"] == a["boxes"] and b["hulls"] == a["hulls"]
        removed = { p: b["triangles_by_paint"].get( p, 0 ) - a["triangles_by_paint"].get( p, 0 ) for p in b["triangles_by_paint"] }
        removed = { p: n for p, n in removed.items() if n }
        want = EXPECTED_REMOVED.get( name, {} )
        ok_removed = removed == want
        report["rooms"][name] = { "collision_identical": same_collision, "boxes": b["boxes"], "hulls": b["hulls"],
                                  "triangles_before": b["triangles"], "triangles_after": a["triangles"],
                                  "triangles_removed_by_paint": removed, "removed_as_expected": ok_removed }
        flag = "OK " if same_collision and ok_removed else "BAD"
        print( f"{flag} {name:10s} collision identical: {same_collision} ({b['boxes']} boxes, {b['hulls']} hulls) | "
               f"triangles {b['triangles']} -> {a['triangles']} | removed {removed or '-'}" )
        if not ( same_collision and ok_removed ):
            bad += 1
    report["all_ok"] = bad == 0
    ( HERE / "equiv_check.json" ).write_text( json.dumps( report, indent=1 ) )
    print( "ALL OK" if bad == 0 else f"{bad} room(s) differ" )
    sys.exit( 0 if bad == 0 else 1 )


if __name__ == "__main__":
    main()

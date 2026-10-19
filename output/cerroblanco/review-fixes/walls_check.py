""" Lists every outside wall the quality pass dresses: its storeys, and whether a floor is beside its plinth band
(outside) and its skirting (inside) at each, from the recorded walls and slabs. """
import sys, pickle
from pathlib import Path
HERE = Path( __file__ ).resolve().parent
sys.path.insert( 0, str( HERE.parents[2] / "Tools" ) )
import cerroblanco_map as C
import cerroblanco_quality_geometry as QG
R = pickle.load( open( HERE / "records.pkl", "rb" ) )
walls, slabs = R["wall"], R["slab"]
print( len( walls ), "walls,", len( slabs ), "slabs" )
for s in slabs:
    print( "  slab", s["e0"], s["e1"], s["n0"], s["n1"], s["z0"], s["z1"], s["holes"], s["top"] )
for w in walls:
    if not w["outward"]:
        continue
    axis, run, across = w["axis"], w["run"], w["across"]
    sign = 1 if w["outward"][0] == "+" else -1
    outer = max( across ) if sign > 0 else min( across )
    inner = min( across ) if sign > 0 else max( across )
    storeys = [ f for f in ( 0, C.FLOOR1 ) if w["z0"] - 1 <= f < w["z1"] - 4 ] if w["z1"] >= 350 else [ w["z0"] ]
    out_floor = { f: list( QG.floored( axis, tuple( run ), outer + sign * 8, f, slabs ) ) for f in storeys }
    in_floor = { f: list( QG.floored( axis, tuple( run ), inner - sign * 8, f, slabs ) ) for f in storeys }
    print( f"{axis} run {run} across {across} {w['outward']} z {w['z0']}-{w['z1']} storeys {storeys}" )
    for f in storeys:
        cov_out = sum( b - a for a, b in out_floor[f] )
        cov_in = sum( b - a for a, b in in_floor[f] )
        L = run[1] - run[0]
        flag = "" if f < 1 else ( "  <-- outside band with no floor outside" if cov_out < L - 4 else "" )
        print( f"    floor {f}: outside floored {cov_out:.0f}/{L:.0f}, inside floored {cov_in:.0f}/{L:.0f}{flag}" )

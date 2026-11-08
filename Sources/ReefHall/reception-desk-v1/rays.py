"""Collision check for the lobby reception desk: the same rays before and after the install must hit the same things.

    python rays.py before|after       writes rays_<label>.json next to this file
    python rays.py compare            before vs after: every ray must give the same hit, position and distance

The rays go through the Reef Hall scene's own physics world (scene.Trace, the open editor document, no play session, no
camera move, nothing changed). Plan coordinates are (e, n) from the lobby tank at (-2420, 0); world = (n, -e, z).
Down rays land on the desk top (z 42), level rays at 20 in meet its two faces and its ends, and level rays at monitor
height (z 55) pass through the old and the new desk alike: neither draws collision there, only the sixteen wedges do.
"""
import json
import math
import sys
from pathlib import Path

import editor as eh

HERE = Path(__file__).resolve().parent
TANK = (-2420.0, 0.0)


def world(a_deg, r, z):
    a = math.radians(a_deg)
    e, n = TANK[0] + r * math.cos(a), TANK[1] + r * math.sin(a)
    return (n, -e, z)


def rays():
    out = []
    for a in (-55, -45, -20, 0, 20, 45, 55):
        out.append((f"down a={a} r=231", world(a, 231, 120), world(a, 231, -5)))
        out.append((f"down a={a} r=216", world(a, 216, 120), world(a, 216, -5)))
        out.append((f"down a={a} r=246", world(a, 246, 120), world(a, 246, -5)))
        out.append((f"public face a={a} z=20", world(a, 330, 20), world(a, 180, 20)))
        out.append((f"staff face a={a} z=20", world(a, 170, 20), world(a, 330, 20)))
        out.append((f"public face a={a} z=60", world(a, 330, 60), world(a, 180, 60)))
        out.append((f"monitor height a={a} z=55", world(a, 330, 55), world(a, 140, 55)))
    for a in (-32, 0, 32):
        out.append((f"through monitor a={a} z=52", world(a, 300, 52), world(a, 150, 52)))
        out.append((f"down through monitor a={a} r=232", world(a, 232, 120), world(a, 232, -5)))
    for end in (-62, 62):
        for r in (216, 231, 246):
            out.append((f"end a={end} r={r} z=20", world(end + (40 if end > 0 else -40), r, 20), world(end - (10 if end > 0 else -10), r, 20)))
    return out


def csharp(items):
    rows = ",\n".join(f'( "{n}", new Vector3( {a[0]:.3f}f, {a[1]:.3f}f, {a[2]:.3f}f ), new Vector3( {b[0]:.3f}f, {b[1]:.3f}f, {b[2]:.3f}f ) )' for n, a, b in items)
    return f'''var s = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( s == null ) return "reefhall is not open";
var items = new (string, Vector3, Vector3)[] {{
{rows} }};
var rows = new System.Collections.Generic.List<object>();
foreach ( var (name, a, b) in items )
{{
    var t = s.Scene.Trace.Ray( a, b ).Run();
    rows.Add( new {{ name, hit = t.Hit, x = t.Hit ? Math.Round( t.HitPosition.x, 2 ) : 0.0, y = t.Hit ? Math.Round( t.HitPosition.y, 2 ) : 0.0,
                    z = t.Hit ? Math.Round( t.HitPosition.z, 2 ) : 0.0, d = t.Hit ? Math.Round( t.Distance, 2 ) : 0.0,
                    obj = t.Hit ? t.GameObject?.Name : null }} );
}}
return rows;
'''


def run(label):
    result = eh.run(csharp(rays()), timeout=240)
    if isinstance(result, str):
        raise SystemExit(result)
    (HERE / f"rays_{label}.json").write_text(json.dumps(result, indent=1))
    hits = sum(1 for r in result if r["hit"])
    print(f"{len(result)} rays, {hits} hit -> rays_{label}.json")
    for r in result[:6]:
        print("  ", r)
    return result


def compare():
    a = json.loads((HERE / "rays_before.json").read_text())
    b = json.loads((HERE / "rays_after.json").read_text())
    assert len(a) == len(b), (len(a), len(b))
    bad = [(x, y) for x, y in zip(a, b) if x != y]
    print(f"{len(a)} rays: {len(a) - len(bad)} identical, {len(bad)} different")
    for x, y in bad[:12]:
        print("  before", x, "\n  after ", y)
    return 0 if not bad else 1


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "compare":
        raise SystemExit(compare())
    run(cmd)

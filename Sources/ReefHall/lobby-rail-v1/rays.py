"""Collision check for the lobby balcony railing: the same rays before and after the install must hit the same things.

    python rays.py before|after|reverted   writes rays_<label>.json next to this file
    python rays.py compare [a b]           two labelled sets (default before after): every ray must give the same hit,
                                           position, distance and object

The rays go through the Reef Hall scene's own physics world (scene.Trace on the open editor document: no play session, no
camera move, nothing changed). Plan coordinates are (e, n); world = (n, -e, z). The railing runs along n = +/-822 from
e -2720 to -1880 on the balcony floor (z 208): the generator's collision-only boxes (a 3 in base to z 212, a 1 in glass
strip to z 246, a 3.2 in handrail box to z 251.6) are the same with the original drawing and with the new sections, so
level rays at base, glass and handrail height, rays at post and mid-bay stations, rays straight down onto the handrail and
rays along the run must all come out exactly alike.
"""
import json
import sys
from pathlib import Path

import editor as eh

HERE = Path(__file__).resolve().parent
E0, E1, N, Z = -2720.0, -1880.0, 822.0, 208.0


def world(e, n, z):
    return (n, -e, z)


def rays():
    out = []
    stations = [E1 - 30 * k for k in range(0, 29)]                        # posts (every 60) and mid-bays, 28 bays of 30
    stations += [E1 - 5, E1 - 55, E0 + 5, E0 + 55]                        # beside the first and last posts
    for side, n in (("N", N), ("S", -N)):
        s = 1 if n > 0 else -1
        for e in stations:
            for z, label in ((2, "base"), (20, "glass"), (41, "handrail")):
                out.append((f"{side} level {label} e={e:g}", world(e, n + 18 * s, Z + z), world(e, n - 18 * s, Z + z)))
            out.append((f"{side} level wide e={e:g}", world(e, n - 18 * s, Z + 20), world(e, n + 18 * s, Z + 20)))
        for e in (E1 - 60, E1 - 360, E1 - 600, E0 + 60):
            for dn in (0.0, 0.7, 1.2, 1.55, 2.0):
                out.append((f"{side} down dn={dn} e={e:g}", world(e, n + dn * s, Z + 60), world(e, n + dn * s, Z - 5)))
        out.append((f"{side} along z=20 from east", world(E1 + 30, n, Z + 20), world(E0 - 30, n, Z + 20)))
        out.append((f"{side} along z=20 from west", world(E0 - 30, n, Z + 20), world(E1 + 30, n, Z + 20)))
        out.append((f"{side} along z=45 from east", world(E1 + 30, n, Z + 45), world(E0 - 30, n, Z + 45)))
        out.append((f"{side} diagonal glass", world(E1 - 200, n + 30 * s, Z + 25), world(E1 - 260, n - 30 * s, Z + 12)))
        out.append((f"{side} diagonal rail", world(E1 - 200, n + 30 * s, Z + 70), world(E1 - 220, n - 30 * s, Z + 30)))
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
    result = eh.script(csharp(rays()), f"rays-{label}.cs")
    if isinstance(result, str):
        raise SystemExit(result)
    (HERE / f"rays_{label}.json").write_text(json.dumps(result, indent=1))
    hits = sum(1 for r in result if r["hit"])
    kinds = {}
    for r in result:
        if r["hit"]:
            kinds[r["obj"]] = kinds.get(r["obj"], 0) + 1
    print(f"{len(result)} rays, {hits} hit -> rays_{label}.json | hit objects: {kinds}")
    for r in result[:4]:
        print("  ", r)
    return result


def compare(la="before", lb="after"):
    a = json.loads((HERE / f"rays_{la}.json").read_text())
    b = json.loads((HERE / f"rays_{lb}.json").read_text())
    assert len(a) == len(b), (len(a), len(b))
    bad = [(x, y) for x, y in zip(a, b) if x != y]
    print(f"{la} vs {lb}: {len(a)} rays: {len(a) - len(bad)} identical, {len(bad)} different")
    for x, y in bad[:12]:
        print(f"  {la}", x, f"\n  {lb}", y)
    return 0 if not bad else 1


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "compare":
        raise SystemExit(compare(*sys.argv[2:4]))
    run(cmd)

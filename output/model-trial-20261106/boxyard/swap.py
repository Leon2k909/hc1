"""Swap the Boxyard wall between its two states while holding output/editor-lock (boxyard-model session):

    python swap.py status      # instances, yard model bounds, front tab (read-only)
    python swap.py revert      # revert.py (old wall back in the yard model, group out of the scene) + reload the Boxyard tab
    python swap.py install     # install.py (new wall) + reload the Boxyard tab

Reload = SceneEditorSession.Reload() on the Boxyard tab (it re-reads the scene file; nothing is saved from the editor).
"""
import json, subprocess, sys, time
from pathlib import Path
import ed

ROOT = Path(r"C:\sbox-projects\hc1\forked-shooter-main")
SRC = ROOT / "Sources/Boxyard/perimeter-wall-v1"

STATUS = '''
var sessions = Editor.SceneEditorSession.All.Select( s => s.Scene?.Name + (s == Editor.SceneEditorSession.Active ? "*" : "") ).ToList();
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
int perimeter = 0, yardRenderers = 0, groups = 0, withLod = 0;
using ( s.Scene.Push() )
{
    foreach ( var go in s.Scene.GetAllObjects( true ) ) if ( go.Name == "Perimeter Wall" ) groups++;
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {
        var path = r.Model?.ResourcePath ?? "";
        if ( path.Contains( "perimeter_wall_v1" ) ) { perimeter++; if ( r.LodOverride != null ) withLod++; }
        if ( path.EndsWith( "boxyard_yard.vmdl" ) ) yardRenderers++;
    }
}
var yard = Model.Load( "models/maps/boxyard/boxyard_yard.vmdl" );
return new { Sessions = sessions, groups, perimeter, withLod, yardRenderers, Yard = new { yard.IsError, Bounds = yard.Bounds.ToString() }, s.HasUnsavedChanges, Playing = Game.IsPlaying };
'''

RELOAD = '''
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var before = s.HasUnsavedChanges;
s.Reload();
await Task.Delay( 3500 );
var s2 = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
return new { before, same = object.ReferenceEquals( s, s2 ), s2.HasUnsavedChanges, Active = Editor.SceneEditorSession.Active?.Scene.Name };
'''


def status():
    return ed.script(STATUS, "swap-status.cs")


def run(script):
    r = subprocess.run([sys.executable, str(SRC / script)], capture_output=True, text=True, encoding="utf-8",
                       env={**__import__("os").environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"})
    print(script, "exit", r.returncode)
    print(r.stdout[-1500:], r.stderr[-800:])
    if r.returncode:
        raise SystemExit(f"{script} failed")


def swap(script, expect_group):
    print("before", json.dumps(status()))
    run(script)
    print("reload", json.dumps(ed.script(RELOAD, "swap-reload.cs")))
    for i in range(24):
        st = status()
        print("status", i, json.dumps(st))
        res = st.get("result", st)
        try:
            # the yard model's own bounds tell which compiled version is live: floor only (z top ~0) or with the old wall (z top > 100)
            top = float(res["Yard"]["Bounds"].split("maxs")[1].split(",")[2])
        except Exception:
            top = None
        bounds_ok = top is not None and ((top < 1.0) if expect_group else (top > 100.0))
        if (res.get("groups") == (1 if expect_group else 0) and res.get("perimeter") == (56 if expect_group else 0)
                and not res["Yard"]["IsError"] and bounds_ok):
            return st
        time.sleep(4)
    raise SystemExit("the scene did not reach the expected state")


if __name__ == "__main__":
    a = sys.argv[1]
    if a == "status":
        print(json.dumps(status(), indent=1))
    elif a == "revert":
        swap("revert.py", False)
    elif a == "install":
        swap("install.py", True)

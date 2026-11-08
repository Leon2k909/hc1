"""Editor helpers for the Boxyard model trial (boxyard-model session). Talks to the shared s&box editor through
`sbox-cli --call <tool> <json>`. Only used while holding output/editor-lock.

    python ed.py info                      # sessions, active scene, each session's viewport camera
    python ed.py front <scene name>        # BringToFront (scene must already be open as a tab)
    python ed.py cam x y z pitch yaw [fov] # pose the Boxyard tab's REAL viewport camera (SceneViewportWidget.State)
    python ed.py shot <out.png> [x y w h]  # screenshot_game (PrintWindow of the editor window), optional crop

The viewport camera is the `State` (CameraPosition / CameraRotation) of the tab's SceneViewportWidget; the scene's
`editor_camera` object only mirrors it (writing to it is undone on the next frame).
"""
import json, os, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(r"C:\sbox-projects\hc1\forked-shooter-main")
ENGINE = Path(os.environ.get("FACEPUNCH_ENGINE") or r"C:\Program Files (x86)\Steam\steamapps\common\sbox")
CLI = ENGINE / "bin/managed/sbox-cli.exe"
SNIP = ROOT / "output/model-trial-20261106/boxyard/snippets"
SNIP.mkdir(parents=True, exist_ok=True)


def call(tool, arguments=None, timeout=240):
    r = subprocess.run([str(CLI), "--call", tool, json.dumps(arguments or {})], cwd=ROOT, capture_output=True, text=True,
                       encoding="utf-8", timeout=timeout)
    text = (r.stdout or "").strip()
    try:
        return json.loads(text)
    except ValueError:
        return {"_text": text, "_err": (r.stderr or "").strip(), "_code": r.returncode}


def script(code, name):
    path = SNIP / name
    path.write_text(code, encoding="utf-8")
    return call("run_csharp", dict(path=str(path)))


INFO = '''
var sessions = Editor.SceneEditorSession.All.Select( s => new {
    Name = s.Scene?.Name, Active = s == Editor.SceneEditorSession.Active, Path = s.Scene?.Source?.ResourcePath,
    Cam = ( s.Scene?.GetAllComponents<CameraComponent>().FirstOrDefault( c => c.GameObject.Name == "editor_camera" ) ?? s.Scene?.Camera ) is CameraComponent c
        ? new { Obj = c.GameObject.Name, Pos = c.WorldPosition.ToString(), Ang = c.WorldRotation.Angles().ToString(), Fov = c.FieldOfView, Axis = c.FovAxis.ToString() } : null } ).ToList();
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, Playing = Game.IsPlaying, Sessions = sessions };
'''


def info():
    return script(INFO, "info.cs")


FRONT = '''
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "{scene}" );
var before = Editor.SceneEditorSession.Active?.Scene.Name;
s.BringToFront();
await Task.Delay( 900 );
return new {{ before, after = Editor.SceneEditorSession.Active?.Scene.Name }};
'''


def front(scene):
    return script(FRONT.format(scene=scene), f"front-{scene}.cs")


CAM = '''
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "{scene}" );
var wasActive = Editor.SceneEditorSession.Active?.Scene.Name;
if ( Editor.SceneEditorSession.Active != s ) {{ s.BringToFront(); await Task.Delay( 900 ); }}
var view = Editor.SceneViewWidget.Current;
if ( view == null || view.Session != s ) return new {{ error = "front view is not " + "{scene}", FrontView = view?.Session?.Scene?.Name, WasActive = wasActive }};
var vp = view.LastSelectedViewportWidget;
var before = new {{ Pos = vp.State.CameraPosition.ToString(), Ang = vp.State.CameraRotation.Angles().ToString() }};
vp.State.CameraPosition = new Vector3( {x}f, {y}f, {z}f );
vp.State.CameraRotation = Rotation.From( {pitch}f, {yaw}f, 0f );
{fov}
await Task.Delay( {settle} );
var cam = s.Scene.GetAllComponents<CameraComponent>().First( c => c.GameObject.Name == "editor_camera" );
return new {{ Scene = s.Scene.Name, WasActive = wasActive, Active = Editor.SceneEditorSession.Active?.Scene.Name, Before = before,
    State = new {{ Pos = vp.State.CameraPosition.ToString(), Ang = vp.State.CameraRotation.Angles().ToString(), Size = vp.Size.ToString() }},
    EditorCam = new {{ Pos = cam.WorldPosition.ToString(), Ang = cam.WorldRotation.Angles().ToString(), Fov = cam.FieldOfView }} }};
'''


def cam(x, y, z, pitch, yaw, fov=None, scene="boxyard", settle=600):
    f = f"vp.TargetFOV = {fov}f;" if fov else ""
    return script(CAM.format(scene=scene, x=x, y=y, z=z, pitch=pitch, yaw=yaw, fov=f, settle=settle), "cam.cs")


STATE = '''
var view = Editor.SceneViewWidget.Current;
var vp = view?.LastSelectedViewportWidget;
return new { Active = Editor.SceneEditorSession.Active?.Scene.Name, FrontView = view?.Session?.Scene?.Name,
    Pos = vp?.State.CameraPosition.ToString(), Ang = vp?.State.CameraRotation.Angles().ToString(), Size = vp?.Size.ToString() };
'''


def state():
    """ Read-only: which tab is in front and where its viewport camera is right now. """
    return script(STATE, "state.cs")


def shot(out, crop=None):
    args = {"command": "screenshot_game"}
    if crop:
        args["parameters"] = {"crop": {"x": crop[0], "y": crop[1], "w": crop[2], "h": crop[3]}}
    r = call("bridge_call", args)
    # The handler writes bridge_window_*.png to the temp folder; the result may be nested under "result".
    path = None
    node = r
    for _ in range(3):
        if isinstance(node, dict) and "path" in node:
            path = node["path"]
            break
        node = node.get("result") if isinstance(node, dict) else None
    if path and out:
        Path(out).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, out)
        r["saved"] = str(out)
    return r


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "info":
        print(json.dumps(info(), indent=1))
    elif a[0] == "front":
        print(front(a[1]))
    elif a[0] == "cam":
        v = [float(t) for t in a[1:]]
        print(cam(*v))
    elif a[0] == "shot":
        print(shot(a[1], [float(t) for t in a[2:6]] if len(a) >= 6 else None))

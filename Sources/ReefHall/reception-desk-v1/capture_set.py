"""Native BEFORE / AFTER captures of the Reef Hall reception desk, from the real editor viewport (no temporary cameras,
scenes or offscreen renders).

    python capture_set.py before|after [pose ...]       (poses from poses.json; default: all)

Takes the shared editor lock (output/editor-lock), opens Reef Hall if it is not loaded, brings it to the front, moves the
editor camera with the editor's own set_editor_camera, captures the viewport (PrintWindow of the editor window, cropped to
the viewport), then puts the previous front scene back and releases the lock. Pictures go to
output/model-trial-20261106/reefhall/<label>[_far|_staff].png; what the editor reported goes to captures_<label>.json.
"""
import json
import math
import os
import sys
import time
from pathlib import Path

import editor as eh

HERE = Path(__file__).resolve().parent
POSES = { k: v for k, v in json.loads((HERE / "poses.json").read_text()).items() if not k.startswith("_") }


# The new desk's textures are requested at up to 2048 px before an AFTER picture, so the first frames do not show low mips
# (never MarkUsed(4096) on a whole map: that ran the shared editor out of video memory). Only this model's materials.
STREAM = r'''var s = Editor.SceneEditorSession.All.FirstOrDefault( x => x.Scene.Name == "reefhall" );
if ( s == null ) return "reefhall is not open";
var names = new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "g_tMetalness", "g_tTintMask", "g_tSelfIllumMask" };
var renderers = s.Scene.GetAllComponents<ModelRenderer>().Where( r => r.Model != null && r.Model.ResourcePath == "models/props/reefhall/reception_desk_v1/reception_desk.vmdl" ).ToArray();
var textures = renderers.SelectMany( r => r.Model.Materials ).SelectMany( m => names.Select( n => m.GetTexture( n ) ).Append( m.FirstTexture ) ).Where( t => t != null ).Distinct().ToArray();
foreach ( var t in textures ) t.MarkUsed( 2048 );
return new { Renderers = renderers.Length, Textures = textures.Length, Sizes = textures.Select( t => t.Width + "x" + t.Height ).Distinct().ToArray() };
'''


def world(p):
    return (p[1], -p[0], p[2])


def look(eye, target):
    """ plan eye / target (e, n, z) -> world position and (pitch, yaw, roll); a positive pitch looks down """
    a, b = world(eye), world(target)
    d = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    yaw = math.degrees(math.atan2(d[1], d[0]))
    pitch = -math.degrees(math.atan2(d[2], math.hypot(d[0], d[1])))
    return a, (round(pitch, 2), round(yaw, 2), 0.0)


def shoot(dest, pos, ang, rect):
    """ The front scene can change under us (another session): check before and after, retake if it did. """
    for _ in range(5):
        if eh.status()["ActiveScene"] != eh.SCENE_NAME:
            print("front scene is", eh.status()["ActiveScene"], "- bringing", eh.SCENE_NAME, "back", flush=True)
            eh.front(eh.SCENE_NAME)
            time.sleep(3)
            continue
        r = eh.set_camera(eh.SCENE_NAME, pos, ang, settle=2500)
        if r["active"] != eh.SCENE_NAME:
            continue
        eh.capture(dest, rect)
        if eh.status()["ActiveScene"] == eh.SCENE_NAME:
            return r
    raise RuntimeError("could not capture " + str(dest))


def main(label, names):
    if not eh.acquire(wait=int(os.environ.get("REEFHALL_LOCK_WAIT", "900"))):
        raise SystemExit("could not get the editor lock")
    st = eh.status()
    home = st["ActiveScene"]
    print("home scene:", home, "| playing:", st["IsPlaying"], flush=True)
    assert not st["IsPlaying"]
    log = {"label": label, "home": home, "poses": {}}
    try:
        sess = eh.sessions()
        if eh.SCENE_NAME not in sess:
            print("opening", eh.SCENE_PATH, flush=True)
            eh.open_scene()
            for _ in range(60):
                time.sleep(3)
                if eh.SCENE_NAME in eh.sessions():
                    break
            time.sleep(10)
        eh.front(eh.SCENE_NAME)
        time.sleep(4)
        rect = eh.viewport_rect(eh.SCENE_NAME)
        log["rect"] = rect
        print("viewport rect", rect, flush=True)
        log["camera_before"] = eh.camera()          # Reef Hall's own viewport camera, put back at the end
        print("viewport camera on arrival:", log["camera_before"], flush=True)
        if label != "before":
            first = HERE / "captures_before.json"
            if first.exists():
                want = json.loads(first.read_text()).get("rect")
                log["rect_matches_before"] = (list(map(round, want)) == list(map(round, rect))) if want else None
                print("viewport rect same as BEFORE:", log["rect_matches_before"], "(BEFORE", want, ")", flush=True)
            print("streaming:", eh.script(STREAM, "stream-desk-textures.cs"), flush=True)
            time.sleep(10)
        for name in names:
            pose = POSES[name]
            if label == "after":
                eh.script(STREAM, "stream-desk-textures.cs")
            pos, ang = look(pose["eye"], pose["target"])
            dest = eh.OUT / f"{label}{pose['file']}.png"
            r = shoot(dest, pos, ang, rect)
            log["poses"][name] = {"world_pos": pos, "angles": ang, "editor": r["got"], "file": str(dest)}
            print(name, "->", dest.name, r["got"], flush=True)
    finally:
        try:
            cam = log.get("camera_before")
            if isinstance(cam, dict) and cam.get("Position"):
                if eh.status()["ActiveScene"] == eh.SCENE_NAME:
                    eh.set_camera(eh.SCENE_NAME, cam["Position"].split(","), cam["Angles"].split(","), settle=500)
                    log["camera_restored"] = eh.camera()
                    print("viewport camera put back:", log["camera_restored"], flush=True)
            back = eh.front(home)
            print("front scene restored:", back, "| expected", home, flush=True)
            log["restored_front"] = back
        except Exception as ex:  # noqa: BLE001 - whatever happens, write the log and let go of the lock
            print("could not put the viewport camera / front scene back:", ex, flush=True)
            log["restore_error"] = str(ex)
        finally:
            (HERE / f"captures_{label}.json").write_text(json.dumps(log, indent=1, default=str))
            eh.release()


if __name__ == "__main__":
    label = sys.argv[1]
    main(label, sys.argv[2:] or list(POSES))

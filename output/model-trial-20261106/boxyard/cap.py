"""Boxyard before/after capture helper (boxyard-model session). Native editor viewport only:
  - the Boxyard tab's SceneViewportWidget.State is posed (the real viewport camera),
  - the whole editor window is captured with the bridge's screenshot_game (PrintWindow), nothing else is rendered,
  - the capture is kept only when the Hierarchy root label reads "boxyard" (other sessions flip the front tab),
  - the viewport area is cropped out of the window capture.

    python cap.py stream                    # MarkUsed the Boxyard map/prop textures (wall ones at 2048, the rest 1024)
    python cap.py shots before              # before / before_far / before_lane into this folder
    python cap.py shots after
"""
import json, re, sys, time
from pathlib import Path
from PIL import Image, ImageChops
import ed

HERE = Path(__file__).parent
VIEW_CROP = (428, 100, 428 + 1102, 100 + 713)       # the viewport inside the 1920 x 1032 editor window
TITLE_BOX = (62, 106, 140, 126)      # the Hierarchy panel's root label follows the active tab (the window title lags)
POSES = {
    # name: (x, y, z, pitch, yaw) in engine units (x = plan north, y = -plan east), fov = the viewport's 80
    "close":   (690, -430, 64, 6, 32),     # about 3.6 m from the north wall, a post and its two planks centred (site A side)
    "far":     (352, -401, 64, 4, 12),     # about 12 m back from the same wall bay (clear of the spawn gizmos)
    "lane":    (700, 700, 64, 0, -80),     # the north lane, looking down it with the north wall on the left (grazing view)
}

STREAM = '''
var s = Editor.SceneEditorSession.All.First( x => x.Scene.Name == "boxyard" );
var seen = new System.Collections.Generic.HashSet<string>();
var report = new System.Collections.Generic.List<object>();
using ( s.Scene.Push() )
{
    foreach ( var r in s.Scene.GetAllComponents<ModelRenderer>() )
    {
        var path = r.Model?.ResourcePath ?? "";
        if ( !path.Contains( "models/maps/boxyard/" ) && !path.Contains( "models/props/boxyard/" ) ) continue;
        for ( int slot = 0; slot < r.Materials.Count; slot++ )
        {
            var m = r.Materials.GetOverride( slot ) ?? r.Materials.GetOriginal( slot );
            if ( m == null || m.IsError || !seen.Add( m.ResourcePath ?? m.Name ) ) continue;
            int size = ( m.Name ?? m.ResourcePath ?? "" ).Contains( "wall" ) || ( m.ResourcePath ?? "" ).Contains( "bx_concrete" ) || ( m.ResourcePath ?? "" ).Contains( "steel" ) || ( m.ResourcePath ?? "" ).Contains( "galv" ) ? 2048 : 1024;
            var sizes = new System.Collections.Generic.List<string>();
            foreach ( var key in new[] { "g_tColor", "g_tNormal", "g_tRma" } )
            {
                var t = m.GetTexture( key );
                if ( t == null ) continue;
                t.MarkUsed( size );
                sizes.Add( key + ":" + t.Width + "x" + t.Height );
            }
            report.Add( new { Material = m.ResourcePath ?? m.Name, Requested = size, Textures = sizes } );
        }
    }
}
await Task.Delay( 2500 );
return new { Count = report.Count, Active = Editor.SceneEditorSession.Active?.Scene.Name, report };
'''


def stream():
    return ed.script(STREAM, "stream.cs")


def title_ok(img):
    ref = Image.open(HERE / "hier_ref_boxyard.png").convert("RGB")
    cur = img.convert("RGB").crop(TITLE_BOX)
    diff = ImageChops.difference(ref, cur)
    px = list(diff.getdata())
    mean = sum(sum(p) for p in px) / (3 * len(px))
    return mean < 4.0, mean


def _nums(t):
    return [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", t or "")]


def pose_ok(st, pose, tol=0.06):
    """ The viewport camera is where it was told to be (other sessions and the user can move it under us). """
    try:
        p, a = _nums(st["Pos"]), _nums(st["Ang"])
        return (all(abs(p[i] - pose[i]) < tol for i in range(3)) and abs(a[0] - pose[3]) < tol and abs(a[1] - pose[4]) < tol)
    except Exception:
        return False


def capture(name, pose, tries=6, settle=900):
    x, y, z, pitch, yaw = pose
    for attempt in range(1, tries + 1):
        r = ed.cam(x, y, z, pitch, yaw, settle=settle)
        if r.get("error"):
            print("  cam error", r.get("error"), r.get("FrontView"))
            time.sleep(1.0)
            continue
        if not pose_ok(r.get("State", {}), pose):
            print("  camera was moved under us before the shot:", r.get("State"), "retry")
            time.sleep(0.5)
            continue
        raw = HERE / "raw" / f"{name}.png"
        s = ed.shot(str(raw))
        if not raw.exists():
            print("  no capture", s)
            continue
        after = ed.state()
        if after.get("FrontView") != "boxyard" or not pose_ok(after, pose):
            print("  camera or tab changed during the shot:", after, "retry")
            continue
        im = Image.open(raw)
        ok, mean = title_ok(im)
        if ok:
            out = HERE / f"{name}.png"
            # the viewport's size follows the editor's dock layout (the Asset Browser dock's height changes): crop what it is now
            try:
                vw, vh = (float(t) for t in r["State"]["Size"].split(","))
            except Exception:
                vw, vh = VIEW_CROP[2] - VIEW_CROP[0], VIEW_CROP[3] - VIEW_CROP[1]
            crop = (VIEW_CROP[0], VIEW_CROP[1], VIEW_CROP[0] + (VIEW_CROP[2] - VIEW_CROP[0]), VIEW_CROP[1] + int(round(vh)))
            im.convert("RGB").crop(crop).save(out)
            print(f"  {name}: ok on attempt {attempt}; state {r.get('State')}; crop {crop}; title diff {mean:.2f}")
            return out
        print(f"  {name}: front tab was not boxyard (title diff {mean:.1f}), retry")
    raise SystemExit(f"could not capture {name}")


def shots(prefix, which=None):
    for key, pose in POSES.items():
        if which and key not in which:
            continue
        suffix = {"close": "", "far": "_far", "lane": "_lane"}[key]
        capture(f"{prefix}{suffix}", pose)


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[0] == "stream":
        print(json.dumps(stream(), indent=0)[:3000])
    elif a[0] == "shots":
        shots(a[1], a[2:] or None)
    elif a[0] == "one":
        pose = tuple(float(t) for t in a[2:7])
        capture(a[1], pose)

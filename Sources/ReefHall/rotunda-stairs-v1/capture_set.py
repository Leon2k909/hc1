"""Native BEFORE / AFTER captures of Reef Hall's straight stairs, from the real editor viewport (no temporary cameras,
scenes or offscreen renders). Reuses the lobby-rail trial's editor helpers (Sources/ReefHall/lobby-rail-v1/editor.py).

    python capture_set.py before|after|reverted [pose ...]       (poses from poses.json; default: all)

Takes the shared editor lock (output/editor-lock), opens Reef Hall if it is not loaded, brings it to the front, moves the
editor camera with the editor's own set_editor_camera, captures the viewport (PrintWindow of the editor window, cropped to
the viewport), then puts the previous front scene back and releases the lock. Pictures go to
output/model-trial-20261106/reefhall_rotunda_stairs/<label>_<pose>.png; what the editor reported goes to captures_<label>.json.
The stairs use only materials the lobby and control room already show, so no texture-streaming request is made (a
MarkUsed on shared lobby textures changed the floor's look during the rail trial).
"""
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lobby-rail-v1"))
import editor as eh          # noqa: E402
import capture_set as rail   # noqa: E402  (look(), shoot())
sys.path.insert(0, str(HERE))
import window_state as WS    # noqa: E402  (a minimized editor window captures as a black frame)

eh.OUT = eh.ROOT / "output/model-trial-20261106/reefhall_rotunda_stairs"
eh.SNIPPETS = eh.OUT / "snippets"
POSES = { k: v for k, v in json.loads((HERE / "poses.json").read_text()).items() if not k.startswith("_") }


def is_black(path):
    """ A capture of a window that is not presenting frames is all zeros. """
    from PIL import Image
    return Image.open(path).convert("L").getextrema()[1] == 0


def main(label, names):
    if not eh.acquire(wait=int(os.environ.get("REEFHALL_LOCK_WAIT", "900"))):
        raise SystemExit("could not get the editor lock")
    st = eh.status()
    home = st["ActiveScene"]
    print("home scene:", home, "| playing:", st["IsPlaying"], flush=True)
    assert not st["IsPlaying"]
    log = {"label": label, "home": home, "poses": {}}
    minimized_handle = None
    try:
        minimized_handle = WS.ensure_drawing()
        log["editor_window_was_minimized"] = bool(minimized_handle)
        print("editor window:", WS.state(), "| it was minimized, restored without activation:" if minimized_handle else "| left as it is", flush=True)
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
        for name in names:
            pose = POSES[name]
            pos, ang = rail.look(pose["eye"], pose["target"])
            dest = eh.OUT / f"{label}_{name}.png"
            r = rail.shoot(dest, pos, ang, rect)
            for attempt in range(3):
                if not is_black(dest):
                    break
                print(name, "came back black (the editor window is not drawing); waiting and retaking", flush=True)
                time.sleep(4)
                r = rail.shoot(dest, pos, ang, rect)
            else:
                if is_black(dest):
                    raise RuntimeError(f"{dest.name} is still all black: the editor window is not presenting frames")
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
            if minimized_handle:
                WS.minimize_again(minimized_handle)        # as found
                print("editor window minimized again, as it was found", flush=True)
            (HERE / f"captures_{label}.json").write_text(json.dumps(log, indent=1, default=str))
            eh.release()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or list(POSES))

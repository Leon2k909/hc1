"""Survey of Boxyard's main routes from the real editor viewport (2026-11-06): which props look crude, close up, at eye level?
World coordinates (Boxyard has no plan frame): poses are eye -> target. Takes the shared editor lock, opens Boxyard if needed,
captures the viewport, puts the viewport camera and the front scene back, releases the lock.
"""
import json
import math
import sys
from pathlib import Path

ROOT = Path(r"C:\sbox-projects\hc1\forked-shooter-main")
RH = ROOT / "Sources/ReefHall"
sys.path.insert(0, str(RH / "office-partitions-v1"))
sys.path.insert(0, str(RH / "lobby-rail-v1"))
import editor as eh          # noqa: E402
import capture_set as cs     # noqa: E402
import window_state as WS    # noqa: E402

eh.SCENE_NAME = "boxyard"
eh.SCENE_PATH = "scenes/maps/Boxyard/boxyard.scene"
HERE = Path(__file__).resolve().parent
OUT = ROOT / "output/model-trial-20261106/boxyard_openbox/probe"
POSES = {k: v for k, v in json.loads((HERE / "poses_oc.json").read_text()).items() if not k.startswith("_")}


def aim(eye, target):
    d = [target[i] - eye[i] for i in range(3)]
    return tuple(eye), (round(-math.degrees(math.atan2(d[2], math.hypot(d[0], d[1]))), 2), round(math.degrees(math.atan2(d[1], d[0])), 2), 0.0)


def main(names):
    log = {"poses": {}}
    handle = None
    with eh.borrowed(scene="boxyard", wait=1500) as home:
        handle = WS.ensure_drawing()
        rect = eh.viewport_rect("boxyard")
        cam0 = eh.camera()
        log.update(home=home, rect=rect, camera_before=cam0)
        print("home scene:", home, "| rect", rect, flush=True)
        try:
            for name in names:
                pos, ang = aim(*POSES[name])
                cs.eh = eh
                r = cs.shoot(OUT / f"{name}.png", pos, ang, rect)
                log["poses"][name] = {"pos": pos, "angles": ang, "editor": r["got"]}
                print(name, "->", r["got"], flush=True)
        finally:
            try:
                if eh.status()["ActiveScene"] == "boxyard" and isinstance(cam0, dict) and cam0.get("Position"):
                    print("camera put back:", eh.set_camera("boxyard", [float(x) for x in cam0["Position"].split(",")],
                          [float(x) for x in cam0["Angles"].split(",")], settle=800), flush=True)
            except Exception as e:  # noqa: BLE001
                print("could not restore the camera:", e)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "survey_log.json").write_text(json.dumps(log, indent=1, default=str))


if __name__ == "__main__":
    main(sys.argv[1:] or list(POSES))

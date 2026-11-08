"""Survey of Reef Hall's main routes from the real editor viewport (2026-11-06): which props look crude, close up, at eye level?

    python survey.py [pose ...]            (poses from poses.json; default: all)

Same rules as the lobby-rail trial: takes the shared editor lock (output/editor-lock), brings Reef Hall to the front, moves
the editor camera with the editor's own set_editor_camera, captures the viewport (native window capture, cropped), puts
the viewport camera and the front scene back, releases the lock. These pictures only shortlist candidates; the evidence
pictures for the chosen prop are taken later with matched poses.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "lobby-rail-v1"))
import editor as eh          # noqa: E402
import capture_set as cs     # noqa: E402

OUT = eh.ROOT / "output/model-trial-20261106/reefhall_survey"
POSES = { k: v for k, v in json.loads((HERE / "poses.json").read_text()).items() if not k.startswith("_") }


def main(names):
    log = { "poses": {} }
    with eh.borrowed(wait=1500) as home:
        log["home"] = home
        rect = eh.viewport_rect(eh.SCENE_NAME)
        cam0 = eh.camera()
        log["rect"], log["camera_before"] = rect, cam0
        print("home scene:", home, "| viewport rect", rect, "| camera", cam0, flush=True)
        try:
            for name in names:
                pose = POSES[name]
                pos, ang = cs.look(pose["eye"], pose["target"])
                r = cs.shoot(OUT / f"{name}.png", pos, ang, rect)
                log["poses"][name] = { "world_pos": pos, "angles": ang, "editor": r["got"] }
                print(name, "->", f"{name}.png", r["got"], flush=True)
        finally:
            try:
                if eh.status()["ActiveScene"] == eh.SCENE_NAME and isinstance(cam0, dict) and cam0.get("Position"):
                    eh.set_camera(eh.SCENE_NAME, cam0["Position"].split(","), cam0["Angles"].split(","), settle=500)
                    log["camera_restored"] = eh.camera()
                    print("viewport camera put back:", log["camera_restored"], flush=True)
            except Exception as ex:  # noqa: BLE001 - always let go of the lock
                print("could not put the viewport camera back:", ex, flush=True)
                log["restore_error"] = str(ex)
            (HERE / "survey_log.json").write_text(json.dumps(log, indent=1, default=str))
    print("done; front scene restored to", home, flush=True)


if __name__ == "__main__":
    main(sys.argv[1:] or list(POSES))

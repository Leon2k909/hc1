"""Generate Riverdale's pipe/prop collision groups without rebuilding the expensive backdrop.

    python Tools/riverdale_collision_scene.py

Never rewrites Assets. Reads original scene, runs gameplay geometry only, then replaces/creates
the two independently named collider groups and writes output/riverdale/aaa/collision-scene.scene.
"""
import json
from pathlib import Path
import map_kit as K
import riverdale_map as R
import riverdale_backdrop as BD


def main():
    from riverdale_map import P, H
    root = K.ROOT
    original = root / "Assets/scenes/maps/Riverdale/riverdale.scene"
    output = root / "output/riverdale/aaa/collision-scene.scene"
    # Expensive far-field mountains and forests are independent of all player-facing colliders.
    BD.build = lambda: (K.Model(), K.Model())
    BD.extra_models = lambda: []
    models = R.build()
    assert len(P.PIPE_SOLIDS) > 10, "No pipe collision candidates generated"
    R.SCENE_FILE = root / "output/riverdale/aaa/collision-layout.scene"
    R.write_scene(set(models), H.lights() + list(P.LIGHTS), R.probes())
    proposed = json.loads(R.SCENE_FILE.read_text(encoding="utf-8"))
    saved = json.loads(original.read_text(encoding="utf-8"))
    keys = ("Pipe Solids", "Yard Prop Solids")
    new_groups = [o for o in proposed["GameObjects"] if o["Name"] in keys]
    assert len(new_groups) == len(keys)
    saved["GameObjects"] = [o for o in saved["GameObjects"] if o["Name"] not in keys] + new_groups
    count = {o["Name"]: len(o["Children"]) for o in new_groups}
    output.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    print(f"staged {count}, preserved original scene objects and lighting", flush=True)


if __name__ == "__main__":
    main()

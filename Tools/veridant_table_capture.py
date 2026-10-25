"""Tabletop detail captures without changing the saved scene or the editor view."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import map_kit as K

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--view", choices=("top", "angled"), required=True)
    parser.add_argument("--phase", default="after")
    args=parser.parse_args()
    assert args.phase.replace("-", "").isalnum()
    helper=(ROOT/"Sources/Veridant/editor/capture-door-obstruction.cs.txt").read_text()
    helper=helper.replace("output/veridant/door-obstruction/capture-request.json","output/veridant/table-v2/capture-request.json")
    helper=helper.replace("capture-door-obstruction.cs.txt","capture-table-v2.cs.txt")
    helper=helper.replace("// Capture temporary surface/woodland trials in the existing saved Veridant document.","// Capture a bistro table detail in the saved Veridant document.")
    script=ROOT/"Sources/Veridant/editor/capture-table-v2.cs.txt"
    if script.exists():assert script.read_text()==helper
    else:script.write_text(helper)
    if args.view=="top":
        position=(381.2884,-111.7994,204.3893)
        angles=(84.95,156.96,0)
        fov=80
    else:
        position=K.to_world((142,342,192))
        target=K.to_world((110,380,147))
        delta=target-position
        angles=(-math.degrees(math.atan2(delta[2],math.hypot(*delta[:2]))),math.degrees(math.atan2(delta[1],delta[0])),0)
        fov=60
    config={"directory":"table-v2-"+args.phase,"name":args.view,"width":1280,"height":960,
            "position":",".join(map(str,position)),"angles":",".join(map(str,angles)),"fov":fov,
            "exposure":2.2,"settle_ms":0,
            "expected_scene_sha256":hashlib.sha256((ROOT/"Assets/scenes/maps/Veridant/veridant.scene").read_bytes()).hexdigest()}
    (ROOT/"output/veridant/table-v2/capture-request.json").write_text(json.dumps(config,indent=2)+"\n")
    print(json.dumps(config))


if __name__=="__main__":main()

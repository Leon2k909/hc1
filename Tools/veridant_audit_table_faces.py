"""Read all current table-material faces before a UV-only update."""
import json
import math
from pathlib import Path

root=Path(__file__).resolve().parents[1]
manifest=json.loads((root/"output/veridant/table-v2/stage-v2/manifest.json").read_text())
for relative,centres in manifest["placements"].items():
    lines=(root/relative).read_bytes().splitlines()
    vertices=[tuple(map(float,line.split()[1:])) for line in lines if line.startswith(b"v ")]
    paint=None;good=0;bad=[]
    for i,line in enumerate(lines):
        if line.startswith(b"usemtl "):paint=line.split()[1]
        elif line.startswith(b"f ") and paint==b"vr_table_honed":
            pts=[vertices[int(t.split(b"/")[0])-1] for t in line.split()[1:]]
            e,n,z=min(centres,key=lambda row:sum((p[0]+row[0])**2+(p[2]-row[1])**2 for p in pts))
            if all(math.hypot(p[0]+e,p[2]-n)<=15.01 and z+27.99<=p[1]<=z+29.51 for p in pts):good+=1
            else:bad.append((i,pts))
    print(json.dumps({"path":relative,"good":good,"bad":len(bad),"expected":len(centres)*2430,"first_bad":bad[:1]}))

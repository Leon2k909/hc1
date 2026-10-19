"""Check vertical motion in actual native waterfall captures, not shader assumptions."""
from pathlib import Path
import json
import sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/"output/spillway"/(sys.argv[1] if len(sys.argv)>1 else "flow-check")
frames=sorted(OUT.glob("fall-*.png"))
if len(frames)<6:raise SystemExit("Capture at least six native waterfall frames first.")
images=[np.asarray(Image.open(p).convert("RGB"),dtype=np.float32).mean(axis=2) for p in frames]
height,width=images[0].shape
# Central sheet only: avoid fixed spillway concrete, silhouettes and mist edges.
x0,x1=int(width*.40),int(width*.60)
y0,y1=int(height*.39),int(height*.61)
def detail(a):return a-gaussian_filter(a,4)
filtered=[detail(a) for a in images]
matches=[]
for a,b in zip(filtered,filtered[1:]):
    prev=a[y0:y1,x0:x1];prev=prev-prev.mean()
    denom=np.linalg.norm(prev)
    choices=[]
    for dy in range(-100,101):
        cur=b[y0+dy:y1+dy,x0:x1];cur=cur-cur.mean()
        score=float(np.sum(prev*cur)/max(denom*np.linalg.norm(cur),1e-6))
        choices.append((score,dy))
    score,dy=max(choices)
    matches.append({"DownwardPixels":dy,"Correlation":round(score,4)})
reliable=[p for p in matches if p["Correlation"]>.30]
median=float(np.median([p["DownwardPixels"] for p in reliable])) if reliable else None
passed=bool(len(reliable)>=3 and median>1 and sum(p["DownwardPixels"]>0 for p in reliable)/len(reliable)>.75)
result={"Method":"Normalized cross-correlation of consecutive native camera images; image Y increases downward", "Frames":len(frames),"Matches":matches,"MedianDownwardPixels":median,"Passed":passed}
(OUT/"motion-validation.json").write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
if not passed:raise SystemExit("Automatic motion check needs inspection; do not claim a pass.")

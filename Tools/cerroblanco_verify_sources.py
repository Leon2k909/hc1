"""Check geometry compatibility and staged material inputs before import."""
from pathlib import Path
import ast
import hashlib
import json
import os
import platform
import subprocess
platform.machine=lambda:os.environ.get("PROCESSOR_ARCHITECTURE","AMD64")
from PIL import Image
import numpy as np
import cerroblanco_map as C
import cerroblanco_parts as P

ROOT=Path(__file__).resolve().parent.parent


def collision(model):
    def values(value):
        if isinstance(value,np.ndarray):return value.round(7).tolist()
        if isinstance(value,(list,tuple)):return [values(v) for v in value]
        return value
    return hashlib.sha256(json.dumps(values([model.boxes,model.hulls]),sort_keys=True).encode()).hexdigest()


def main():
    before_source=subprocess.run(["rtk","proxy","git","show","HEAD:Tools/cerroblanco_parts.py"],cwd=ROOT,check=True,capture_output=True,text=True,encoding="utf-8").stdout
    wanted={n.name:n for n in ast.parse(before_source).body if isinstance(n,ast.FunctionDef) and n.name in ("picture","hedge_box")}
    original={name:getattr(P,name) for name in wanted}
    after=C.build()
    try:
        for name,node in wanted.items():
            code=compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),"original-cerroblanco-parts","exec")
            exec(code,P.__dict__)
        before=C.build()
    finally:
        for name,fn in original.items():setattr(P,name,fn)
    compatibility={name:{"before":collision(before[name]),"after":collision(after[name]),"props_unchanged":json.dumps(before[name].props,default=lambda a:np.asarray(a).tolist(),sort_keys=True)==json.dumps(after[name].props,default=lambda a:np.asarray(a).tolist(),sort_keys=True)} for name in before}
    assert all(v["before"]==v["after"] and v["props_unchanged"] for v in compatibility.values()),compatibility
    stage=ROOT/"output/cerroblanco/stage"
    images=[]
    for p in sorted(stage.rglob("*.png")):
        with Image.open(p) as im:
            assert im.width & (im.width-1)==0 and im.height & (im.height-1)==0,p
            images.append({"path":p.relative_to(stage).as_posix(),"size":im.size})
    # Confirm explicit picture UVs refer to bounded artwork within each banner.
    art=[]
    for name,model in after.items():
        if name!="cerroblanco_dressing":continue
        for (paint,index),uv in model.polygon_uvs.items():
            if not paint.startswith("cb_banner_"):continue
            if (paint,index) in before[name].polygon_uvs:continue
            assert all(0<=u<=1 and 0<=v<=1 for u,v in uv)
            art.append({"paint":paint,"face":index,"uv":uv})
    assert len(art)==22,len(art)
    report={"collision_compatibility":compatibility,"power_of_two_images":images,"corrected_canvas_uvs":len(art),"result":"pass"}
    (ROOT/"output/cerroblanco/source-validation.json").write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps({"collision_models":len(compatibility),"unchanged_collision":True,"images":len(images),"corrected_canvases":len(art)}))


if __name__=="__main__":main()

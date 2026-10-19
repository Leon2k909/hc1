"""Check the machinery revision against the saved build's collision and sources."""
from pathlib import Path
import hashlib
import importlib.util
import json
import platform
import sys

platform._wmi_query=lambda *a,**k: (_ for _ in ()).throw(OSError("Skip WMI"))
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"Tools"))
import numpy as np
import collider_map as C
import collider_validate as V

OUT=ROOT/"output/collider/art-v3"
STAGE=OUT/"stage"
def digest(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p): return json.loads(p.read_text(encoding="utf-8"))
def default(v): return v.tolist() if hasattr(v,"tolist") else list(v)
def collision_hash(v): return hashlib.sha256(json.dumps(v,default=default,sort_keys=True).encode()).hexdigest()

models=C.build()
collision={name:{"boxes":m.boxes,"hulls":m.hulls} for name,m in models.items()}
assert collision_hash(collision)==collision_hash(read(OUT/"baseline-collision.json")),"Collision differs"
triangles={}
for name,m in models.items():
    count=0
    for polygons in m.polygons.values():
        for points,normal in polygons:
            pts=np.asarray(points)
            assert np.isfinite(pts).all() and np.isfinite(normal).all(),name
            assert np.linalg.norm(normal)>.99,name
            for i in range(1,len(pts)-1):
                assert np.linalg.norm(np.cross(pts[i]-pts[0],pts[i+1]-pts[0]))>1e-8,name
                count+=1
    triangles[name]=count
spec=importlib.util.spec_from_file_location("verify_services",ROOT/"Sources/Collider/verify-services.py")
service=importlib.util.module_from_spec(spec);spec.loader.exec_module(service)
window_rays=service.visible_wall_hits(models)
assert all(p["opaque_hits"]==0 for p in window_rays),window_rays
layout=read(OUT/"layout-validation.json")
assert layout["checked_spots"]==68 and all(layout[k]==0 for k in ("obstructed_or_unsupported","unreachable","exposed_retakes_pairs"))
V.STAGE=STAGE
V.validate(STAGE/"collider.scene.json",OUT/"scene-validation.json")
baseline=read(OUT/"baseline.json")
files=[]
for p in sorted(STAGE.rglob("*")):
    if not p.is_file():continue
    relative=p.relative_to(STAGE).as_posix()
    if not relative.startswith(("models/maps/collider/","materials/collider/")):continue
    target=ROOT/"Assets"/relative
    before=baseline.get("Assets/"+relative)
    after=digest(p)
    assert (digest(target) if target.exists() else None) in (before,after),"Independent asset change: "+relative
    if before==after:continue
    files.append({"path":relative,"before_sha256":before,"sha256":after,"bytes":p.stat().st_size})
for p in (STAGE/"models/maps/collider").glob("*_hulls_*.obj"):
    assert digest(p)==baseline["Assets/"+p.relative_to(STAGE).as_posix()],p.name
for name,_,solid in C.MODELS:
    if not solid:continue
    marker='_class = "PhysicsShapeList"'
    path=f"models/maps/collider/{name}.vmdl"
    before=(OUT/"before/Assets"/path).read_text().partition(marker)
    after=(STAGE/path).read_text().partition(marker)
    assert before[1] and before[2]==after[2],path
assert digest(STAGE/"ui/minimaps/minimap_collider.png")==digest(ROOT/"Assets/ui/minimaps/minimap_collider.png")
report={"revision":"art-v3","stage":"output/collider/art-v3/stage","files":files,
    "triangles":triangles,"collision_identical":True,"physics_definitions_identical":True,
    "collision_sha256":collision_hash(collision),"offline_positions_passed":68,
    "geometry_finite_and_nondegenerate":True,"window_render_rays":window_rays,
    "point_lights":len(C.LIGHTS),"spot_lights":len(C.SPOTLIGHTS),
    "shadow_lights":sum(l[-1] for l in C.LIGHTS)+sum(l[-1] for l in C.SPOTLIGHTS),
    "baseline_scene_sha256":baseline["Assets/scenes/maps/Collider/collider.scene"],
    "source_sha256":{p.relative_to(ROOT).as_posix():digest(p) for p in (ROOT/"Tools").glob("collider_*.py")}}
(OUT/"manifest.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps({k:report[k] for k in ("triangles","collision_identical","physics_definitions_identical","offline_positions_passed","point_lights","spot_lights","shadow_lights")},indent=2))

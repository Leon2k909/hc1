"""Validate the staged service detail against the accepted collision and assets."""
from pathlib import Path
import argparse
import hashlib
import json
import platform
import sys

# SciPy's platform probe can hang in WMI on this workstation.
platform._wmi_query=lambda *a,**k: (_ for _ in ()).throw(OSError("WMI unavailable during this check"))
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"Tools"))
import numpy as np
import collider_map as C
import collider_validate as V

OUT=ROOT/"output/collider/services-v1"
STAGE=OUT/"stage"


def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding="utf-8"))
def array_default(v):return v.tolist() if hasattr(v,"tolist") else list(v)
def collision_hash(value):
    return hashlib.sha256(json.dumps(value,default=array_default,sort_keys=True).encode()).hexdigest()


def visible_wall_hits(models):
    """Ray-test opaque render triangles, independently of the retained player clip."""
    triangles=[]
    for name,m in models.items():
        if name=="collider_glass":continue
        for paint,polygons in m.polygons.items():
            for pts,normal in polygons:
                pts=np.asarray(pts)
                if pts[:,1].max()<600 or pts[:,1].min()>700 or pts[:,2].min()>160:continue
                for i in range(1,len(pts)-1):triangles.append(pts[[0,i,i+1]])
    tri=np.asarray(triangles)
    a=tri[:,0];edge1=tri[:,1]-a;edge2=tri[:,2]-a
    direction=np.array((0.,1.,0.));p=np.cross(direction,edge2)
    det=np.einsum("ij,ij->i",edge1,p)
    valid=np.abs(det)>1e-8
    inv=np.zeros_like(det);inv[valid]=1/det[valid]
    result=[]
    for e in (-335.,-185.,185.,335.):
        origin=np.array((e,600.,130.));offset=origin-a
        u=np.einsum("ij,ij->i",offset,p)*inv
        q=np.cross(offset,edge1)
        v=q@direction*inv
        distance=np.einsum("ij,ij->i",edge2,q)*inv
        hits=valid&(u>=0)&(v>=0)&(u+v<=1)&(distance>0)&(distance<100)
        result.append({"pane_e":e,"opaque_hits":int(hits.sum())})
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview",action="store_true")
    args=parser.parse_args()
    models=C.build()
    baseline=read(OUT/"baseline-collision.json")
    collision={name:{"boxes":m.boxes,"hulls":m.hulls} for name,m in models.items()}
    assert collision_hash(baseline)==collision_hash(collision),"Gameplay collision changed"
    window_checks=visible_wall_hits(models)
    assert all(c["opaque_hits"]==0 for c in window_checks),window_checks
    print("Collision matches the baseline; all four window panes have clear render rays",flush=True)
    triangles={}
    for name,m in models.items():
        count=0
        for polygons in m.polygons.values():
            for pts,normal in polygons:
                pts=np.asarray(pts)
                assert np.isfinite(pts).all() and np.isfinite(normal).all(),name
                assert np.linalg.norm(normal)>.99,name
                for i in range(1,len(pts)-1):
                    assert np.linalg.norm(np.cross(pts[i]-pts[0],pts[i+1]-pts[0]))>1e-8,name
                    count+=1
        triangles[name]=count
    layout=read(OUT/"layout-validation.json")
    assert layout["checked_spots"]==68 and all(layout[k]==0 for k in
        ("obstructed_or_unsupported","unreachable","exposed_retakes_pairs"))
    V.STAGE=STAGE
    V.validate(STAGE/"collider.scene.json",OUT/"scene-validation.json")
    baseline_assets=read(OUT/"baseline.json")["model_sha256"]
    files=[];unchanged=[];import_pending=False
    for path in sorted((STAGE/"models/maps/collider").iterdir()):
        before=ROOT/"Assets/models/maps/collider"/path.name
        expected=baseline_assets[path.name]
        after=digest(path)
        actual=digest(before)
        assert actual in (expected,after),"Imported Collider asset changed independently: "+path.name
        if after==expected:unchanged.append(path.name);continue
        import_pending=import_pending or actual!=after
        files.append({"path":path.relative_to(STAGE).as_posix(),"before_sha256":expected,"sha256":after,
                      "bytes":path.stat().st_size})
    # Physics definitions and convex hull mesh files must remain byte-identical,
    # in addition to the independent in-memory collision comparison above.
    assert all(name in unchanged for name in baseline_assets if "_hulls_" in name)
    physics={}
    for name,_,has_collision in C.MODELS:
        if not has_collision:continue
        relative=f"models/maps/collider/{name}.vmdl"
        marker='_class = "PhysicsShapeList"'
        old=(ROOT/"Assets"/relative).read_text().partition(marker)
        new=(STAGE/relative).read_text().partition(marker)
        assert old[1] and new[1] and old[2]==new[2],"Physics definition changed: "+relative
        physics[relative]=hashlib.sha256(new[2].encode()).hexdigest()
    assert digest(STAGE/"ui/minimaps/minimap_collider.png")==digest(ROOT/"Assets/ui/minimaps/minimap_collider.png")
    report={"revision":"services-v1","native_import_pending":import_pending,
        "stage":"output/collider/services-v1/stage","files":files,"unchanged_model_files":unchanged,
        "triangles":triangles,"collision_sha256":collision_hash(collision),
        "collision_identical":True,"physics_definitions_identical":True,"physics_definition_sha256":physics,"minimap_identical":True,
        "window_render_rays":window_checks,"geometry_finite_and_nondegenerate":True,
        "offline_positions_passed":68,"lights":len(C.LIGHTS),"shadow_lights":sum(l[-1] for l in C.LIGHTS),
        "native_visual_review_report":"output/collider/services-v1/native-review/review-result.json",
        "lighting_note":"The new transparent wall openings require a fresh lighting review/bake; neither v2 nor the pending v3 bake includes them.",
        "source_sha256":{f"Tools/{name}":digest(ROOT/"Tools"/name) for name in
                         ("collider_map.py","collider_services.py","collider_detail_geometry.py")}}
    (OUT/"manifest.json").write_text(json.dumps(report,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,indent=2),flush=True)
    if args.preview:
        import collider_preview_textured as P
        out=OUT/"offline-preview";out.mkdir(exist_ok=True)
        views=[{"name":"service-windows","eye":[440,-150,72],"target":[-130,820,132],"fov":82},
               {"name":"ceiling-services","eye":[500,-500,650],"target":[-650,80,830],"fov":76}]
        for view in views:
            P.render(models,view,1280,720,exposure=.23).save(out/(view["name"]+".png"))
        (out/"provenance.json").write_text(json.dumps({"native_engine_capture":False,"views":views,
            "software_exposure":.23,"limitations":["Approximate unshadowed lighting","No reflection rendering","Glass omitted"]},indent=2))


if __name__=="__main__":main()

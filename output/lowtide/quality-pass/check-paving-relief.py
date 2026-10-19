"""Check physical registration, normals and parallax gradient mathematics."""
from pathlib import Path
import hashlib
import json
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
FOLDER = ROOT/'output/lowtide/quality-pass'
STAGE = FOLDER/'paving-relief-stage'
manifest = json.loads((FOLDER/'paving-relief-manifest.json').read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
for relative, digest in manifest['protected'].items():
    assert sha(ROOT/relative) == digest, relative
for relative, record in manifest['changes'].items():
    assert sha(STAGE/relative) == record['after'], relative
surface = manifest['surface_report']
data = STAGE/'materials/lowtide/paving_relief'
normal = np.asarray(Image.open(data/'lt_setts_normal.png'), dtype=float)/127.5-1
heights = np.asarray(Image.open(data/'lt_setts_height.png'), dtype=float)/255*surface['depth_mm']
ao = np.asarray(Image.open(data/'lt_setts_ao.png'), dtype=float)/255
assert normal.shape == (2048, 2048, 3) and heights.shape == ao.shape == (2048, 2048)
assert np.max(abs(np.linalg.norm(normal, axis=-1)-1)) < .007
assert np.isfinite(normal).all() and np.isfinite(heights).all()
assert heights.min() >= 0 and heights.max() <= 9
assert ao.min() >= .645 and ao.max() <= 1
u, v, w, h = surface['region']
assert np.allclose(np.array(surface['millimetres_per_pixel'])*np.array([w,h])*2048,
                   64*25.4/np.array(surface['scale']))

# Reconstruct known world-space UV gradients under rotations, flips and shear.
# This checks the physical scale and mirrored-UV handling of the shader basis.
rng=np.random.default_rng(19238)
gradient_errors=[]
cases=0
for _ in range(500):
    basis, _ = np.linalg.qr(rng.normal(size=(3,3)))
    n = basis[:,2]
    px = basis[:,0] * rng.uniform(.1,3) + basis[:,1] * rng.uniform(-1,1)
    py = basis[:,0] * rng.uniform(-1,1) + basis[:,1] * rng.uniform(.1,3)
    a,b=np.cross(py,n),np.cross(n,px)
    determinant=np.dot(px,a)
    if abs(determinant)<1e-4: continue
    gu = basis[:,:2] @ rng.uniform(-.08,.08,2)
    gv = basis[:,:2] @ rng.uniform(-.08,.08,2)
    rx=np.array([np.dot(gu,px),np.dot(gv,px)])
    ry=np.array([np.dot(gu,py),np.dot(gv,py)])
    reconstructed=np.array([(rx[j]*a+ry[j]*b)/determinant for j in range(2)])
    gradient_errors.append(float(np.max(abs(reconstructed-np.array([gu,gv])))))
    cases+=1
assert max(gradient_errors)<1e-11

# A constant-depth plane has an analytic ray/UV intersection. Check march
# interpolation at both normal and grazing views, including an undisplaced top.
trace_errors=[]
for facing in (.02,.2,.5,.85,1):
    steps=int(24+(8-24)*facing)
    for height in np.linspace(0,1,33):
        ray=np.array([.03,-.018]); delta=ray/steps
        at=np.array([.32,.79]); start=at.copy(); depth=0; surface_depth=1-height
        previous=surface_depth
        for _ in range(steps):
            if depth>=surface_depth: break
            previous=surface_depth-depth; at-=delta; depth+=1/steps
        after=surface_depth-depth
        weight=np.clip(after/min(after-previous,-.00001),0,1)
        result=at+delta*weight
        trace_errors.append(float(np.max(abs(result-(start-ray*surface_depth)))))
assert max(trace_errors)<1e-12
report=dict(protected_files=len(manifest['protected']), staged_files=len(manifest['changes']),
    gradient_cases=cases, maximum_gradient_error=max(gradient_errors),
    flat_intersections=len(trace_errors), maximum_intersection_error=max(trace_errors),
    colour_unchanged=True, mesh_scene_and_collision_unchanged=True,
    surface=surface, status='CPU/data validation passed; native compile and visual review separate')
(FOLDER/'paving-relief-data-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='surface'},indent=2))

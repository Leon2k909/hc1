"""Stage only the APC's yard chunk; refuse physics or unrelated geometry drift."""
import sys,json,hashlib,collections,shutil,py_compile
from pathlib import Path
root=Path('C:/Users/mimi-/Documents/S&box Projects/hc1');out=Path(__file__).parent
sys.path.insert(0,str(root/'Tools'))
import forestbase_map as F
import forestbase_apc as A
import map_kit as K
for name in ('forestbase_apc','forestbase_map'):py_compile.compile(str(root/'Tools'/(name+'.py')),doraise=True)
source=out/'armor-source.png'
if not source.exists():shutil.copy2(Path('C:/Users/mimi-/.codex/generated_images/01a15fb3-66d8-7c71-aeba-4e3ba10cd0fd/exec-28554549-83b0-474e-9e94-21e053d501c8.png'),source)
A.materials(out/'materials',source)
print('APC PBR materials staged',flush=True)
# Construct the actual in-map vehicle and its identical old collision first.
vehicle=F.model();F.truck(vehicle,-900,-995,0,True)
print('APC geometry built',flush=True)
models=F.build(visual_chunks=['yard']);yard=models['yard']
stage=out/'stage';stage.mkdir(exist_ok=True)
count=K.write_obj(stage/'yard.obj',yard,'yard');K.write_vmdl(stage/'yard.vmdl',F.RES,'yard',yard)
old=(out/'yard.vmdl').read_text();new=(stage/'yard.vmdl').read_text();marker='_class = "PhysicsShapeList"'
assert old[old.index(marker):]==new[new.index(marker):],'Physics changed'
for p in stage.glob('yard_hulls_*.obj'):assert p.read_bytes()==(root/'Assets/models/maps/forestbase'/p.name).read_bytes(),p.name
def triangles(path):
    v=[];vt=[];vn=[];paint='';result=collections.Counter()
    for line in path.open():
        cols=line.split()
        if not cols:continue
        if cols[0]=='v':v.append(tuple(cols[1:]))
        elif cols[0]=='vt':vt.append(tuple(cols[1:]))
        elif cols[0]=='vn':vn.append(tuple(cols[1:]))
        elif cols[0]=='usemtl':paint=cols[1]
        elif cols[0]=='f':
            face=[]
            for token in cols[1:]:
                a,b,c=map(int,token.split('/'));face.append((v[a-1],vt[b-1],vn[c-1]))
            result[(paint,tuple(face))]+=1
    return result
before=triangles(out/'yard.obj');after=triangles(stage/'yard.obj')
removed=before-after;added=after-before
# Map-kit OBJ coordinates are (-east, up, north). Every changed triangle must
# lie in the APC's narrow authored bounds, including its original whip aerials.
for (paint,face),copies in (removed+added).items():
    for pos,uv,normal in face:
        minus_e,z,n=map(float,pos);e=-minus_e
        assert -1052<=e<=-748 and -1064<=n<=-926 and -1<=z<=175,(paint,e,n,z)
report={'chunk':'yard','oldTriangles':sum(before.values()),'triangles':count,
        'removedTriangles':sum(removed.values()),'addedTriangles':sum(added.values()),
        'allChangedTrianglesInsideAPC':True,'allOtherGeometryUnchanged':True,
        'physicsUnchanged':True,'sourceYardSHA256':hashlib.sha256((out/'yard.obj').read_bytes()).hexdigest(),
        'vehicleBounds':{'planMin':[-1052,-1064,-1],'planMax':[-748,-926,175]},
        'builtInImageGeneration':True,'generatedAlbedo':str(source)}
(out/'audit.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)

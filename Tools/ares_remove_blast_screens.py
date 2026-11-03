"""Remove the two wing doorway blast screens from the installed Ares hall."""
from pathlib import Path
from collections import Counter
import hashlib,json,re,shutil,sys
import numpy as np
ROOT=Path.cwd();OUT=ROOT/'output/ares/remove-blast-screens-20261031';OUT.mkdir(parents=True,exist_ok=True)
obj=ROOT/'Assets/models/maps/ares/pressure-doors-v2/hall_base.obj'
vmdl=ROOT/'Assets/models/maps/ares/ares_hall.vmdl';source=ROOT/'Tools/ares_map.py'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
lines=obj.read_bytes().decode('utf-8').splitlines(keepends=True);vertices=[];paint='';removed={-1:[],1:[]};materials={-1:Counter(),1:Counter()};actual={-1:Counter(),1:Counter()}
def key(paint,points):return paint,tuple(sorted(tuple(round(float(x),4) for x in p) for p in points))
for index,line in enumerate(lines):
    p=line.split()
    if not p:continue
    if p[0]=='v':a,z,n=map(float,p[1:]);vertices.append((-a,n,z))
    elif p[0]=='usemtl':paint=p[1]
    elif p[0]=='f':
        pts=np.array([vertices[int(x.split('/')[0])-1] for x in p[1:]])
        for side in (-1,1):
            e=pts[:,0]*side
            if np.all((e>=1256.99)&(e<=1279.01)&(pts[:,1]>=-174.51)&(pts[:,1]<=174.51)&(pts[:,2]>=-.01)&(pts[:,2]<=192.01)):
                removed[side].append(index);materials[side][paint]+=1;actual[side][key(paint,pts)]+=1;break
print(json.dumps({'selectedTriangles':{str(k):len(v) for k,v in removed.items()},'materials':{str(k):dict(v) for k,v in materials.items()}},indent=2))
if '--inspect' in sys.argv:sys.exit(0)
assert all(materials[s]==Counter({'ar_hazard':12,'ar_signs':4,'ar_steel':50,'ar_wall':10}) for s in (-1,1))
sys.path.insert(0,str(ROOT/'Tools'));import ares_map as A
generator=source.read_text();start=generator.index('    # The blast screen inside the middle door:');end=generator.index('    # The zone marker on the outer wall',start)
block=generator[start:end];ns=vars(A).copy();exec('def original_screen(m, s):\n'+block,ns)
for side in (-1,1):
    m=A.Model();ns['original_screen'](m,side);expected=Counter()
    for mat,polys in m.polygons.items():
        for points,_ in polys:
            for k in range(1,len(points)-1):expected[key(mat,(points[0],points[k],points[k+1]))]+=1
    assert expected==actual[side],('Geometry does not exactly match generated screen',side,expected-actual[side],actual[side]-expected)
    assert len(m.boxes)==1 and not m.hulls
doc=vmdl.read_bytes().decode('utf-8');matches=[]
for match in re.finditer(r'\{\s*_class = "PhysicsShapeBox"[^{}]*\}',doc):
    origin=re.search(r'origin = \[([^\]]+)\]',match[0]);dimensions=re.search(r'dimensions = \[([^\]]+)\]',match[0])
    if origin and list(map(float,origin[1].split(','))) in ([0.,1268.,96.],[0.,-1268.,96.]):
        assert list(map(float,dimensions[1].split(',')))==[16.,340.,192.];matches.append(match)
assert len(matches)==2
newdoc=doc
for m in reversed(matches):
    a=newdoc.rfind('\n',0,m.start())+1;b=newdoc.index('\n',m.end())+1;newdoc=newdoc[:a]+newdoc[b:]
newobj=''.join(line for i,line in enumerate(lines) if i not in set(removed[-1]+removed[1]))
newsource=generator[:start]+'    # Doorway blast screens removed at the user\'s request.\n'+generator[end:]
constant='SCREEN_E, SCREEN_N = ( 1260.0, 1276.0 ), ( -170.0, 170.0 )    # the blast screens inside the wings\' middle doors (abs e)\n'
assert newsource.count(constant)==1;newsource=newsource.replace(constant,'')
assert 'SCREEN_E' not in newsource and 'SCREEN_N' not in newsource
payloads=[(obj,newobj.encode()),(vmdl,newdoc.encode()),(source,newsource.encode())]
before={str(p.relative_to(ROOT)):sha(p) for p,_ in payloads}
completed=[]
try:
    for path,data in payloads:
        backup=OUT/'before'/path.relative_to(ROOT);backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();shutil.copy2(path,backup)
        tmp=path.with_name(path.name+'.screens-incoming');tmp.write_bytes(data);tmp.replace(path);completed.append(path)
except BaseException:
    for path in reversed(completed):shutil.copy2(OUT/'before'/path.relative_to(ROOT),path)
    raise
report={'removedScreens':2,'removedTriangles':sum(map(len,removed.values())),'removedCollisionBoxes':2,
        'originalScreenGeometryMatchedExactly':True,'otherObjLinesPreserved':True,'otherModelDocDataPreserved':True,
        'beforeSHA256':before,'afterSHA256':{str(p.relative_to(ROOT)):sha(p) for p,_ in payloads},'nativeCompilePerformed':False}
(OUT/'removal.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

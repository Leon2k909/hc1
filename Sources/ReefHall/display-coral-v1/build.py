"""Organic sea-fan colony at a close-range display; original aquarium stays unchanged."""
from pathlib import Path
import sys,json,hashlib,math
import numpy as np
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import reefhall_map as R
OUT=ROOT/'output/reefhall/display-coral-v1';STAGE=OUT/'stage/Assets';RES='models/props/reefhall/display_coral_v1';MODEL=STAGE/RES;MODEL.mkdir(parents=True,exist_ok=True)
baseline=json.loads((OUT/'baseline.json').read_text());lo,hi=np.array(baseline['bounds']);origin=(lo+hi)/2;origin[2]=lo[2]
def build(lod):
    m=K.Model();rng=np.random.default_rng(107);paths=[]
    def branch(a,b,c,r0,r1,seed):
        # Quadratic curves, circular sections, smoothly tapered tissue and rounded terminal caps.
        rings=(10,7,4)[lod];sides=(10,7,5)[lod];a,b,c=map(lambda p:np.array(p,float),(a,b,c));centers=[];radii=[]
        for t in np.linspace(0,1,rings):
            centers.append((1-t)**2*a+2*(1-t)*t*b+t*t*c);radii.append(r0*(1-t)+r1*t)
        tangent=(c-b)/np.linalg.norm(c-b)
        centers.extend([c+tangent*r1*.65,c+tangent*r1*.9]);radii.extend([r1*.65,r1*.24])
        sections=[];normals=[]
        for k,(p,r) in enumerate(zip(centers,radii)):
            axis=centers[min(k+1,len(centers)-1)]-centers[max(k-1,0)];axis/=np.linalg.norm(axis)
            ref=np.array((0.,1.,0));u=np.cross(axis,ref);u/=np.linalg.norm(u);v=np.cross(axis,u)
            dirs=[u*math.cos(j*math.tau/sides)+v*math.sin(j*math.tau/sides) for j in range(sides)]
            sections.append([p+d*r for d in dirs]);normals.append(dirs)
        for k in range(len(sections)-1):
            for j in range(sides):
                jj=(j+1)%sides;G._face(m,'rh_coral_purple',[sections[k][j],sections[k][jj],sections[k+1][jj],sections[k+1][j]],nrm=[normals[k][j],normals[k][jj],normals[k+1][jj],normals[k+1][j]])
        G._face(m,'rh_coral_purple',sections[-1],towards=tangent);G._face(m,'rh_coral_purple',sections[0],towards=a-b)
        if lod==0:
            # Tiny pale polyp crowns emerge from the branch tissue along the upper growth.
            for k in (rings//2,rings-1):
                p=centers[k];rad=radii[k]
                for j in (1,4,7):
                    d=np.array((math.cos(j*math.tau/10),math.sin(j*math.tau/10),.15));d/=np.linalg.norm(d)
                    G.lathe_axis(m,p+d*(rad*.78),d,[(0,0),(.07,0),(.09,.05),(.06,.12),(0,.15)],'rh_coral_white',sides=5)
    # A fan grows from a shared holdfast into seven irregular curved trunks and smaller lateral forks.
    for index,s in enumerate(np.linspace(-1,1,7)):
        start=np.array((s*.12,0,-.15));bend=np.array((s*3.1,.32*math.sin(index*2),3.1));tip=np.array((s*5.8,.5*math.cos(index*1.6),6.9-abs(s)*1.5))
        branch(start,bend,tip,.32,.095,index)
        for fraction,sign in ((.42,-1),(.61,1),(.78,-1)):
            root=(1-fraction)**2*start+2*(1-fraction)*fraction*bend+fraction*fraction*tip
            length=1.05+.55*rng.random();end=root+np.array((sign*length,.35*rng.uniform(-1,1),1.55+.9*rng.random()))
            control=root+np.array((sign*length*.7,.25*rng.uniform(-1,1),.6));branch(root,control,end,.145,.055,index)
    # A broad encrusted base seats below the original sand level.
    G.lathe_axis(m,(0,0,-.3),(0,0,1),[(0,0),(.7,0),(.58,.24),(.32,.45),(0,.45)],'rh_coral_purple',sides=(20,14,10)[lod])
    R.configure(m)
    # Fit all living tissue into the original occupied envelope, preserving the existing fish avoidance volume.
    points=np.array([p for faces in m.polygons.values() for poly,_ in faces for p in poly]);a,b=points.min(0),points.max(0);scale=(hi-lo)/(b-a)
    targetlo=lo-origin
    for paint,faces in list(m.polygons.items()):
        for k,(poly,normal) in enumerate(faces):
            normal=np.array(normal)/scale;normal/=np.linalg.norm(normal);m.polygons[paint][k]=([(p-a)*scale+targetlo for p in poly],normal)
            if (paint,k) in m.polygon_normals:
                ns=np.array(m.polygon_normals[(paint,k)])/scale;ns/=np.linalg.norm(ns,axis=1,keepdims=True);m.polygon_normals[(paint,k)]=list(ns)
        m.tile_overrides[paint]=8.
    return m
def write_oriented(path,m,name):
    count=K.write_obj(path,m,name);lines=path.read_text().splitlines();vertices=np.array([l.split()[1:] for l in lines if l.startswith('v ')],float);normals=np.array([l.split()[1:] for l in lines if l.startswith('vn ')],float)
    for i,line in enumerate(lines):
        if not line.startswith('f '):continue
        tokens=line.split()[1:];refs=[[int(x)-1 for x in t.split('/')] for t in tokens];tri=vertices[[x[0] for x in refs]];normal=normals[[x[2] for x in refs]].mean(0)
        if np.dot(np.cross(tri[1]-tri[0],tri[2]-tri[0]),normal)<0:lines[i]='f '+' '.join((tokens[0],tokens[2],tokens[1]))
    path.write_text('\n'.join(lines)+'\n');return count
models=[];counts=[]
for lod in range(3):
    m=build(lod);models.append(m);counts.append(write_oriented(MODEL/f'coral_lod{lod}.obj',m,f'coral_lod{lod}'))
K.write_vmdl(MODEL/'coral.vmdl',RES,'coral_lod0',models[0]);doc=(MODEL/'coral.vmdl').read_text();a=doc.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=doc.index('\n\t\t\t},',a)+len('\n\t\t\t},')
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/coral_lod{i}.obj" import_scale = 1 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for i in range(3));groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"] }},' for i,d in enumerate((0,20,55)))
(MODEL/'coral.vmdl').write_text(doc[:a]+f'{{ _class = "RenderMeshList" children = [ {meshes} ] }},\n{{ _class = "LODGroupList" children = [ {groups} ] }},'+doc[b:])
src=ROOT/baseline['source'];assert hashlib.sha256(src.read_bytes()).hexdigest()==baseline['source_sha256'],'Current source changed; inspect/rebase baseline first'
lines=src.read_text().splitlines(keepends=True);cut=set(baseline['face_lines']);assert len(cut)==288 and all(lines[i].startswith('f ') for i in cut)
(MODEL/'preview.obj').write_text(''.join(line for i,line in enumerate(lines) if i not in cut));(MODEL/'reefhall_rotunda_tanks.mtl').write_bytes(src.with_suffix('.mtl').read_bytes())
(MODEL/'preview.vmdl').write_text(src.with_suffix('.vmdl').read_text().replace('filename = "models/maps/reefhall/reefhall_rotunda_tanks.obj"',f'filename = "{RES}/preview.obj"'))
protected=[src,src.with_suffix('.vmdl'),src.with_suffix('.mtl'),ROOT/'Assets/scenes/maps/ReefHall/reefhall.scene']
manifest=dict(preview_only=True,existing_upgrade_audit='Searched coral/reef rock model and source filenames, source/docs upgrade references; no suitable existing upgraded colony found.',triangles=counts,old_triangles=288,position_world=K.to_world(origin).tolist(),original_bounds=baseline['bounds'],
 protected={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in protected},files={p.relative_to(STAGE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in MODEL.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'triangles':counts,'old_faces':288,'position':manifest['position_world']}))

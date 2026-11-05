from pathlib import Path
import sys,math,json,re,collections,hashlib
import numpy as np
from PIL import Image
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2];sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_map as R
RES='models/maps/riverside/folded-tarp-v1';MAT='materials/riverside/folded-tarp-v1';MODEL=REVIEW/'Assets'/RES;MATERIAL=REVIEW/'Assets'/MAT;OUT=REVIEW/'output/riverside/folded-tarp-v1'
for p in (MODEL,MATERIAL,OUT):p.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(145);n=1024;yy,xx=np.mgrid[:n,:n];weave=np.sin(xx*math.pi/2)*np.sin(yy*math.pi/2);grain=rng.random((n,n));albedo=246+weave*5+(grain-.5)*5
Image.fromarray(np.repeat(albedo.clip(0,255).astype('uint8')[:,:,None],3,axis=2)).save(MATERIAL/'weave.png')
nx=np.cos(xx*math.pi/2)*.065;ny=np.cos(yy*math.pi/2)*.065;norm=np.dstack((nx,ny,np.ones_like(nx)));norm/=np.linalg.norm(norm,axis=2)[:,:,None];Image.fromarray(((norm*.5+.5)*255).astype('uint8')).save(MATERIAL/'normal.png')
def mat(name,tint,rough=.72,metal=0):
    color=f'"{MAT}/weave.png"' if name in ('cloth','underside','hem') else '"[1 1 1 0]"'
    normalmap=f'{MAT}/normal.png' if name in ('cloth','underside','hem') else 'materials/default/default_normal.tga'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {color}
 TextureNormal "{normalmap}"
 TextureRoughness "[{rough} {rough} {rough} 0]"
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[{' '.join(str(v) for v in tint)} 1]"
}}
''',encoding='utf-8')
mat('cloth',(.117647,.274510,.509804));mat('underside',(.087,.20,.37),.82);mat('hem',(.10,.24,.45),.77);mat('thread',(.11,.24,.41),.9);mat('steel',(.35,.37,.35),.46,.85);mat('dark',(.012,.018,.022),.95)
Z=np.array((0.,0.,1.))
def roof(y):return 1-5.5*abs(y)/62.5
def sheet(x,y,level=3,curl=True):
    z=roof(y)+.14+level*.52
    z+=.45*math.sin(x*.20+y*.045)+.30*math.sin(y*.24-x*.06)
    z+=1.25*math.exp(-((x-y*.25+3)/3.2)**2)-.50*math.exp(-((x+y*.14-18)/2.4)**2)+.65*math.exp(-((y+x*.12+12)/3.0)**2)
    z+=.13*math.sin((x+y)*.62)*math.exp(-min(40-abs(x),40-abs(y))/6)
    if curl and x+y>70:
        d=(x+y-70)/math.sqrt(2);a=d/3.5;shift=(3.5*math.sin(a)-d)/math.sqrt(2);x+=shift;y+=shift;z+=3.5*(1-math.cos(a))
    return np.array((x,y,z))
def normal(x,y,level=3,curl=True):
    a=sheet(x+.01,y,level,curl)-sheet(x-.01,y,level,curl);b=sheet(x,y+.01,level,curl)-sheet(x,y-.01,level,curl);n=np.cross(a,b);return n/np.linalg.norm(n)
def model(lod=0):
    m=K.Model();size=(64,40,24)[lod];steps=np.linspace(-40,40,size+1)
    # Upper and lower fabric faces follow the shallow pitched roof and physical fold radii.
    for bottom in (False,True):
        for i in range(size):
            for j in range(size):
                coords=[(steps[i],steps[j]),(steps[i+1],steps[j]),(steps[i+1],steps[j+1]),(steps[i],steps[j+1])]
                pts=[sheet(x,y) for x,y in coords];ns=[normal(x,y) for x,y in coords]
                if bottom:pts=[q-n*.06 for q,n in zip(pts,ns)]
                if bottom:pts.reverse();coords.reverse();ns=[-n for n in ns[::-1]]
                m.polygon('underside' if bottom else 'cloth',pts,normals=ns,uv=[(x/12.8,y/12.8) for x,y in coords])
    # The lower folded sheet becomes visible below the peeled-back corner.
    base=np.linspace(-40,40,9)
    for i in range(8):
        for j in range(8):
            xy=[(base[i],base[j]),(base[i+1],base[j]),(base[i+1],base[j+1]),(base[i],base[j+1])]
            pts=[sheet(x,y,0,False) for x,y in xy];ns=[normal(x,y,0,False) for x,y in xy];m.polygon('cloth',pts,normals=ns,uv=[(x/12.8,y/12.8) for x,y in xy])
    # Successive soft folded edges, rather than solid vertical box walls.
    for level in range(4):
        inset=(.3,.0,.45,.0)[level]
        for axis in (0,1):
            for sg in (-1,1):
                path=[]
                for t in steps:
                    x,y=(sg*(40-inset),t) if axis==0 else (t,sg*(40-inset));path.append(sheet(x,y,level,level==3))
                for k in range(len(path)-1):
                    a,b=path[k:k+2];pts=[a-Z*.055,b-Z*.055,b+Z*.055,a+Z*.055];towards=np.array((sg,0,0) if axis==0 else (0,sg,0));G.card(m,'hem',pts,towards,uv=[(k/5,0),((k+1)/5,0),((k+1)/5,1),(k/5,1)])
                if level==3:G._sweep(m,path,.10,'hem',sides=6 if lod<2 else 4,caps=True)
    if lod<2:
        # Reinforced folded hems with quiet double stitch lines.
        for axis in (0,1):
            for sg in (-1,1):
                for t in np.arange(-37,38,2 if lod==0 else 4):
                    x,y=(sg*39,t) if axis==0 else (t,sg*39);q=sheet(x,y)+normal(x,y)*.035;direction=np.array((0.,.30,0)) if axis==0 else np.array((.30,0,0));G._sweep(m,[q-direction,q+direction],.025,'thread',sides=4)
    # Metal eyelets have an open annular lip and a recessed dark interior.
    for x,y in [(-36,-36),(0,-36),(36,-36),(-36,0),(36,0),(-36,36),(0,36),(36,36)]:
        q=sheet(x,y);n=normal(x,y);G.lathe_axis(m,q+n*.03,n,[(.29,0.),(.50,0.),(.53,.05),(.48,.12),(.29,.12),(.29,0.)],'steel',sides=(16,12,8)[lod]);G.lathe_axis(m,q-n*.005,n,[(0.,0.),(.28,0.),(.28,.015),(0.,.015)],'dark',sides=12)
    m.material_overrides={p:MAT+'/'+p+'.vmat' for p in m.polygons};m.tile_overrides={p:12.8 for p in m.polygons}
    return m
models=[model(i) for i in range(3)];counts=[K.write_obj(MODEL/f'tarp_lod{i}.obj',models[i],f'tarp_lod{i}') for i in range(3)];K.write_vmdl(MODEL/'tarp.vmdl',RES,'tarp_lod0',models[0]);t=(MODEL/'tarp.vmdl').read_text();a=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');b=t.index('\n\t\t\t},',a)+len('\n\t\t\t},')
nodes=''.join(f'{{_class="RenderMeshFile" name="lod{i}" filename="{RES}/tarp_lod{i}.obj" import_scale=1 align_origin_x_type="None" align_origin_y_type="None" align_origin_z_type="None" import_filter={{exclude_by_default=false exception_list=[]}}}},' for i in range(3));groups=''.join(f'{{_class="LODGroup" switch_threshold={d} meshes=["lod{i}"]}},' for i,d in enumerate((0,15,35)));(MODEL/'tarp.vmdl').write_text(t[:a]+f'{{_class="RenderMeshList" children=[{nodes}]}},{{_class="LODGroupList" children=[{groups}]}},'+t[b:])
old=K.Model();R.box(old,-40,40,-40,40,0,3,'rs_tarp_blue');R.configure(old);K.write_model(MODEL,RES,'legacy_tarp',old)
absolute=P.place(old,(737,607,314),90);K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_tarp')
def records(p):
    lines=p.read_text().splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,l in enumerate(lines):
        if l.startswith('usemtl '):paint=l.split()[1]
        if l.startswith('f '):faces.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in l.split()[1:])))))
    return lines,faces
_,keys=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(k for _,k in keys);public=ROOT/'Assets/models/maps/riverside/riverside_levee.vmdl';text=public.read_text();source=None
for ref in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text):
    candidate=ROOT/'Assets'/ref;lines,faces=records(candidate)
    if not wanted-collections.Counter(k for _,k in faces):source=candidate;break
assert source,'Saved tarp differs from the assumed original'
cut=set()
for i,k in faces:
    if wanted[k]:cut.add(i);wanted[k]-=1
assert len(cut)==12 and not +wanted
(MODEL/'levee_without_tarp.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in cut).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib levee_without_tarp.mtl'));(MODEL/'levee_without_tarp.mtl').write_bytes(source.with_suffix('.mtl').read_bytes());(MODEL/'levee_without_tarp.vmdl').write_text(text.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/levee_without_tarp.obj'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();manifest=dict(preview_only=True,triangles=counts,position=[607,-737,314],yaw=90,source_model=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),source_vmdl=public.relative_to(ROOT).as_posix(),source_vmdl_sha256=sha(public),files={p.relative_to(REVIEW).as_posix():sha(p) for d in (MODEL,MATERIAL) for p in d.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))

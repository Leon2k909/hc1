"""Private review of the NO PLACE BETTER neon: real rounded tubes and serviceable sign hardware."""
from pathlib import Path
import sys,math,json,hashlib,re,collections
import numpy as np
from PIL import Image
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');HERE=Path(__file__).parent;REVIEW=HERE.parents[2]
sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K
import riverdale_parts as G
import riverside_parts as P
import riverside_materials as RM
import riverside_map as R
RES='models/maps/riverside/neon-sign-v1';MAT='materials/riverside/neon-sign-v1'
MODEL=REVIEW/'Assets'/RES;MATERIAL=REVIEW/'Assets'/MAT;OUT=REVIEW/'output/riverside/neon-sign-v1'
for folder in (MODEL,MATERIAL,OUT):folder.mkdir(parents=True,exist_ok=True)
rng=np.random.default_rng(817);size=1024;yy,xx=np.mgrid[0:size,0:size]/(size-1)
noise=np.asarray(Image.fromarray(rng.integers(0,256,(64,64),dtype='uint8')).resize((size,size),Image.Resampling.BICUBIC),float)/255
grain=rng.random((size,size));wear=(np.minimum(xx,1-xx)<.013)|(np.minimum(yy,1-yy)<.015)
chips=wear&(noise>.57);runoff=(1-yy)**8*(.3+.7*noise)
color=np.zeros((size,size,3))+[69,78,71];color-=runoff[...,None]*[14,15,14];color+=(noise[...,None]-.5)*8+(grain[...,None]-.5)*3;color[chips]=[94,77,56]
Image.fromarray(color.clip(0,255).astype('uint8')).save(MATERIAL/'enamel_color.png')
rough=(.65+runoff*.11+grain*.055);Image.fromarray((rough*255).clip(0,255).astype('uint8')).save(MATERIAL/'enamel_rough.png')
dy,dx=np.gradient(noise*.035+grain*.008);normal=np.dstack((-dx,-dy,np.ones_like(dx)));normal/=np.linalg.norm(normal,axis=2)[...,None]
Image.fromarray(((normal*.5+.5)*255).clip(0,255).astype('uint8')).save(MATERIAL/'enamel_normal.png')
def mat(name,color,rough=.65,metal=0,extra=''):
    c='"'+MAT+'/'+color+'"' if isinstance(color,str) else '"['+' '.join(str(x) for x in color)+' 0]"'
    details=f'TextureNormal "materials/default/default_normal.tga"\n TextureRoughness "[{rough} {rough} {rough} 0]"'
    if name=='enamel':details=f'TextureNormal "{MAT}/enamel_normal.png"\n TextureRoughness "{MAT}/enamel_rough.png"'
    (MATERIAL/f'{name}.vmat').write_text(f'''Layer0
{{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor {c}
 {details}
 g_flRoughnessScaleFactor "1"
 g_flMetalness "{metal}"
 g_vColorTint "[1 1 1 1]"
 {extra}
}}
''',encoding='utf-8')
mat('enamel','enamel_color.png',metal=.02);mat('backplate',(.058,.063,.057),.83)
mat('steel',(.25,.28,.26),.48,.84);mat('ceramic',(.53,.49,.41),.36)
mat('rubber',(.018,.020,.017),.85);mat('rust',(.18,.083,.036),.92)
# A hotter center and red edges approximate the longer light path through the center of the gas tube.
q=np.abs(np.linspace(-1,1,256));hot=np.clip((q-.25)/.75,0,1)**2
rgb=np.stack([np.full(256,255),30+hot*200,10+hot*165],axis=1)
Image.fromarray(np.repeat(rgb[None,:,:],64,axis=0).astype('uint8')).save(MATERIAL/'neon_red_color.png')
mat('neon_red','neon_red_color.png',.24,extra='F_SELF_ILLUM 1\n TextureSelfIllumMask "[1 1 1 0]"\n g_flSelfIllumBrightness "8.0"\n g_flSelfIllumAlbedoFactor "1"\n g_vSelfIllumTint "[1 1 1 0]"')
X=np.array((1.,0,0));Y=np.array((0.,-1,0));Z=np.array((0.,0,1.))
def p(x,d,z):return X*x+Y*d+Z*z
def strokes():
    # Same hand-drawn stroke library, seed, spacing and layout as the atlas original.
    rng=np.random.default_rng(14);sets=[RM.stroke_lines(line,rng,jitter=.004) for line in ('NO','PLACE','BETTER')]
    sw,sh=105.,120.;w,h=sw*.84,sh*.84;em=min(h*.88/(3+.38*2),w*.88/max(width for _,width in sets));top=sh*.08+(h-em*(3+.38*2))/2
    result=[]
    for row,(paths,width) in enumerate(sets):
        ox=sw*.08+(w-width*em)/2;base=top+em*(row+1)+em*.38*row
        for path in paths:result.append([(ox+x*em-sw/2,410+sh/2-base+y*em) for x,y in path])
    return result
PATHS=strokes()
def model(lod=0):
    m=K.Model();sides=(12,8,6)[lod]
    def box(c,size,paint='enamel',b=.10):G.bevel_box(m,p(*c),(X,Y,Z),size,paint,bevel=b if lod<2 else min(b,.025))
    def cyl(c,axis,length,r,paint='steel',n=None):G.lathe_axis(m,p(*c),axis,[(0.,0.),(float(r),0.),(float(r),float(length)),(0.,float(length))],paint,sides=n or sides)
    def tube(points,r,paint,n=None,bend=.5):G.tube(m,points,r,paint,sides=n or sides,bend_radius=bend)
    # Original pole radius, cabinet volume and height retained.
    cyl((0,0,0),Z,360,4,'enamel',24 if lod<2 else 12)
    for z in (3.,24.,337.):cyl((0,0,z),Z,1.2,4.35,'steel')
    box((0,0,1.0),(17,17,2),'steel',.25)
    if lod<2:
        for x in (-6.3,6.3):
            for d in (-6.3,6.3):cyl((x,d,2),Z,.9,.68,'steel',6)
    # Folded metal lightbox, inset black faces, gaskets and rolled perimeter rails.
    box((0,0,410),(111,10,126),'enamel',.65)
    for sg in (-1,1):
        box((0,sg*5.1,410),(106,.20,121),'rubber',.15)
        box((0,sg*5.25,410),(104,.18,119),'backplate',.12)
        for z in (349.4,470.6):box((0,sg*5.44,z),(108,.8,1.4),'enamel',.20)
        for x in (-53.7,53.7):box((x,sg*5.44,410),(1.4,.8,120),'enamel',.18)
        # Small mounting rails remain visibly behind the tubes.
        for z in (381.,410.,439.):box((0,sg*5.57,z),(98,.38,.60),'enamel',.08)
        for index,path in enumerate(PATHS):
            pts=path
            if lod==1 and len(pts)>6:pts=pts[::2]+([] if pts[-1]==pts[::2][-1] else [pts[-1]])
            if lod==2 and len(pts)>6:pts=pts[::3]+([] if pts[-1]==pts[::3][-1] else [pts[-1]])
            # Mirror the second face's horizontal axis so its text reads correctly from behind.
            points=[p(sg*x,sg*7.15,z) for x,z in pts]
            tube(points,.38,'tube',n=(10,8,6)[lod],bend=.70)
            if lod==0:
                # Electrode boots cover the final tube ends; small insulated leads return to the backing.
                for at,neighbor in [(0,1),(-1,-2)]:
                    q=np.asarray(points[at]);a=np.asarray(points[neighbor])-q;a/=np.linalg.norm(a)
                    G.lathe_axis(m,q,a,[(0.,0.),(.57,0.),(.57,1.0),(.44,1.25),(0.,1.25)],'rubber',sides=8)
                    terminal=q-a*.32
                    tube([terminal,terminal-Y*sg*.7,terminal-Y*sg*1.65+Z*.5],.11,'rubber',n=5,bend=.20)
                # Two or three restrained ceramic stand-offs per independently bent tube.
                samples=[pts[0],pts[len(pts)//2]] if len(pts)<6 else [pts[0],pts[len(pts)//2],pts[-1]]
                for x,z in samples:
                    cyl((sg*x,sg*5.57,z),Y*sg,1.1,.36,'ceramic',8)
                    cyl((sg*x,sg*6.7,z),Y*sg,.16,.53,'steel',8)
                    if lod==0:box((sg*x,sg*7.38,z),(.11,.12,.93),'steel',.02)
        if lod<2:
            for x in (-50.8,50.8):
                for z in (352.,382.,438.,468.):cyl((x,sg*5.92,z),Y*sg,.08,.22,'steel',6)
    # Side service door, hinge barrels, lock, rain lip, mounting cradle and supply conduit.
    box((55.61,0,394),(.20,7.7,31),'rubber',.13)
    box((55.78,0,394),(.20,7.2,30.5),'enamel',.12)
    for z in (384.,404.):cyl((55.96,-3.6,z),Z,3,.34,'steel',8)
    cyl((56.02,2.0,394),X,.18,.66,'steel',8)
    box((0,0,474),(114,12,1.3),'enamel',.20)
    box((0,0,344),(25,10,3),'steel',.20)
    for x in (-8.,8.):box((x,0,338),(1.1,7.5,12),'steel',.12)
    box((0,-4.65,322),(8,3.7,12),'enamel',.25)
    if lod<2:
        tube([p(0,-4.0,28),p(0,-4.0,306),p(0,-6.5,310),p(0,-6.5,316)],.42,'steel',n=8,bend=1.3)
        for z in (38.,160.,285.):box((0,-4.45,z),(2.5,.65,1),'steel',.10)
    for paint,faces in m.polygons.items():
        for i,(pts,nrm) in enumerate(faces):
            if paint=='tube':
                norms=m.polygon_normals.get((paint,i),[nrm]*len(pts));uv=[((float(np.dot(n,Y))+1)*.5,.5) for n in norms]
            elif abs(nrm[2])>.7:uv=[((q[0]+57)/114,(-q[1]+7)/14) for q in pts]
            elif abs(nrm[0])>.7:uv=[((-q[1]+7)/14,(q[2]-347)/127) for q in pts]
            else:uv=[((q[0]+55.5)/111,(q[2]-347)/126) for q in pts]
            m.polygon_uvs[(paint,i)]=uv
    m.material_overrides={paint:MAT+'/'+paint+'.vmat' for paint in m.polygons};m.material_overrides['tube']=MAT+'/neon_red.vmat';m.tile_overrides={paint:32 for paint in m.polygons}
    # Rounded sweep joints occasionally collapse a tiny fan triangle at OBJ's .001-inch precision.
    # Keep the valid half of each face and drop only triangles with zero exported area.
    clean=K.Model()
    for paint,faces in m.polygons.items():
        for i,(points,normal) in enumerate(faces):
            for k in range(1,len(points)-1):
                indices=[0,k,k+1];pts=[points[j] for j in indices];rounded=np.round(pts,3)
                if np.linalg.norm(np.cross(rounded[1]-rounded[0],rounded[2]-rounded[0]))<=2e-8:continue
                normals=m.polygon_normals.get((paint,i))
                clean.polygon(paint,pts,normal,uv=[m.polygon_uvs[(paint,i)][j] for j in indices],normals=None if normals is None else [normals[j] for j in indices])
    clean.material_overrides=m.material_overrides;clean.tile_overrides=m.tile_overrides
    return clean
models=[model(i) for i in range(3)]
triangles=[K.write_obj(MODEL/f'neon_lod{i}.obj',models[i],f'neon_lod{i}') for i in range(3)]
K.write_vmdl(MODEL/'neon_sign.vmdl',RES,'neon_lod0',models[0])
t=(MODEL/'neon_sign.vmdl').read_text(encoding='utf-8');start=t.index('\t\t\t{\n\t\t\t\t_class = "RenderMeshList"');end=t.index('\n\t\t\t},',start)+len('\n\t\t\t},')
nodes='\n'.join(f'{{_class = "RenderMeshFile" name = "lod{i}" filename = "{RES}/neon_lod{i}.obj" import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" import_filter = {{exclude_by_default = false exception_list = []}}}},' for i in range(3))
groups='\n'.join(f'{{_class = "LODGroup" switch_threshold = {d} meshes = ["lod{i}"]}},' for i,d in enumerate((0,20,45)))
(MODEL/'neon_sign.vmdl').write_text(t[:start]+f'{{_class = "RenderMeshList" children = [{nodes}]}},\n{{_class = "LODGroupList" children = [{groups}]}},'+t[end:],encoding='utf-8')
local=K.Model();P.neon_sign(local,(0,0,0),(0,-1));R.configure(local);K.write_model(MODEL,RES,'legacy_neon',local)
absolute=K.Model();P.neon_sign(absolute,*R.NO_PLACE);R.configure(absolute);oldtri=K.write_obj(OUT/'legacy-absolute.obj',absolute,'old_neon')
def records(path):
    lines=path.read_text(encoding='utf-8').splitlines(keepends=True);v=[tuple(round(float(x),3) for x in l.split()[1:4]) for l in lines if l.startswith('v ')];paint='';faces=[]
    for i,line in enumerate(lines):
        if line.startswith('usemtl '):paint=line.split()[1]
        if line.startswith('f '):faces.append((i,(paint,tuple(sorted(v[int(t.split('/')[0])-1] for t in line.split()[1:])))))
    return lines,faces
_,keys=records(OUT/'legacy-absolute.obj');wanted=collections.Counter(key for _,key in keys)
public=ROOT/'Assets/models/maps/riverside/riverside_dressing.vmdl';text=public.read_text(encoding='utf-8');source=None
for resource in re.findall(r'filename\s*=\s*"([^"]+\.obj)"',text):
    candidate=ROOT/'Assets'/resource
    if not candidate.exists():continue
    lines,faces=records(candidate)
    if not wanted-collections.Counter(key for _,key in faces):source=candidate;break
assert source,'Original neon changed; inspect active dressing input'
removed=set()
for i,key in faces:
    if wanted[key]:removed.add(i);wanted[key]-=1
assert not +wanted and len(removed)==oldtri
(MODEL/'dressing_without_neon.obj').write_text(''.join(l for i,l in enumerate(lines) if i not in removed).replace('mtllib '+source.with_suffix('.mtl').name,'mtllib dressing_without_neon.mtl'),encoding='utf-8')
(MODEL/'dressing_without_neon.mtl').write_bytes(source.with_suffix('.mtl').read_bytes())
(MODEL/'dressing_without_neon.vmdl').write_text(text.replace(source.relative_to(ROOT/'Assets').as_posix(),RES+'/dressing_without_neon.obj'),encoding='utf-8')
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=dict(preview_only=True,triangles=triangles,original_triangles=oldtri,position=[1150,60,0],yaw=math.degrees(math.atan(.05)),cabinet_dimensions=[111,10,126],source_model=source.relative_to(ROOT).as_posix(),source_sha256=sha(source),source_vmdl=public.relative_to(ROOT).as_posix(),source_vmdl_sha256=sha(public),external_files={p:sha(ROOT/p) for p in ('Assets/materials/riverside/rs_lit.vmat','Assets/materials/riverside/rs_lit_color.png','Assets/materials/riverside/rs_lit_illum.png')},files={p.relative_to(REVIEW).as_posix():sha(p) for folder in (MODEL,MATERIAL) for p in folder.iterdir() if p.is_file()})
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in manifest.items() if k!='files'},indent=2))

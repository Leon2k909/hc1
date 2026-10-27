"""Ares transport cases: reusable formed shells, hardware and facility markings.

The four variants preserve both original sizes and the marked/plain stacking
pattern. Props are render-only: the existing map collision remains authoritative.
"""
import math
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import gaussian_filter

import map_kit as K
import riverdale_parts as P
import ares_case_shell as Shell

ROOT = Path(__file__).resolve().parents[1]
PREFIX = 'materials/ares/crate-v2'
MODEL_PREFIX = 'models/props/ares/crate-v2'
NAMES = ('black', 'black_edge', 'rubber', 'gasket', 'steel', 'alloy', 'dust', 'id', 'stencil')
MATERIALS = {f'ar_cargo_{n}': f'{PREFIX}/{n}.vmat' for n in NAMES}
X = np.array((1., 0., 0.)); Y = np.array((0., 1., 0.)); Z = np.array((0., 0., 1.))
SIZES = {'standard': (48., 30., 32.), 'cargo': (72., 45., 48.)}


def variant(size, front):
    name = next(n for n, dims in SIZES.items() if np.allclose(dims, size))
    return name + ('-marked' if front == 'front_text' else '-plain')


def prop_path(size, front):
    return f'{MODEL_PREFIX}/{variant(size, front)}.vmdl'


def far_shell(model, size):
    L, H, W = size; seam = H * .735
    rings = []
    for z, inset in ((.54, 1.06), (1.4, .74), (seam-.26, .46),
                     (seam+.18, .42), (seam+.65, .21), (H-.95, .21), (H, .56)):
        xy, normals = Shell.rounded_rect(L-2*inset, W-2*inset, 2.5, 2)
        rings.append([np.array((*p, z)) for p in xy])
    for j in range(len(rings)-1):
        paint = 'ar_cargo_gasket' if j == 2 else 'ar_cargo_black'
        for i in range(len(rings[j])):
            k = (i+1) % len(rings[j])
            P.card(model, paint, (rings[j][i], rings[j][k], rings[j+1][k], rings[j+1][i]),
                   np.array((*normals[i], 0.)),
                   normals=[np.array((*n, 0.)) for n in (normals[i], normals[k], normals[k], normals[i])])
    P.card(model, 'ar_cargo_dust', rings[-1], Z)
    P.card(model, 'ar_cargo_black', rings[0], -Z)
    for sign in (-1, 1):
        P.bevel_box(model, (sign*L*.318, -W/2+.4, seam-.3), (X,Y,Z),
                    (2.7,.6,4.4), 'ar_cargo_steel', bevel=.14)
        P.bevel_box(model, (sign*(L/2-.38), 0, H*.385), (Y,X,Z),
                    (9.4,.18,3.5), 'ar_cargo_rubber', bevel=.35)
    for sx in (-1,1):
        for sy in (-1,1):
            P.bevel_box(model,(sx*(L/2-3.25),sy*(W/2-3.25),.35),(X,Y,Z),
                        (4.1,4.1,.70),'ar_cargo_rubber',bevel=.30)


def add_marks(model, size, marked, lod):
    L, H, W = size; seam = H*.735; radius=2.5
    body_low, body_high = 1.4, seam-.26
    depth = .52 if lod < 2 else 0.
    def field(out, right, half_depth, half_width, u, z):
        shrink = .74 + (.46-.74)*(z-body_low)/(body_high-body_low)
        span = half_width-radius
        return out*(half_depth-shrink-depth+.025) + right*u*(span-shrink)/span + Z*z
    def print_card(paint, out, right, half_depth, half_width, width, height, z, uv):
        points=[field(out,right,half_depth,half_width,u,h)
                for u,h in ((-width/2,z-height/2),(width/2,z-height/2),
                            (width/2,z+height/2),(-width/2,z+height/2))]
        P.card(model,paint,points,out,uv=uv)
    if marked:
        print_card('ar_cargo_stencil',-Y,X,W/2,L/2,L*.43,H*.45,H*.375,
                   ((0,0),(1,0),(1,1),(0,1)))
    # Printed identification plates sit in the flat recessed end fields, clear
    # of the carrying pockets. They follow the shell taper exactly.
    for normal,right in ((X,Y),(-X,-Y)):
        print_card('ar_cargo_id',normal,right,L/2,W/2,min(16.,W*.45),H*.115,seam-4.,
                   ((0,0),(1,0),(1,1),(0,1)))


def build_prop(size, marked, lod=0):
    L,H,W=map(float,size);local=K.Model()
    if lod < 2:
        Shell.build_into(local,(0,0),(L,W,H),surface=None,marked=marked,quality=lod)
    else:
        far_shell(local,size)
    add_marks(local,size,marked,lod)
    result=K.Model();result.material_overrides.update(MATERIALS)
    result.tile_overrides.update({p:16. for p in MATERIALS})
    # The authored shell's catching face is -Y; Ares' original front is +Y.
    axes=np.array((-X,-Y,Z))
    for paint,rows in local.polygons.items():
        for i,(points,normal) in enumerate(rows):
            mat=paint
            if paint in ('ar_cargo_black','ar_cargo_black_edge') and normal[2]>.86:
                mat='ar_cargo_dust'
            ns=local.polygon_normals.get((paint,i))
            result.polygon(mat,[p@axes for p in points],normal=normal@axes,
                normals=[n@axes for n in ns] if ns is not None else None,
                uv=local.polygon_uvs.get((paint,i)))
    assert not result.boxes and not result.hulls
    return result


def append_instance(model,e,n,z,heading,size,front,side,top,collide=True):
    model.props.append({'model':prop_path(size,front),'position':(float(e),float(n),float(z)),
                        'heading':float(heading),'variant':variant(size,front)})
    if collide:
        L,H,W=size;t=math.radians(heading)
        x=np.array((math.cos(t),math.sin(t),0.));y=np.cross(Z,x)
        model.oriented_box((e,n,z+H/2),(x,y,Z),(L,W,H),{},'plastic')
    return z+size[1]


def scene_group(ids,props=None):
    id_path=ROOT/'Sources/Ares/crate-v2/scene-instance-ids.json'
    if id_path.exists():
        import json
        saved_ids=json.loads(id_path.read_text());fallback=ids
        ids=lambda key:saved_ids.get(key) or fallback(key)
    if props is None:
        import ares_map as A
        captured=K.Model()
        # Replaying dressing is deterministic and writes no assets. Preserve its
        # source placement logic rather than maintaining a second list of poses.
        A.dressing(captured)
        props=captured.props
    children=[]
    for i,item in enumerate(props):
        key=f'world/cargo-cases/{i:03d}'
        children.append(K.game_object(ids,f'ARES transport case {i+1:03d}',key,
            K.to_world(item['position']),rotation=K.yaw_rotation(item['heading']),
            components=[K.component(ids,'Sandbox.ModelRenderer',key+'/renderer',
                Model=item['model'],Tint='1,1,1,1',RenderType='On')]))
    return K.game_object(ids,'ARES transport cases','world/cargo-cases',children=children)


def write_materials(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True)
    rng=np.random.default_rng(260622);n=1024
    def noise(sigma):
        a=gaussian_filter(rng.normal(size=(n,n)),sigma,mode='wrap');return a/max(a.std(),1e-9)
    grain=noise(.7);pores=noise(1.5);broad=noise(45);handling=noise(88)
    scratch=Image.new('L',(n,n));draw=ImageDraw.Draw(scratch)
    for _ in range(90):
        x,y=rng.uniform(0,n,2);length=rng.uniform(4,40);a=rng.uniform(-.3,.3)
        draw.line((x,y,x+length*math.cos(a),y+length*math.sin(a)),fill=int(rng.integers(20,130)),width=1)
    scuffs=gaussian_filter(np.asarray(scratch,dtype=float)/255,.5)
    h=.0015*grain+.0008*pores-.0012*scuffs;step=16/n
    dx=(np.roll(h,-1,1)-np.roll(h,1,1))/(2*step);dy=(np.roll(h,-1,0)-np.roll(h,1,0))/(2*step)
    normal=np.stack((-dx,dy,np.ones_like(dx)),axis=-1);normal/=np.linalg.norm(normal,axis=-1)[...,None]
    Image.fromarray(np.clip((normal*.5+.5)*255,0,255).astype('uint8')).save(out/'shell_normal.png')
    Image.new('RGB',(16,16),(128,128,255)).save(out/'flat_normal.png')
    for name,rough in (('shell',.57),('edge',.46),('rubber',.78),('steel',.35),('dust',.68),('paper',.72)):
        Image.fromarray(np.clip((rough+.018*grain+.022*handling-.12*scuffs)*255,0,255).astype('uint8')).save(out/f'{name}_rough.png')
    for name,color in (('black',(48.,51.,52.)),('black_edge',(53.,57.,58.)),('rubber',(29.,31.,32.)),
                       ('gasket',(13.,15.,16.)),('steel',(89.,96.,99.)),('alloy',(156.,164.,166.))):
        shade=1+.006*broad+.010*grain+.006*handling+.10*scuffs
        Image.fromarray(np.clip(shade[...,None]*np.asarray(color),0,255).astype('uint8')).save(out/f'{name}_color.png')
    dust=np.clip(.10+.07*broad,.01,.28)[...,None]
    base=np.asarray(Image.open(out/'black_color.png'),float)
    color=base*(1-dust)+np.asarray((104.,85.,70.))*dust
    Image.fromarray(np.clip(color,0,255).astype('uint8')).save(out/'dust_color.png')

    # Flat artwork uses the project's existing Ares logo and Dinish typeface.
    import ares_materials as AM
    font=ImageFont.truetype(str(AM.FONT_BOLD),85)
    small=ImageFont.truetype(str(AM.FONT_BOLD),28)
    tiny=ImageFont.truetype(str(AM.FONT_BOLD),22)
    plate=Image.new('RGB',(1536,384),(202,203,197));d=ImageDraw.Draw(plate)
    d.rectangle((14,14,1521,369),outline=(74,79,79),width=3)
    for polygon,ink in AM.logo_polygons(150,80,148):
        d.polygon(polygon,fill=(162,44,37) if ink else (202,203,197))
    d.text((290,44),'ARES FACILITY',font=font,fill=(33,40,43))
    d.text((300,159),'ATMOS DIV. 07  /  SEALED EQUIPMENT',font=small,fill=(47,55,58))
    d.text((300,211),'TYPE 04    HANDLING CLASS 2',font=small,fill=(47,55,58))
    for x in range(301,1127,7):
        if rng.random()>.26:d.rectangle((x,278,x+int(rng.integers(2,5)),337),fill=(37,45,47))
    d.text((1183,275),'07',font=font,fill=(44,52,54))
    # Power-of-two normal maps and texture resources throughout.
    plate=plate.resize((2048,512),Image.Resampling.LANCZOS)
    plate.save(out/'id_color.png')
    stencil=Image.new('L',(1024,1024));d=ImageDraw.Draw(stencil)
    font=ImageFont.truetype(str(AM.FONT_BOLD),150)
    for i,word in enumerate(('MARS','BIGGER','CLEANER','BRIGHTER')):
        bounds=d.textbbox((0,0),word,font=font);width=bounds[2]-bounds[0]
        d.text(((1024-width)/2,90+i*210),word,font=font,fill=255)
    mask=np.asarray(stencil).copy();chips=rng.random(mask.shape)<.0015;mask[chips]=0
    Image.fromarray(mask).save(out/'stencil_alpha.png')
    Image.new('RGB',(16,16),(190,193,188)).save(out/'stencil_color.png')
    for name in NAMES:
        rough={'black':'shell','black_edge':'edge','gasket':'rubber','alloy':'steel','id':'paper','stencil':'paper'}.get(name,name)
        metal=.86 if name=='alloy' else .72 if name=='steel' else 0.
        normal='flat_normal' if name in ('gasket','alloy','id','stencil') else 'shell_normal'
        alpha=('    F_ALPHA_TEST "1"\n    g_flAlphaTestReference "0.4"\n'
               f'    TextureTranslucency "{PREFIX}/stencil_alpha.png"\n') if name=='stencil' else ''
        text=('// Tools/ares_cargo_case.py\n"Layer0"\n{\n    shader "shaders/complex.shader"\n'
              '    F_SPECULAR "1"\n'+alpha+f'    g_flMetalness "{metal}"\n    g_flRoughnessScaleFactor "1"\n'
              f'    TextureColor "{PREFIX}/{name}_color.png"\n    TextureNormal "{PREFIX}/{normal}.png"\n'
              f'    TextureRoughness "{PREFIX}/{rough}_rough.png"\n'
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'
              '    g_vColorTint "[1 1 1 1]"\n    g_flModelTintAmount "1"\n}\n')
        (out/f'{name}.vmat').write_text(text)


def write_models(directory):
    out=Path(directory);out.mkdir(parents=True,exist_ok=True);reports={}
    for name,size in SIZES.items():
        for marked in (False,True):
            tag=name+('-marked' if marked else '-plain');lods=[]
            for lod in range(3):
                model=build_prop(size,marked,lod)
                path=out/f'{tag}-lod{lod}.obj';K.write_obj(path,model,tag)
                points=np.vstack([p for rows in model.polygons.values() for p,n in rows])
                assert np.isfinite(points).all() and np.isfinite([n for rows in model.polygons.values() for p,n in rows]).all()
                L,H,W=size;assert np.all(points.min(0)>=np.array((-L/2-1.2,-W/2-1.2,0))-.001)
                assert np.all(points.max(0)<=np.array((L/2+1.2,W/2+1.2,H))+.001)
                lods.append(model.triangle_count())
            mats='\n'.join(f'{{ from = "{p}.vmat" to = "{m}" }},' for p,m in MATERIALS.items())
            meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{MODEL_PREFIX}/{tag}-lod{l}.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }},' for l in range(3))
            lodgroups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {threshold} meshes = ["lod{l}"] }},' for l,threshold in enumerate((0.0,10.0,24.0)))
            doc=('<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
                 '{ rootNode = { _class = "RootNode" children = [\n'
                 '{ _class = "MaterialGroupList" children = [{ _class = "DefaultMaterialGroup" remaps = [\n'+mats+
                 '\n] use_global_default = false global_default_material = "" }] },\n'
                 '{ _class = "RenderMeshList" children = [\n'+meshes+'\n] },\n'
                 '{ _class = "LODGroupList" children = [\n'+lodgroups+'\n] }\n'
                 '] model_archetype = "" primary_associated_entity = "" base_model_name = "" } }\n')
            (out/f'{tag}.vmdl').write_text(doc)
            reports[tag]={'size':size,'lod_triangles':lods,'render_only':True}
    return reports

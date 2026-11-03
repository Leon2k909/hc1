"""Stage the approved Ares interior delta against current published sources."""
from pathlib import Path
from collections import Counter
import sys, json, re, hashlib, ast
import numpy as np
from PIL import Image
import native
ROOT=native.ROOT;OUT=native.OUT;STAGE=OUT/'stage';BEFORE=OUT/'before'
sys.path.insert(0,str(ROOT/'Tools'))
import ares_map as A
import ares_interior as I
import map_kit as K
import riverdale_splice as S

def sha(data):return hashlib.sha256(data).hexdigest()
def snapshot(relative):
    data=(ROOT/relative).read_bytes();target=BEFORE/relative
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():assert target.read_bytes()==data,f'Input changed since staging: {relative}'
    else:target.write_bytes(data)
    return data
def staged(relative,data):
    p=STAGE/relative;p.parent.mkdir(parents=True,exist_ok=True)
    p.write_bytes(data if isinstance(data,bytes) else data.encode('utf-8'));return p
def export(model,path,name):
    A.configure(model);I.configure(model)
    K.write_obj(path,model,name)
    return S.read_obj(path)[1]
def material_aliases(doc,materials):
    token='remaps =';pos=doc.index('[',doc.index(token))+1
    additions=[]
    for name,path in materials.items():
        assert f'from = "{name}.vmat"' not in doc,f'Already installed material: {name}'
        additions.append(f'\n{{ from = "{name}.vmat" to = "{path}" }},')
    return doc[:pos]+''.join(additions)+doc[pos:]

STAGE.mkdir(parents=True,exist_ok=True)
source_scene='Assets/scenes/maps/Ares/ares.scene'
scene_bytes=snapshot(source_scene)
print('Visual roots:',[g.get('Name') for g in json.loads(scene_bytes)['GameObjects']],flush=True)
models=[];files={}

# Reproduce only the six original roof trusses, six flat side pilasters and
# original top floor face. All must match the installed base before anything
# can be written to the editor.
old_hall=K.Model()
for e in (-900.,-600.,-300.,300.,600.,900.):A.truss(old_hall,e,A.HALL_N0,A.HALL_N1+A.LEAN*640-20)
for side in (-1,1):
    face=side*A.HALL_E
    for n in (-600.,-150.,300.):
        lo=(face-side*10,n-12,A.G) if side>0 else (face,n-12,A.G)
        hi=(face,n+12,A.HALL_TOP) if side>0 else (face+10,n+12,A.HALL_TOP)
        old_hall.box(lo,hi,'ar_steel')
old_hall.box((-2032,-752,-24),(2032,720,0),{'default':None,'+z':'ar_floor'})
new_hall=K.Model();I.append_hall(new_hall);I.outer_floor(new_hall)
old_core=K.Model();new_core=K.Model()
for e,n in ((270,270),(-270,270),(-270,-270),(270,-270)):
    heading=np.degrees(np.arctan2(n,e))+90
    A.pump_unit(old_core,e,n,heading);I.pump_unit(new_core,e,n,heading)
assert len(old_core.boxes)==len(new_core.boxes)==4
for before,after in zip(old_core.boxes,new_core.boxes):
    assert all(np.allclose(a,b,rtol=0,atol=1e-10) for a,b in zip(before[:3],after[:3])) and before[3]==after[3]

for name,old,new in (('ares_hall',old_hall,new_hall),('ares_reactor',old_core,new_core)):
    document=f'Assets/models/maps/ares/{name}.vmdl';doc_bytes=snapshot(document);doc=doc_bytes.decode('utf-8')
    paths=re.findall(r'filename\s*=\s*"([^"]+)"',doc)
    primary='Assets/'+paths[0]
    original=snapshot(primary);source_path=BEFORE/primary
    header,published=S.read_obj(source_path)
    old_faces=export(old,OUT/f'{name}-removed.obj',name)
    new_faces=export(new,OUT/f'{name}-added.obj',name)
    have=Counter(published);remove=Counter(old_faces)
    missing=remove-have
    assert not missing,f'{name}: {sum(missing.values())} of {sum(remove.values())} old faces do not match the installed source'
    retained=list((have-remove).elements())
    restyled=0
    if name=='ares_hall':
        revised=[]
        for material,corners in retained:
            # Only the six-inch gallery toe boards in the central hall. Stair
            # nosings, door thresholds and all wing warnings retain their paint.
            points=[list(map(float,p.split())) for p,uv,nrm in corners]
            if material=='ar_hazard' and all(208-1e-3<=p[1]<=214+1e-3 and abs(p[0])<=1101 and -721<=p[2]<=765 for p in points):
                revised.append((I.FRAME,corners));restyled+=1
            else:revised.append((material,corners))
        retained=revised
    final=retained+new_faces
    base_name='hall_base' if name=='ares_hall' else 'reactor_base'
    trial_relative=f'Assets/models/maps/ares/interior-v1/{base_name}.obj'
    trial=STAGE/trial_relative;trial.parent.mkdir(parents=True,exist_ok=True)
    header=[line if not line.startswith('mtllib ') else f'mtllib {base_name}.mtl\n' for line in header]
    S.write_obj(trial,header,final)
    mtl=''.join(f'newmtl {paint}\nKd 1 1 1\nd 1\n' for paint in sorted({m for m,_ in final}))
    trial.with_suffix('.mtl').write_text(mtl)
    materials={m:I.MATERIALS[m] for m in sorted({p for p,_ in final}) if m in I.MATERIALS}
    live_doc=material_aliases(doc,materials)
    preview_doc=live_doc.replace(paths[0],trial_relative[7:])
    preview=f'Assets/models/maps/ares/interior-v1/{name}_preview.vmdl'
    staged(preview,preview_doc)
    for p in (trial,trial.with_suffix('.mtl'),STAGE/preview):
        files[p.relative_to(STAGE).as_posix()]=sha(p.read_bytes())
    # Prepare live replacements separately; they are applied only after native QA.
    live_obj=OUT/'install-stage'/primary;live_obj.parent.mkdir(parents=True,exist_ok=True)
    live_header=[line if not line.startswith('mtllib ') else f'mtllib {Path(primary).stem}.mtl\n' for line in header]
    S.write_obj(live_obj,live_header,final)
    live_mtl=live_obj.with_suffix('.mtl');live_mtl.write_text(mtl)
    live_document=OUT/'install-stage'/document;live_document.parent.mkdir(parents=True,exist_ok=True);live_document.write_bytes(live_doc.encode('utf-8'))
    mtl_relative=str(Path(primary).with_suffix('.mtl')).replace('\\','/')
    if (ROOT/mtl_relative).exists():snapshot(mtl_relative)
    marker='_class = "PhysicsShapeList"'
    assert doc[doc.index(marker):]==live_doc[live_doc.index(marker):],name+' physics changed'
    models.append(dict(name=name,primary=primary,document=document,preview=preview[7:],
        removed_faces=len(old_faces),added_faces=len(new_faces),restyled_toe_faces=restyled,
        preserved_faces=len(published)-len(old_faces),source_sha256=sha(original),document_sha256=sha(doc_bytes),
        physics_sha256=sha(doc[doc.index(marker):].encode('utf-8')),materials=materials,
        private_geometry_sha256=sha((OUT/f'{name}-added.obj').read_bytes())))
    print(f'{name}: removed {len(old_faces)}, added {len(new_faces)}, recoloured {restyled} toe faces; retained {len(published)-len(old_faces)} other faces',flush=True)

# Private PBR tiles. Fine surface variation is subordinate to the large forms.
rng=np.random.default_rng(31103);size=512
coarse=np.asarray(Image.fromarray(rng.integers(0,256,(32,32),dtype=np.uint8)).resize((size,size),Image.Resampling.BICUBIC),float)/255-.5
fine=rng.normal(0,1,(size,size));configs={
 I.PANEL:((180,177,164),.67,.0),I.FRAME:((46,51,51),.55,.65),I.RED:((121,59,43),.61,.0),
 I.ALLOY:((139,144,142),.43,1.),I.DARK:((22,26,25),.77,.0),I.FLOOR:((66,71,70),.73,.12)}
for paint,(color,rough,metal) in configs.items():
    name=paint[6:];folder=STAGE/'Assets/materials/ares/interior-v1';folder.mkdir(parents=True,exist_ok=True)
    variation=coarse*(3 if paint==I.PANEL else 6)+fine*(.25 if paint==I.PANEL else .55)
    rgb=np.clip(np.asarray(color)[None,None,:]+variation[:,:,None],0,255).astype('uint8')
    Image.fromarray(rgb).save(folder/f'{name}_color.png')
    Image.fromarray(np.clip((rough+coarse*.045+fine*.002)*255,0,255).astype('uint8')).save(folder/f'{name}_rough.png')
    # A very fine powder-coat grain, in tangent-space normal format.
    height=coarse*.03+fine*.0008
    dy,dx=np.gradient(height);norm=np.stack((-dx*.7,-dy*.7,np.ones_like(dx)),axis=-1);norm/=np.linalg.norm(norm,axis=-1,keepdims=True)
    Image.fromarray(np.clip((norm*.5+.5)*255,0,255).astype('uint8')).save(folder/f'{name}_normal.png')
    text=f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_flMetalness "{metal}"
 g_flRoughnessScaleFactor "1"
 TextureColor "materials/ares/interior-v1/{name}_color.png"
 TextureNormal "materials/ares/interior-v1/{name}_normal.png"
 TextureRoughness "materials/ares/interior-v1/{name}_rough.png"
 TextureAmbientOcclusion "materials/default/default_ao.tga"
 g_vColorTint "[1 1 1 1]"
 g_flModelTintAmount "1"
}}
'''
    (folder/f'{name}.vmat').write_text(text)
    for p in folder.glob(f'{name}*'):files[p.relative_to(STAGE).as_posix()]=sha(p.read_bytes())

# Narrow source hooks ensure a subsequent generator run retains the new design.
source=snapshot('Tools/ares_map.py').decode('utf-8')
hook='''        if paint.startswith( "ar_pd_" ) and paint in model.material_overrides:'''
assert source.count(hook)==1
source=source.replace(hook,'''        if paint.startswith( "ar_in_" ) and paint in model.material_overrides:
            continue
'''+hook)
start=source.index('        # Pilasters on the hall side,');end=source.index('    # The south wall:',start)
source=source[:start]+source[end:]
old='''    for e in ( -900.0, -600.0, -300.0, 300.0, 600.0, 900.0 ):
        truss( m, e, HALL_N0, HALL_N1 + LEAN * 640 - 20 )'''
assert source.count(old)==1;source=source.replace(old,'    # Curved pressure frames are added by ares_interior.append_hall().')
start=source.index('def pump_unit( m, e, n, heading ):');end=source.index('\ndef console(',start)
source=source[:start]+'''def pump_unit( m, e, n, heading ):
    from ares_interior import pump_unit as draw_pump
    return draw_pump( m, e, n, heading )

'''+source[end:]
old='''    m.box( ( -WING_E - WALL, HALL_N0 - WALL, -24 ), ( WING_E + WALL, HALL_N1, 0 ), { "+z": "ar_floor", "default": "ar_concrete_dark" }, METAL )'''
assert source.count(old)==1
source=source.replace(old,old.replace('"+z": "ar_floor"','"+z": None')+'''
    from ares_interior import outer_floor
    outer_floor( m )''')
old='''    concourse( hall, glass )
    reactor( column_model, glass )'''
assert source.count(old)==1
source=source.replace(old,'''    concourse( hall, glass )
    from ares_interior import append_hall
    append_hall( hall )
    reactor( column_model, glass )''')
old='''    m.oriented_box( ( a + b ) / 2 + UP * 3.0, ( along, side, UP ), ( length, 0.6, 6.0 ), "ar_hazard" )'''
assert source.count(old)==1
source=source.replace(old,'''    toe_paint = "ar_in_frame" if abs( z - G ) < 0.01 and all( abs( p[0] ) <= HALL_E and HALL_N0 <= p[1] <= DECK_N1 for p in ( a, b ) ) else "ar_hazard"
    m.oriented_box( ( a + b ) / 2 + UP * 3.0, ( along, side, UP ), ( length, 0.6, 6.0 ), toe_paint )''')
ast.parse(source)
live_source=OUT/'install-stage/Tools/ares_map.py';live_source.parent.mkdir(parents=True,exist_ok=True);live_source.write_text(source)
manifest=dict(revision='ares-interior-v1',files=files,models=models,scene_sha256=sha(scene_bytes),
 source_sha256=sha((BEFORE/'Tools/ares_map.py').read_bytes()),concept='Sources/Ares/interior-concept-20261103/concept-v1.png',
 collision_unchanged=True,pump_collision_boxes_unchanged=True,editor_scene_not_modified=True)
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('Staged',len(files),'private files; all original model physics retained.',flush=True)

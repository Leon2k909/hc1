"""Stage the approved reel, remove two placeholders and the stair obstruction's box.

All mutations here stay outside Assets. Native editor scripts publish the reviewed
files and serialize the new scene instance after successful native compilation.
"""
from pathlib import Path
import hashlib,json,math,re,shutil
import numpy as np
from PIL import Image
ROOT=Path.cwd();HERE=ROOT/'Sources/Orion/cable-reel-trial-v1'
OUT=ROOT/'output/orion-cable-reel-installed-20261030';STAGE=OUT/'stage';STAGE.mkdir(parents=True,exist_ok=True)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
RESOURCE='models/props/orion/cable_reel_v1';MATERIAL='materials/orion/cable_reel_v1'
report=json.loads((ROOT/'output/asset-improvement-20261030/orion-cable-reel/export-validation.json').read_text())
assert sha(HERE/'cable_reel_after.glb')==report['sha256']
provenance=json.loads((HERE/'provenance.json').read_text())
source=ROOT/provenance['source'];assert sha(source)==provenance['sourceSHA256']
aliases={
 'Weathered_timber_-_original_photographic_CC0_scan':('cr_wood','wood',.38),
 'Exposed_sawn_board_end_grain':('cr_endgrain','endgrain',.70),
 'Fine_textured_black_cable_jacket':('cr_cable','cable',.55),
 'Weathered_galvanized_hardware':('cr_zinc','zinc',.60),
 'Localized_oxidized_steel':('cr_oxide','oxide',.60),
 'Faded_paper_inventory_label':('cr_label','label',0.)}
md=STAGE/'Assets'/MATERIAL;md.mkdir(parents=True,exist_ok=True)
modeldir=STAGE/'Assets'/RESOURCE;modeldir.mkdir(parents=True,exist_ok=True)

# Match the reviewed Blender normal-map strengths in native texture data.
for original,(alias,prefix,strength) in aliases.items():
    if prefix=='label':
        shutil.copy2(HERE/'textures/inventory_label.png',md/'label_color.png')
    else:
        for suffix in ('color','roughness','metallic'):
            p=HERE/'textures'/f'{prefix}_{suffix}.png'
            if p.exists():shutil.copy2(p,md/p.name)
        src=HERE/'textures'/f'{prefix}_normal.png'
        a=np.asarray(Image.open(src).convert('RGB'),dtype=np.float32)/127.5-1
        a*=strength;a[:,:,2]+=1-strength;a/=np.linalg.norm(a,axis=2)[:,:,None]
        Image.fromarray(np.uint8(np.clip((a*.5+.5)*255+.5,0,255))).save(md/src.name)
    text='"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
    text+=f'    TextureColor "{MATERIAL}/{prefix}_color.png"\n'
    if prefix=='label':text+='    TextureRoughness "[0.89 0.89 0.89 0]"\n'
    else:
        text+=f'    TextureNormal "{MATERIAL}/{prefix}_normal.png"\n    TextureRoughness "{MATERIAL}/{prefix}_roughness.png"\n'
    if (md/f'{prefix}_metallic.png').exists():text+=f'    TextureMetalness "{MATERIAL}/{prefix}_metallic.png"\n'
    else:text+='    g_flMetalness "0"\n'
    text+='    TextureAmbientOcclusion "[1 1 1 0]"\n    g_flRoughnessScaleFactor "1"\n    g_flModelTintAmount "1"\n}\n'
    (md/f'{alias}.vmat').write_text(text)

lods=[]
for lod in range(4):
    raw=OUT/'raw'/f'lod{lod}.obj';assert raw.exists()
    out=[f'mtllib cable_reel_lod{lod}.mtl\n',f'o lod{lod}\n'];count=0;used=set()
    for line in raw.read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':
            x,y,z=map(float,p[1:]);out.append(f'v {-x/.0254:.7f} {z/.0254:.7f} {y/.0254:.7f}\n')
        elif p[0]=='vn':
            x,y,z=map(float,p[1:]);out.append(f'vn {-x:.9f} {z:.9f} {y:.9f}\n')
        elif p[0]=='vt':out.append(line+'\n')
        elif p[0]=='usemtl':
            assert p[1] in aliases,p[1];alias=aliases[p[1]][0];used.add(alias);out.append('usemtl '+alias+'\n')
        elif p[0]=='f':assert len(p)==4;count+=1;out.append(line+'\n')
    assert len(used)==6
    (modeldir/f'cable_reel_lod{lod}.obj').write_text(''.join(out))
    (modeldir/f'cable_reel_lod{lod}.mtl').write_text(''.join(f'newmtl {a}\nKd 1 1 1\nd 1\n' for a in sorted(used)))
    lods.append(count)
assert lods[0]==81443 and all(a>b for a,b in zip(lods,lods[1:])),lods
header='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
remaps='\n'.join(f'{{ from = "{a}.vmat" to = "{MATERIAL}/{a}.vmat" }},' for a,p,s in aliases.values())
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{RESOURCE}/cable_reel_lod{l}.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for l in range(4))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = ["lod{l}"] }},' for l,t in enumerate((0,24,60,150)))
(modeldir/'cable_reel.vmdl').write_text(header+'{ rootNode = { _class = "RootNode" children = [\n{ _class = "MaterialGroupList" children = [{ _class = "DefaultMaterialGroup" remaps = [\n'+remaps+'\n] use_global_default = false global_default_material = "" }] },\n{ _class = "RenderMeshList" children = [\n'+meshes+'\n] },\n{ _class = "LODGroupList" children = [\n'+groups+'\n] }\n] model_archetype = "" primary_associated_entity = "" base_model_name = "" } }\n')

# Retain every unrelated original OBJ byte and attribute/index; remove exactly 56 faces.
lines=source.read_bytes().decode('utf-8').splitlines(keepends=True);vs=[];paint='';removed={0:[],1:[]};keep=[]
origins=[np.array((380.,1320.,240.)),np.array((470.,1300.,240.))]
for number,line in enumerate(lines,1):
    p=line.split()
    if p and p[0]=='v':a,z,n=map(float,p[1:]);vs.append(np.array((-a,n,z)))
    elif p and p[0]=='usemtl':paint=p[1]
    elif p and p[0]=='f':
        pts=np.array([vs[int(t.split('/')[0])-1] for t in p[1:]])
        selected=None
        for k,origin in enumerate(origins):
            rel=pts-origin
            if paint=='oa_wall_dark' and np.all(np.abs(np.linalg.norm(rel[:,:2],axis=1)-26)<.002) and np.all(np.minimum(abs(rel[:,2]),abs(rel[:,2]-46))<.001):
                selected=k;break
        if selected is not None:removed[selected].append(number);continue
    keep.append(line)
assert [len(removed[i]) for i in range(2)]==[28,28]
rel=Path('models/maps/orion/orion_launch_deck.obj');dest=STAGE/'Assets'/rel;dest.parent.mkdir(parents=True,exist_ok=True)
dest.write_text(''.join(keep),encoding='utf-8',newline='')
doc=source.with_suffix('.vmdl');old=doc.read_bytes().decode('utf-8');matches=[]
for m in re.finditer(r'\{\s*_class = "PhysicsShapeBox"[^{}]*\}',old):
    vals=re.search(r'origin = \[([^\]]+)\]',m[0]);dims=re.search(r'dimensions = \[([^\]]+)\]',m[0])
    if vals and list(map(float,vals[1].split(',')))==[1300.,-470.,263.]:
        assert list(map(float,dims[1].split(',')))==[52.,52.,46.];matches.append(m)
assert len(matches)==1
m=matches[0];start=old.rfind('\n',0,m.start())+1;end=old.index('\n',m.end())+1
new=old[:start]+old[end:]
assert 'origin = [ 1320.0000, -380.0000, 263.0000 ]' in new
(STAGE/'Assets'/rel.with_suffix('.vmdl')).write_text(new,encoding='utf-8',newline='')
files=[]
for p in sorted((STAGE/'Assets').rglob('*')):
    if not p.is_file():continue
    relative=p.relative_to(STAGE/'Assets').as_posix();original=ROOT/'Assets'/relative
    files.append({'relative':relative,'after':sha(p),'before':sha(original) if original.exists() else None,
                  'phase':'map' if relative.startswith('models/maps/') else 'resource'})
scene=ROOT/'Assets/scenes/maps/Orion/orion.scene'
manifest={'revision':'approved-reel-v1-and-clear-deck-stair','userApproved':True,'lodTriangles':lods,
    'resource':RESOURCE+'/cable_reel.vmdl','files':files,'sceneSHA256':sha(scene),'sceneRelative':'scenes/maps/Orion/orion.scene',
    'originalMapTriangles':sum(l.startswith('f ') for l in lines),'remainingMapTriangles':sum(l.startswith('f ') for l in keep),
    'removedFaceLines':removed,'removedStairBox':m[0],'approvedPlacementWorld':[1320,-380,240],
    'retainedFirstCollider':True,'removedSecondCollider':True,'sourcePreviewGLBSHA256':report['sha256']}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({'stagedFiles':len(files),'lodTriangles':lods,'removedPlaceholderTriangles':56,'stairColliderRemoved':True,'assetsWritten':False}))

"""Stage the approved native generator and remove only its old 12 render triangles."""
from pathlib import Path
import hashlib,json,re,shutil
import numpy as np
from PIL import Image
ROOT=Path.cwd();HERE=ROOT/'Sources/Orion/generator-trial-v1';OUT=ROOT/'output/orion-generator-installed-20261030';STAGE=OUT/'stage/Assets'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report=json.loads((ROOT/'output/asset-improvement-20261030/orion-generator/export-validation.json').read_text())
assert sha(HERE/'generator_after.glb')==report['sha256']
provenance=json.loads((HERE/'provenance.json').read_text());source=ROOT/provenance['source'];assert sha(source)==provenance['sourceSHA256']
RESOURCE='models/props/orion/generator_v1';MATERIAL='materials/orion/generator_v1'
# Source MTL name: private alias, PBR prefix or image, roughness, metallic, optional linear tint.
definitions={
 'Weathered_slate_powder_coating':('gn_paint','paint',.65,0,None),
 'Graphite_chassis_coating':('gn_skid','skid',.65,0,None),
 'Acoustic_liner_and_EPDM_seals':('gn_rubber','rubber',.65,0,None),
 'Galvanized_fasteners':('gn_zinc','zinc',.4,.95,None),
 'Brushed_stainless_exhaust':('gn_steel','steel',.42,.96,None),
 'Heat_tinted_exhaust_welds':('gn_heat','heat',.55,.7,None),
 'Original_Orion_equipment_plate':('gn_brand','brand.png',.6,.15,None),
 'Service_warning_label':('gn_warning','warning.png',.7,0,None),
 'Recessed_LCD_under_glass':('gn_lcd','display.png',.27,0,None),
 'Muted_safety_yellow':('gn_yellow',None,.57,0,(.52,.36,.055)),
 'Emergency_stop_red_polymer':('gn_red',None,.56,0,(.38,.022,.012)),
 'Status_green_lens':('gn_green',None,.23,0,(.025,.21,.10))}
md=STAGE/MATERIAL;md.mkdir(parents=True,exist_ok=True);modeldir=STAGE/RESOURCE;modeldir.mkdir(parents=True,exist_ok=True)
for name,(alias,prefix,rough,metal,tint) in definitions.items():
    text='"Layer0"\n{\n    shader "shaders/complex.shader"\n    F_SPECULAR "1"\n'
    if prefix and prefix.endswith('.png'):
        shutil.copy2(HERE/'textures'/prefix,md/prefix);text+=f'    TextureColor "{MATERIAL}/{prefix}"\n'
    elif prefix:
        for suffix in ('color','roughness','metallic'):
            p=HERE/'textures'/f'{prefix}_{suffix}.png';shutil.copy2(p,md/p.name)
        p=HERE/'textures'/f'{prefix}_normal.png';n=np.asarray(Image.open(p).convert('RGB'),dtype=np.float32)/127.5-1
        n*=.5;n[:,:,2]+=.5;n/=np.linalg.norm(n,axis=2)[:,:,None]
        Image.fromarray(np.uint8(np.clip((n*.5+.5)*255+.5,0,255))).save(md/p.name)
        text+=f'    TextureColor "{MATERIAL}/{prefix}_color.png"\n    TextureNormal "{MATERIAL}/{prefix}_normal.png"\n'
        text+=f'    TextureRoughness "{MATERIAL}/{prefix}_roughness.png"\n    TextureMetalness "{MATERIAL}/{prefix}_metallic.png"\n'
    else:
        text+='    TextureColor "[1 1 1 1]"\n    g_vColorTint "['+' '.join(map(str,(*tint,1)))+']"\n'
    if not prefix or prefix.endswith('.png'):text+=f'    TextureRoughness "[{rough} {rough} {rough} 0]"\n    g_flMetalness "{metal}"\n'
    if alias=='gn_lcd':text+='    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1 1 1 0]"\n    g_flSelfIllumBrightness "0.45"\n'
    text+='    TextureAmbientOcclusion "[1 1 1 0]"\n    g_flRoughnessScaleFactor "1"\n    g_flModelTintAmount "1"\n}\n'
    (md/f'{alias}.vmat').write_text(text)
lods=[]
for lod in range(4):
    out=[f'mtllib generator_lod{lod}.mtl\n',f'o lod{lod}\n'];used=set();count=0
    for line in (OUT/'raw'/f'lod{lod}.obj').read_text().splitlines():
        p=line.split()
        if not p:continue
        if p[0]=='v':x,y,z=map(float,p[1:]);out.append(f'v {-x/.0254:.7f} {z/.0254:.7f} {y/.0254:.7f}\n')
        elif p[0]=='vn':x,y,z=map(float,p[1:]);out.append(f'vn {-x:.9f} {z:.9f} {y:.9f}\n')
        elif p[0]=='vt':out.append(line+'\n')
        elif p[0]=='usemtl':alias=definitions[p[1]][0];used.add(alias);out.append('usemtl '+alias+'\n')
        elif p[0]=='f':assert len(p)==4;count+=1;out.append(line+'\n')
    assert len(used)==12,(lod,used)
    (modeldir/f'generator_lod{lod}.obj').write_text(''.join(out))
    (modeldir/f'generator_lod{lod}.mtl').write_text(''.join(f'newmtl {a}\nKd 1 1 1\nd 1\n' for a in sorted(used)));lods.append(count)
assert lods[0]==51658 and all(a>b for a,b in zip(lods,lods[1:])),lods
header='<!-- kv3 encoding:text:version{e21c7f3c-8a33-41c5-9977-a76d3a32aa0d} format:modeldoc29:version{3cec427c-1b0e-4d48-a90a-0436f33a6041} -->\n'
remaps='\n'.join(f'{{ from = "{v[0]}.vmat" to = "{MATERIAL}/{v[0]}.vmat" }},' for v in definitions.values())
meshes='\n'.join(f'{{ _class = "RenderMeshFile" name = "lod{l}" filename = "{RESOURCE}/generator_lod{l}.obj" import_translation = [0,0,0] import_rotation = [0,0,0] import_scale = 1.0 align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" parent_bone = "" import_filter = {{ exclude_by_default = false exception_list = [] }} }},' for l in range(4))
groups='\n'.join(f'{{ _class = "LODGroup" switch_threshold = {t:.1f} meshes = ["lod{l}"] }},' for l,t in enumerate((0,24,60,150)))
(modeldir/'generator.vmdl').write_text(header+'{ rootNode = { _class = "RootNode" children = [\n{ _class = "MaterialGroupList" children = [{ _class = "DefaultMaterialGroup" remaps = [\n'+remaps+'\n] use_global_default = false global_default_material = "" }] },\n{ _class = "RenderMeshList" children = [\n'+meshes+'\n] },\n{ _class = "LODGroupList" children = [\n'+groups+'\n] }\n] model_archetype = "" primary_associated_entity = "" base_model_name = "" } }\n')
lines=source.read_bytes().decode().splitlines(keepends=True);vs=[];paint='';keep=[];removed=[];origin=np.array((265.,1335.,240.))
for i,line in enumerate(lines,1):
    p=line.split()
    if p and p[0]=='v':a,z,n=map(float,p[1:]);vs.append(np.array((-a,n,z)))
    elif p and p[0]=='usemtl':paint=p[1]
    elif p and p[0]=='f':
        pts=np.array([vs[int(s.split('/')[0])-1]-origin for s in p[1:]])
        if np.all(np.minimum(abs(pts-np.array((-65,-35,0))),abs(pts-np.array((65,35,70))))<.001):
            assert paint in ('oa_dark','oa_steel');removed.append(i);continue
    keep.append(line)
assert len(removed)==12
rel=Path('models/maps/orion/orion_launch_deck.obj');p=STAGE/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(''.join(keep),newline='')
files=[]
for p in sorted(STAGE.rglob('*')):
    if not p.is_file():continue
    rel=p.relative_to(STAGE).as_posix();original=ROOT/'Assets'/rel
    files.append({'relative':rel,'after':sha(p),'before':sha(original) if original.exists() else None,'phase':'map' if rel.startswith('models/maps/') else 'resource'})
scene=ROOT/'Assets/scenes/maps/Orion/orion.scene'
manifest={'revision':'approved-generator-v1','userApproved':True,'resource':RESOURCE+'/generator.vmdl','files':files,'lodTriangles':lods,
 'sceneRelative':'scenes/maps/Orion/orion.scene','sceneSHA256':sha(scene),'removedFaceLines':removed,'approvedPlacementWorld':[1335,-265,240],
 'sourcePreviewGLBSHA256':report['sha256'],'originalCollisionModelSHA256':sha(source.with_suffix('.vmdl')),'collisionUnchanged':True}
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2));print(json.dumps({'stagedFiles':len(files),'lodTriangles':lods,'removedPlaceholderTriangles':12,'collisionUnchanged':True,'assetsWritten':False}))

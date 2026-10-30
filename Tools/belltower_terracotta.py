"""Stage the pots' dedicated colour, fine ceramic grain and continuous material."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Sources/Belltower/terracotta-v1'
OUT=ROOT/'output/belltower/terracotta-v1'
PREFIX='materials/belltower/terracotta-v1'


def material():
    return ('// Tools/belltower_terracotta.py; dedicated pot finish\n'+
        '"Layer0"\n{\n'+
        '    shader "shaders/belltower_terracotta.shader"\n'+
        '    F_SPECULAR "1"\n'+
        f'    TextureColor "{PREFIX}/clay-albedo-v1.png"\n'+
        f'    TextureNormal "{PREFIX}/clay-normal-v1.png"\n'+
        f'    TextureRoughness "{PREFIX}/clay-roughness-v1.png"\n'+
        '    TextureAmbientOcclusion "materials/default/default_ao.tga"\n'+
        '    g_flClayTileInches "12"\n'+
        '    g_flClayNormalStrength "0.65"\n'+
        '    g_flClayWeathering "0.7"\n'+
        '    g_vColorTint "[0.82 0.86 0.87 1]"\n'+
        '    g_flModelTintAmount "1"\n}\n')


def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--stage',default='stage-v1');args=parser.parse_args()
    assert args.stage.replace('-','').isalnum() and args.stage.startswith('stage-')
    stage=OUT/args.stage;stage.mkdir(parents=True,exist_ok=False)
    private=stage/'Assets'/PREFIX;private.mkdir(parents=True)
    # Export at the engine's required mip dimensions; retain the original ImageGen source.
    with Image.open(SOURCE/'clay-albedo-v1.png') as image:
        image.convert('RGB').resize((2048,2048),Image.Resampling.LANCZOS).save(private/'clay-albedo-v1.png')
    size=2048;rng=np.random.default_rng(2701026)
    fine=gaussian_filter(rng.standard_normal((size,size)).astype(np.float32),1.1,mode='wrap')
    fine/=fine.std()
    broad=gaussian_filter(rng.standard_normal((size,size)).astype(np.float32),12,mode='wrap')
    broad/=broad.std()
    height=fine*.00065+broad*.0007
    # True physical derivatives: 12-inch tile, sub-millimetre fired-clay grain.
    du=(np.roll(height,-1,axis=1)-np.roll(height,1,axis=1))/(24/size)
    dv=(np.roll(height,-1,axis=0)-np.roll(height,1,axis=0))/(24/size)
    normals=np.stack((-du,-dv,np.ones_like(height)),axis=-1)
    normals/=np.linalg.norm(normals,axis=-1,keepdims=True)
    Image.fromarray(np.clip(np.rint((normals*.5+.5)*255),0,255).astype(np.uint8),'RGB').save(private/'clay-normal-v1.png')
    rough=np.clip(.80+.025*broad+.012*fine,.72,.9)
    Image.fromarray(np.rint(rough*255).astype(np.uint8),'L').save(private/'clay-roughness-v1.png')
    shader=stage/'Assets/shaders/belltower_terracotta.shader';shader.parent.mkdir(parents=True)
    shutil.copyfile(SOURCE/'terracotta.shader',shader)
    mat=stage/'Assets/materials/buildings/clay_pot.vmat';mat.parent.mkdir(parents=True)
    mat.write_text(material())
    files={}
    for path in (private/'clay-albedo-v1.png',private/'clay-normal-v1.png',private/'clay-roughness-v1.png',shader,mat):
        relative=path.relative_to(stage).as_posix();target=ROOT/relative
        before=sha(target) if target.exists() else None;backup=stage/'before'/relative
        if before:backup.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,backup)
        files[relative]={'before':before,'after':sha(path),'source':path.relative_to(ROOT).as_posix(),
            'backup':backup.relative_to(ROOT).as_posix() if before else None}
    # Keep shared roof colour and wall-render relief protected. No scene/model writes.
    protected=['Assets/materials/buildings/clay_pot_color.png','Assets/materials/buildings/render_normal.png',
        'Assets/materials/buildings/render_rough.png']
    inputs=['Tools/belltower_terracotta.py','Sources/Belltower/terracotta-v1/terracotta.shader',
        'Sources/Belltower/terracotta-v1/clay-albedo-v1.png']
    manifest={'revision':'belltower-terracotta-v1','stage':args.stage,'files':files,
        'protected_sha256':{p:sha(ROOT/p) for p in protected},'source_sha256':{p:sha(ROOT/p) for p in inputs},
        'normal_pixels':size,'physical_tile_inches':12,'normal_height_rms_inches':float(height.std()),
        'materials_changed':['materials/buildings/clay_pot.vmat'],'geometry_changed':False}
    (stage/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'import-request.json').write_text(json.dumps({'stage':args.stage})+'\n')
    print(json.dumps({'files':len(files),'physical_tile_inches':12,'geometry_changed':False}))


if __name__=='__main__':main()

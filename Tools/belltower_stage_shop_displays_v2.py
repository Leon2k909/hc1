"""Stage the revised physical grocery displays without publishing runtime assets."""
import argparse
import hashlib
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import map_kit as K
import belltower_shop_displays_v2 as S
from belltower_stage_shop_displays import apertures

ROOT=Path(__file__).resolve().parents[1]
RESOURCE='models/maps/belltower/shop-display-v2'
SOURCES=['Tools/belltower_shop_displays_v2.py','Tools/belltower_stage_shop_displays_v2.py',
    'Tools/belltower_soft_props.py',
    'Tools/belltower_shop_displays.py','Tools/belltower_stage_shop_displays.py',
    'Tools/belltower_furniture.py','Tools/map_kit.py',
    'Sources/Belltower/shop-displays/labels-v2.png',
    'Sources/Belltower/shop-displays/shop_display_v2.shader']


def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()


def author_surface_maps(folder):
    """New procedural material maps, not edits of the generated label pixels."""
    rng=np.random.default_rng(271036)
    size=512
    def noise(grid):
        im=Image.fromarray((rng.random((grid,grid))*255).astype('uint8'))
        return np.asarray(im.resize((size,size),Image.Resampling.BICUBIC),float)/255
    field=.36*noise(5)+.31*noise(21)+.20*noise(83)+.13*noise(512)
    fine=noise(512)-.5
    rough=np.clip(.65+field*.27+fine*.10,0,1)
    Image.fromarray((rough*255).astype('uint8')).save(folder/'surface_rough.png')
    # Current stock glass reads roughness directly, unlike legacy complex's
    # scalar control. Keep the sampled glass roughness physically restrained.
    Image.fromarray((rough*.22*255).astype('uint8')).save(folder/'glass_rough.png')
    yy,xx=np.mgrid[:size,:size]
    height=field*.025+fine*.007+np.sin(xx*.64+np.sin(yy*.09))*.0015
    gy,gx=np.gradient(height)
    normal=np.stack((-gx*7,-gy*7,np.ones_like(gx)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(folder/'surface_normal.png')
    paper=np.array((.69,.61,.47))[None,None,:]*(.78+field[...,None]*.33+fine[...,None]*.08)
    Image.fromarray(np.uint8(np.clip(paper,0,1)*255)).save(folder/'paper_color.png')
    oxidation=np.maximum(0,(field-.53)*3)
    tin=np.array((.53,.54,.50))[None,None,:]*(.72+field[...,None]*.45)
    tin=tin*(1-oxidation[...,None]*.43)+np.array((.24,.12,.048))[None,None,:]*oxidation[...,None]*.30
    Image.fromarray(np.uint8(np.clip(tin+fine[...,None]*.055,0,1)*255)).save(folder/'tin_color.png')
    # Simple native text graphics are authored deterministically; engraved
    # product-label artwork is supplied by the separate built-in ImageGen atlas.
    cards=Image.new('RGB',(1024,512));draw=ImageDraw.Draw(cards)
    font_root=Path('C:/Windows/Fonts')
    fonts=[font_root/'georgiab.ttf',font_root/'timesbd.ttf']
    font=next((p for p in fonts if p.exists()),None)
    if font is None:raise FileNotFoundError('A local serif font is required for shelf tickets.')
    heading=ImageFont.truetype(str(font),43);price=ImageFont.truetype(str(font),93)
    for tile,(name,cost) in enumerate((('TEA','9d'),('OLIVE OIL','1/6'),('COFFEE','1/9'),('SALT','3d'))):
        x,y=(tile%2)*512,(tile//2)*256
        draw.rectangle((x,y,x+511,y+255),fill=(210,195,157))
        draw.rectangle((x+15,y+13,x+497,y+243),outline=(72,55,31),width=3)
        draw.text((x+256,y+54),name,font=heading,fill=(48,39,26),anchor='mm')
        draw.text((x+256,y+161),cost,font=price,fill=(48,39,26),anchor='mm')
    cards.save(folder/'price-cards.png')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,default=ROOT/'output/belltower/shop-displays/stage-v5')
    out=parser.parse_args().out.resolve()
    assert out.is_relative_to(ROOT/'output/belltower/shop-displays')
    if out.exists():raise FileExistsError('Preserve prior reviews; choose a new stage directory.')
    source_hashes={p:sha(ROOT/p) for p in SOURCES}
    town_hashes={f'Assets/models/maps/belltower/belltower_{side}.{ext}':
        sha(ROOT/f'Assets/models/maps/belltower/belltower_{side}.{ext}')
        for side in ('centre','west','east') for ext in ('obj','vmdl')}
    records=apertures(ROOT/'Assets/models/maps/belltower/belltower_west.obj')
    model=K.Model()
    for record in records:
        S.build(model,**{k:record[k] for k in ('origin','outward','width','height')})
        # Build the other side in its own outward frame. A geometry reflection
        # would reverse printed labels and repeat the same shelf inventory.
        opposite={k:record[k] for k in ('origin','outward','width','height')}
        opposite['origin']=[-record['origin'][0],*record['origin'][1:]]
        opposite['outward']=[-record['outward'][0],*record['outward'][1:]]
        S.build(model,**opposite)
    assert not model.boxes and not model.hulls and not model.props
    for paint,faces in model.polygons.items():
        for i,(points,normal) in enumerate(faces):
            assert np.isfinite(points).all()
            assert np.dot(np.cross(points[1]-points[0],points[2]-points[0]),normal)>0
            uv=model.polygon_uvs.get((paint,i))
            if paint in ('shop2_labels','shop2_prices'):
                assert uv is not None and np.isfinite(uv).all()
                assert all(0<=u<=1 and 0<=v<=1 for u,v in uv)
    folder=out/'Assets'/RESOURCE;folder.mkdir(parents=True)
    K.write_obj(folder/'shop_displays.obj',model,'shop_displays_v2')
    K.write_vmdl(folder/'shop_displays.vmdl',RESOURCE,'shop_displays',model)
    material_folder=out/'Assets'/S.RESOURCE;material_folder.mkdir(parents=True)
    shader=out/'Assets/shaders/belltower_shop_display_v2.shader';shader.parent.mkdir(parents=True)
    shader.write_bytes((ROOT/'Sources/Belltower/shop-displays/shop_display_v2.shader').read_bytes())
    author_surface_maps(material_folder)
    (material_folder/'labels-v2.png').write_bytes((ROOT/'Sources/Belltower/shop-displays/labels-v2.png').read_bytes())
    for paint in S.COLOURS:
        (out/'Assets'/S.material_path(paint)).write_text(S.material_text(paint),encoding='utf8',newline='\n')
    for key in 'abc':
        p=out/f'Assets/materials/belltower/shopfront_{key}.vmat';p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(S.glass_material_text(),encoding='utf8',newline='\n')
    for group in (source_hashes,town_hashes):
        assert all(sha(ROOT/p)==v for p,v in group.items()),'Shared source changed during staging.'
    files={}
    for p in (out/'Assets').rglob('*'):
        if p.is_file():
            rel=p.relative_to(out).as_posix();live=ROOT/rel
            files[rel]={'before':sha(live) if live.exists() else None,'after':sha(p)}
    manifest={'revision':'shop-displays-v2','displays':18,'west_apertures':records,
        'triangles':model.triangle_count(),'material_count':len(model.polygons),'new_colliders':0,
        'town_models_rebuilt':False,'model_path':RESOURCE+'/shop_displays.vmdl','files':files,
        'source_sha256':source_hashes,'town_model_sha256':town_hashes,
        'staging_scene_sha256':sha(ROOT/'Assets/scenes/maps/Belltower/belltower.scene'),
        'integration':'One visual-only ModelRenderer on existing identity-transform Town, replacing any older supplemental display model; clear glass replaces the three photo materials.',
        'independent_east_dressing':True,
        'native_compilation_verified':False,'native_visual_validation':False,
        'construction_renderer_matches':'Exact staged display OBJ, texture atlas and material property values. Frame context is extracted from current town geometry; shader approximations are not native captures.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'stage':str(out),'displays':18,'triangles':manifest['triangles'],
        'materials':manifest['material_count'],'files':len(files),'published':False}))


if __name__=='__main__':main()

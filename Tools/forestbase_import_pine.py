"""Import Poly Haven's CC0 Pine Tree 01 with its authored LODs and PBR materials.
Source: https://polyhaven.com/a/pine_tree_01. Downloads cached locally; 1K is ample for distant trees.
"""
import json, urllib.request, hashlib, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
import map_kit as K

OUT=K.ASSETS/'models/maps/forestbase/pine'
RES='models/maps/forestbase/pine'
UA={'User-Agent':'HC1 Forest Base Asset Importer/1.0'}

def fetch(url,path,md5=None):
    if path.exists() and (not md5 or hashlib.md5(path.read_bytes()).hexdigest()==md5): return
    path.parent.mkdir(parents=True,exist_ok=True)
    data=urllib.request.urlopen(urllib.request.Request(url,headers=UA),timeout=60).read()
    if md5 and hashlib.md5(data).hexdigest()!=md5: raise ValueError('Download checksum mismatch: '+url)
    path.write_bytes(data)

def main():
    files=json.loads(urllib.request.urlopen(urllib.request.Request('https://api.polyhaven.com/files/pine_tree_01',headers=UA)).read())
    source=K.ASSETS.parent/'Sources/ForestBase'
    blend=files['blend']['1k']['blend']; fetch(blend['url'],source/'pine.blend',blend['md5'])
    spec=files['gltf']['1k']['gltf']
    def download(entry):
        name,s=entry; fetch(s['url'],OUT/name,s['md5'])
    with ThreadPoolExecutor(max_workers=6) as pool: list(pool.map(download,[(n,s) for n,s in spec['include'].items() if not n.endswith('.bin')]))
    blender=r'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe'
    for script in ('forestbase_pine_blender.py','forestbase_pine_impostors.py'):
        subprocess.run([blender,'--background',str(source/'pine.blend'),'--python',str(Path(__file__).with_name(script))],check=True)
    (OUT/'LICENSE.txt').write_text('Pine Tree 01 by Rico Cilliers / Rob Tuytel, Poly Haven. CC0 1.0.\nhttps://polyhaven.com/a/pine_tree_01\nhttps://polyhaven.com/license\n',encoding='utf-8')
    finalize()

def finalize():
    files=json.loads(urllib.request.urlopen(urllib.request.Request('https://api.polyhaven.com/files/pine_tree_01',headers=UA)).read())
    alpha=files['twig_alpha']['1k']['png']; fetch(alpha['url'],OUT/'textures/twig_alpha.png',alpha['md5'])
    names=['bark','trunk_a','twig','dead_branches','trunk_b','trunk_c']
    for name in names:
        source='bark' if name in ('dead_branches','trunk_c') else name
        prefix=f'pine_tree_01_{source}'
        arm=np.array(Image.open(OUT/f'textures/{prefix}_arm_1k.jpg').convert('RGB'))
        for prop,channel in [('ao',0),('rough',1)]: Image.fromarray(arm[:,:,channel]).save(OUT/f'textures/{name}_{prop}.png')
        lines=['"Layer0"','{',' shader "shaders/complex.shader"',' F_SPECULAR "1"',' F_RENDER_BACKFACES "1"']
        for prop,file in [('Color',prefix+'_diff_1k.jpg'),('Normal',prefix+'_nor_gl_1k.jpg'),('Roughness',name+'_rough.png'),('AmbientOcclusion',name+'_ao.png')]:
            lines.append(f' Texture{prop} "{RES}/textures/{file}"')
        # The atlas contains cutout twigs as well as opaque branch/needle islands.
        # Its authored mask removes the solid dark borders around twig clusters.
        if name=='twig':
            lines += [' F_ALPHA_TEST "1"',f' TextureTranslucency "{RES}/textures/twig_alpha.png"',' g_flAlphaTestReference "0.25"']
        lines += ['}']; K.write_text(OUT/f'pine_tree_01_{name}.vmat','\n'.join(lines)+'\n')
    template=(K.ASSETS/'models/grass/grass_tuft.vmdl').read_text()
    card=(OUT/'pine_tree_01_twig.vmat').read_text()
    K.write_text(OUT/'twig_card.vmat',card)
    import math
    for variant in 'abc':
        for angle in (0,90):
            path=OUT/f'impostor_{variant}_{angle}.png'
            if not path.exists(): continue
            rgba=np.array(Image.open(path).convert('RGBA'))
            rgb=np.clip(rgba[:,:,:3].astype(float)*1.55,0,255).astype('uint8')
            Image.fromarray(rgb).save(OUT/f'impostor_{variant}_{angle}_color.png')
            Image.fromarray(rgba[:,:,3]).save(OUT/f'impostor_{variant}_{angle}_alpha.png')
            K.write_text(OUT/f'impostor_{variant}_{angle}.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_ALPHA_TEST "1"
 F_RENDER_BACKFACES "1"
 TextureColor "{RES}/impostor_{variant}_{angle}_color.png"
 TextureTranslucency "{RES}/impostor_{variant}_{angle}_alpha.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[.85 .85 .85 0]"
 g_flAlphaTestReference "0.28"
}}
''')
    # Full geometric crowns at close/mid distance; whole-tree impostors only in the far LOD.
    for variant in 'abc':
        for lod in range(3):
            crown=K.Model(); crown.material_overrides['twig_card']=f'{RES}/twig_card.vmat'; crown.tile_overrides['twig_card']=64
            if (OUT/f'impostor_{variant}_0.png').exists():
                for j,angle in enumerate((0,60,120)):
                    paint=f'impostor_{variant}_{0 if j!=1 else 90}'
                    crown.material_overrides[paint]=f'{RES}/{paint}.vmat'
                    crown.tile_overrides[paint]=64
                    a=math.radians(angle); side=np.array((math.cos(a),math.sin(a),0))*216
                    crown.polygon(paint,[-side,side,side+(0,0,864),-side+(0,0,864)],
                                  uv=((0,0),(1,0),(1,1),(0,1)),both_sides=True)
                K.write_model(OUT,RES,f'crown_{variant}_lod{lod}',crown)
                continue
            rng=np.random.default_rng(ord(variant)); tiers=(32,28,24)[lod]; arms=(11,10,9)[lod]
            for k,z in enumerate(np.linspace(110,790,tiers)):
                radius=(185*(1-z/810)**.65+8)*rng.uniform(.8,1.14)
                for j in range(arms):
                    angle=j*2*math.pi/arms+k*2.399+rng.uniform(-.2,.2)
                    forward=np.array((math.cos(angle),math.sin(angle),0)); side=np.cross((0,0,1),forward)
                    for f in (.3,.6,.9):
                        origin=forward*radius*f+(0,0,z-radius*f*.22)
                        for turn in (-.8,.8):
                            direction=forward*math.cos(turn)+side*math.sin(turn)+(0,0,rng.uniform(-.25,.35))
                            direction/=np.linalg.norm(direction)
                            lateral=np.cross(direction,(0,0,1)); lateral/=np.linalg.norm(lateral)
                            length=radius*.75+14
                            tip=origin+direction*length
                            width=length*.58
                            pts=[origin-lateral*width/2,origin+lateral*width/2,tip+lateral*width/2,tip-lateral*width/2]
                            # Top-left twig in the source atlas. OBJ v is up; atlas y is down.
                            crown.polygon('twig_card',pts,both_sides=True,uv=((.015,.54),(.237,.54),(.237,.99),(.015,.99)))
            K.write_model(OUT,RES,f'crown_{variant}_lod{lod}',crown)
    for variant in 'abc':
        remaps=',\n'.join(f'{{ from = "pine_tree_01_{name}.vmat" to = "{RES}/pine_tree_01_{name}.vmat" }}' for name in names)
        remaps+=f',\n{{ from = "twig_card.vmat" to = "{RES}/twig_card.vmat" }}'
        for angle in (0,90): remaps+=f',\n{{ from = "impostor_{variant}_{angle}.vmat" to = "{RES}/impostor_{variant}_{angle}.vmat" }}'
        text=template.replace('remaps = [ ] use_global_default = true global_default_material = "models/grass/grass.vmat"',
                              f'remaps = [ {remaps} ] use_global_default = false global_default_material = ""')
        for lod in range(3): text=text.replace(f'models/grass/grass_tuft_lod{lod}.obj',f'{RES}/pine_{variant}_lod{lod}.obj')
        # Additional render meshes participate in the same LOD switch as the branch skeleton.
        start=text.index('   { _class = "RenderMeshList"'); end=text.index('   { _class = "LODGroupList"')
        entries=[]
        for lod in range(3):
            meshes=[(f'lod{lod}',f'pine_{variant}_lod{lod}')]
            if lod==2: meshes.append((f'crown{lod}',f'crown_{variant}_lod{lod}'))
            for mesh,filename in meshes:
                entries.append(f'    {{ _class = "RenderMeshFile" name = "{mesh}" filename = "{RES}/{filename}.obj" import_scale = 1.0 import_translation = [0,0,0] import_rotation = [0,0,0] align_origin_x_type = "None" align_origin_y_type = "None" align_origin_z_type = "None" }}')
            if lod==2: text=text.replace(f'meshes = [ "lod{lod}" ]',f'meshes = [ "lod{lod}", "crown{lod}" ]')
        text=text[:start]+'   { _class = "RenderMeshList" children = [\n'+',\n'.join(entries)+'\n   ] },\n'+text[end:]
        text=text.replace('switch_threshold = 10.0','switch_threshold = 50.0').replace('switch_threshold = 25.0','switch_threshold = 110.0')
        K.write_text(OUT/f'pine_{variant}.vmdl',text)
    print('Pine game LOD models and PBR materials written.')

if __name__=='__main__':
    import sys
    finalize() if '--finalize' in sys.argv else main()

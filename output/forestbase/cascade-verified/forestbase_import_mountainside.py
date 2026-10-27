"""Import Poly Haven Mountainside (CC0), with original proportions and PBR scan maps."""
import json,subprocess,urllib.request
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
import map_kit as K
from forestbase_import_pine import fetch,UA
OUT=K.ASSETS/'models/maps/forestbase/mountainside'
SOURCE=K.ROOT/'Sources/ForestBase/mountainside'
RES='models/maps/forestbase/mountainside'
def main():
    files=json.load(urllib.request.urlopen(urllib.request.Request('https://api.polyhaven.com/files/mountainside',headers=UA)))
    spec=files['gltf']['2k']['gltf'];fetch(spec['url'],SOURCE/'source.gltf',spec['md5'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item:fetch(item[1]['url'],SOURCE/item[0],item[1]['md5']),spec['include'].items()))
    OUT.mkdir(parents=True,exist_ok=True)
    for suffix in ('diff','nor_gl','arm'):
        Image.open(SOURCE/f'textures/mountainside_{suffix}_2k.jpg').save(OUT/f'{suffix}.jpg',quality=95)
    arm=np.asarray(Image.open(OUT/'arm.jpg'))
    for name,channel in (('ao',0),('rough',1)):Image.fromarray(arm[:,:,channel]).save(OUT/f'{name}.png')
    K.write_text(OUT/'cliff.vmat',f'''"Layer0"
{{
 shader "shaders/forestbase_cascade_rock.shader"
 F_SPECULAR "1"
 TextureColor "{RES}/diff.jpg"
 TextureNormal "{RES}/nor_gl.jpg"
 TextureRoughness "{RES}/rough.png"
 TextureAmbientOcclusion "{RES}/ao.png"
}}
''')
    subprocess.run(['C:/Program Files/Blender Foundation/Blender 5.2/blender.exe','--background','--python',str(K.ROOT/'Tools/forestbase_mountainside_blender.py')],check=True)
    template=(K.ASSETS/'models/grass/grass_tuft.vmdl').read_text().replace('models/grass/grass.vmat',f'{RES}/cliff.vmat')
    for lod in range(3):template=template.replace(f'models/grass/grass_tuft_lod{lod}.obj',f'{RES}/cliff_lod{lod}.obj')
    template=template.replace('switch_threshold = 10.0','switch_threshold = 900.0').replace('switch_threshold = 25.0','switch_threshold = 2200.0')
    K.write_text(OUT/'cliff.vmdl',template)
    K.write_text(OUT/'LICENSE.txt','Mountainside, Poly Haven. Dario Barresi / Rico Cilliers. CC0 1.0.\nhttps://polyhaven.com/a/mountainside\nhttps://polyhaven.com/license\n')
    (K.ROOT/'output/forestbase/mountainside-downloads.json').write_text(json.dumps(spec,indent=2))
if __name__=='__main__':main()

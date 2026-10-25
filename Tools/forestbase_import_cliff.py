"""Import a CC0 scanned cliff, retaining UVs and three modest game LODs."""
import json, subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from PIL import Image
import map_kit as K
from forestbase_import_pine import fetch, UA
import urllib.request
import sys

NAME=sys.argv[1] if len(sys.argv)>1 else 'coastal_cliff_01'
KIND='boulder' if NAME=='boulder_01' else 'cliff'
OUT=K.ASSETS/f'models/maps/forestbase/{KIND}'
RES=f'models/maps/forestbase/{KIND}'
SOURCE=K.ASSETS.parent/f'Sources/ForestBase/{KIND}'

def main():
    files=json.load(urllib.request.urlopen(urllib.request.Request(f'https://api.polyhaven.com/files/{NAME}',headers=UA)))
    spec=files['gltf']['2k']['gltf']
    fetch(spec['url'],SOURCE/'cliff.gltf',spec['md5'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda item:fetch(item[1]['url'],SOURCE/item[0],item[1]['md5']),spec['include'].items()))
    OUT.mkdir(parents=True,exist_ok=True)
    for suffix in ('diff','nor_gl','arm'):
        Image.open(SOURCE/f'textures/{NAME}_{suffix}_2k.jpg').save(OUT/f'{suffix}.jpg',quality=95)
    arm=np.array(Image.open(OUT/'arm.jpg'))
    for p,c in [('ao',0),('rough',1)]: Image.fromarray(arm[:,:,c]).save(OUT/f'{p}.png')
    K.write_text(OUT/'cliff.vmat',f'''"Layer0"
{{
 shader "shaders/complex.shader"
 F_SPECULAR "1"
 g_vColorTint "[.67 .74 .70 1]"
 g_flRoughnessScaleFactor "1.4"
 TextureColor "{RES}/diff.jpg"
 TextureNormal "{RES}/nor_gl.jpg"
 TextureRoughness "{RES}/rough.png"
 TextureAmbientOcclusion "{RES}/ao.png"
}}
''')
    subprocess.run([r'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe','--background','--python',str(Path(__file__).with_name('forestbase_cliff_blender.py')),'--',KIND],check=True)
    template=(K.ASSETS/'models/grass/grass_tuft.vmdl').read_text()
    template=template.replace('models/grass/grass.vmat',f'{RES}/cliff.vmat')
    for lod in range(3): template=template.replace(f'models/grass/grass_tuft_lod{lod}.obj',f'{RES}/cliff_lod{lod}.obj')
    K.write_text(OUT/'cliff.vmdl',template)
    K.write_text(OUT/'LICENSE.txt',f'{NAME}, Poly Haven. CC0 1.0.\nhttps://polyhaven.com/a/{NAME}\nhttps://polyhaven.com/license\n')

if __name__=='__main__': main()

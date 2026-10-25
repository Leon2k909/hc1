"""Cache verified Poly Haven CC0 surface scans for Forest Base, 2K maps."""
import json, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import map_kit as K
from forestbase_import_pine import fetch, UA

OUT=K.ASSETS/'materials/forestbase/scans'
RES='materials/forestbase/scans'
ASSETS=['asphalt_02','concrete_floor_02','concrete_wall_007','wood_planks','corrugated_iron_02','metal_plate_02','container_side','muddy_tracks','mud_forest']

def main(selected=None):
    OUT.mkdir(parents=True,exist_ok=True)
    for asset in selected or ASSETS:
        try:
            data=json.loads(urllib.request.urlopen(urllib.request.Request('https://api.polyhaven.com/files/'+asset,headers=UA),timeout=30).read())
        except Exception as e:
            print(asset,e); continue
        jobs=[]; maps={}
        for suffix,prop in [('diff','Color'),('nor_gl','Normal'),('rough','Roughness'),('ao','AmbientOcclusion'),('metal','Metalness')]:
            alternatives={'diff':('diff','diffuse','albedo','color','col'),'rough':('rough','roughness')}.get(suffix,(suffix,))
            key=next((k for k in data if k.lower() in alternatives or any(k.lower().endswith('_'+s) for s in alternatives)),None)
            if key is None: continue
            choices=data[key]['2k']; ext='jpg' if 'jpg' in choices else 'png'; s=choices[ext]
            path=OUT/f'{asset}_{suffix}.{ext}'; jobs.append((s,path)); maps[prop]=f'{RES}/{path.name}'
        with ThreadPoolExecutor(max_workers=4) as pool:
            list(pool.map(lambda job:fetch(job[0]['url'],job[1],job[0]['md5']),jobs))
        material=['"Layer0"','{',' shader "shaders/complex.shader"',' F_SPECULAR "1"']
        material += [f' Texture{p} "{v}"' for p,v in maps.items()]
        if 'Metalness' not in maps: material += [' TextureMetalness "[0 0 0 0]"']
        if asset=='concrete_wall_007':
            material=[line.replace('shaders/complex.shader','shaders/forestbase_facade.shader') for line in material]
            material += [' g_flTintColor "[.87 .91 .96]"']
        if asset=='asphalt_02':
            material=[line.replace('shaders/complex.shader','shaders/forestbase_wetground.shader') for line in material]
            material += [' TextureMetalness "[0 0 0 0]"',' g_flTintColor "[.7 .74 .76]"']
        if asset=='container_side': material += [' g_vColorTint "[.44 .48 .32 1]"']
        if asset=='metal_plate_02': material += [' g_vColorTint "[.28 .32 .32 1]"']
        if asset=='muddy_tracks':
            material=[line.replace('shaders/complex.shader','shaders/forestbase_mud.shader') for line in material]
            material+=[' TextureMetalness "[0 0 0 0]"',' g_flTintColor "[.60 .65 .65]"']
        material += ['}']
        K.write_text(OUT/f'{asset}.vmat','\n'.join(material)+'\n')
        print('Imported',asset)
    sources=['https://polyhaven.com/a/'+asset for asset in ASSETS if (OUT/f'{asset}.vmat').exists()]
    K.write_text(OUT/'LICENSE.txt','Poly Haven surface scans, CC0 1.0.\n'+'\n'.join(sources)+'\nhttps://polyhaven.com/license\n')

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('assets',nargs='*',metavar='ASSET',help='Optional asset names; omit to import the full palette.')
    args=parser.parse_args()
    unknown=set(args.assets)-set(ASSETS)
    if unknown: parser.error('Unknown surface asset: '+', '.join(sorted(unknown)))
    main(args.assets)

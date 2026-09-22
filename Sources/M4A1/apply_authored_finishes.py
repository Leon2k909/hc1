"""Apply the reviewed imagegen atlases after baking the matching, unchanged UVs.

Regenerate the authored color atlases if build_parts.py changes the UV layout.
Only material references/parameters are edited; the raster images are untouched.
"""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
for name in ['heavy_barrel','precision_stock']:
    folder=ROOT/f'Assets/attachments/m4a1/{name}'
    assert (folder/f'{name}_color_authored.png').is_file()
    roughness='.85' if name=='precision_stock' else '1'
    tint='0.65 0.65 0.65 1' if name=='precision_stock' else '1 1 1 1'
    channels=[('Color','color_authored'),('Normal','normal'),('Roughness','roughness'),('Metalness','metalness'),('AmbientOcclusion','ao')]
    text='"Layer0"\n{\n shader "shaders/complex.shader"\n F_SPECULAR "1"\n F_METALNESS_TEXTURE "1"\n'
    text+=f' g_flRoughnessScaleFactor "{roughness}"\n g_vColorTint "[{tint}]"\n'
    text+=''.join(f' Texture{key} "attachments/m4a1/{name}/{name}_{value}.png"\n' for key,value in channels)+'}\n'
    (folder/f'{name}.vmat').write_text(text,encoding='utf8')
    print('Applied authored finish:',name)

from pathlib import Path
o=Path('output/veridant/gallery-art-v1')
s=Path('output/veridant/lounge-tables-v1/prepare.py').read_text().replace('veridant_lounge_table as B','veridant_gallery_art as B').replace('lounge-tables-v1','gallery-art-v1').replace('lounge_coffee_table','gallery_art').replace('coffee_table','art')
s=s.replace("for c in [(-420,-390),(-580,-390)]:P.cylinder(old,c,16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.art(old,'art_1',(-497,-543.8,196),(-1,0,0),52)")
s=s.replace("P.cylinder(original,(0,0),16,0,16,'vr_stone_dark',14,top='vr_stone_dark')","P.art(original,'art_1',(0,0,0),(-1,0,0),52)")
s=s.replace("for i,y in enumerate((420,580)):","for i,y in enumerate((497,)):").replace("'Lounge coffee table '","'Gallery coastal painting '").replace("f'-390,{y},0'","f'-543.8,{y},196'")
s=s.replace('sbox.2026.11.06.14.08.40.png','sbox.2026.11.06.16.09.24.png')
s+='''\nimport shutil
md=OUT/'stage/materials/veridant/gallery-art-v1';md.mkdir(parents=True,exist_ok=True)
shutil.copy2(Path('C:/Users/leon2/.codex/generated_images/01a1ac9b-89d5-7aa3-8fe2-8ad23ca89dc1/exec-5d8cb7c8-0609-49be-850e-9034fd0fe2f4.png'),md/'coastal.png')
(md/'coastal.vmat').write_text('Layer0\\n{\\n shader "shaders/complex.shader"\\n TextureColor "materials/veridant/gallery-art-v1/coastal.png"\\n TextureNormal "materials/default/default_normal.tga"\\n TextureRoughness "[0.9 0.9 0.9 0]"\\n g_flMetalness "0"\\n g_vColorTint "[1 1 1 1]"\\n}\\n')
'''
(o/'prepare.py').write_text(s)

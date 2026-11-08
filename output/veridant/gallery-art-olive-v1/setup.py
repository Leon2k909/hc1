from pathlib import Path
s=Path('output/veridant/gallery-art-v1/prepare.py').read_text()
s=s.replace('veridant_gallery_art as B','veridant_gallery_art_olive as B').replace('gallery-art-v1','gallery-art-olive-v1').replace('gallery_art_v1','gallery_art_olive_v1').replace('gallery_art_original_v1','gallery_art_olive_original_v1').replace("'art_1'","'art_2'").replace('-497','-433').replace('(497,)','(433,)').replace('Gallery coastal painting','Gallery olive painting').replace('coastal','olive').replace('exec-5d8cb7c8-0609-49be-850e-9034fd0fe2f4.png','exec-3f9ca237-847f-4352-8000-e3bdf2c5df2d.png').replace('sbox.2026.11.06.16.09.24.png','sbox.2026.11.06.16.16.31.png')
Path('output/veridant/gallery-art-olive-v1/prepare.py').write_text(s)

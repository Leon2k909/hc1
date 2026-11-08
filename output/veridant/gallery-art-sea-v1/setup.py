from pathlib import Path
s=Path('output/veridant/gallery-art-v1/prepare.py').read_text()
s=s.replace('veridant_gallery_art as B','veridant_gallery_art_sea as B').replace('gallery-art-v1','gallery-art-sea-v1').replace('gallery_art_v1','gallery_art_sea_v1').replace('gallery_art_original_v1','gallery_art_sea_original_v1')
s=s.replace("P.art(old,'art_1',(-497,-543.8,196),(-1,0,0),52)","P.art(old,'art_5',(-703.8,-370,192),(0,1,0),50)")
s=s.replace("P.art(original,'art_1',(0,0,0),(-1,0,0),52)","P.art(original,'art_5',(0,0,0),(0,1,0),50)")
s=s.replace('(497,)','(703.8,)').replace("f'-543.8,{y},196'","f'-370,{y},192'").replace('Gallery coastal painting','Gallery sea painting').replace('coastal','sea').replace('exec-5d8cb7c8-0609-49be-850e-9034fd0fe2f4.png','exec-f451df6a-7bd1-4dd5-83d5-e61b3b579dff.png').replace('sbox.2026.11.06.16.09.24.png','sbox.2026.11.06.16.22.10.png')
Path('output/veridant/gallery-art-sea-v1/prepare.py').write_text(s)

from pathlib import Path
s=Path('Tools/veridant_gallery_art_sea.py').read_text().replace('art_5','art_3').replace('(0,1,0),50','(0,-1,0),44').replace('e+1.02','e-1.02').replace('[(-18.75,-25),(18.75,-25),(18.75,25),(-18.75,25)]','[(44,-22),(-44,-22),(-44,22),(44,22)]').replace('((1,0,0))','((-1,0,0))').replace('gallery-art-sea-v1/sea','gallery-art-garden-v1/garden')
Path('Tools/veridant_gallery_art_garden.py').write_text(s)
s=Path('output/veridant/gallery-art-sea-v1/prepare.py').read_text().replace('veridant_gallery_art_sea','veridant_gallery_art_garden').replace('gallery-art-sea-v1','gallery-art-garden-v1').replace('gallery_art_sea','gallery_art_garden')
s=s.replace("P.art(old,'art_5',(-703.8,-370,192),(0,1,0),50)","P.art(old,'art_3',(-216.2,-460,196),(0,-1,0),44)").replace("P.art(original,'art_5',(0,0,0),(0,1,0),50)","P.art(original,'art_3',(0,0,0),(0,-1,0),44)")
s=s.replace('(703.8,)','(216.2,)').replace("f'-370,{y},192'","f'-460,{y},196'").replace('Gallery sea painting','Gallery garden painting').replace('sea.png','garden.png').replace('sea.vmat','garden.vmat').replace('exec-f451df6a-7bd1-4dd5-83d5-e61b3b579dff.png','exec-5e19ef85-3199-407a-8306-af78a24ce0bc.png').replace('sbox.2026.11.06.16.22.10.png','sbox.2026.11.06.16.30.25.png')
Path('output/veridant/gallery-art-garden-v1/prepare.py').write_text(s)

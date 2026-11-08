from pathlib import Path
s=Path('Tools/veridant_gallery_art_sea.py').read_text().replace('art_5','art_4').replace('(0,1,0),50','(0,1,0),44').replace('[(-18.75,-25),(18.75,-25),(18.75,25),(-18.75,25)]','[(-22,-22),(22,-22),(22,22),(-22,22)]').replace('gallery-art-sea-v1/sea','operations-art-v1/still-life')
Path('Tools/veridant_operations_art.py').write_text(s)
s=Path('output/veridant/gallery-art-sea-v1/prepare.py').read_text().replace('veridant_gallery_art_sea','veridant_operations_art').replace('gallery-art-sea-v1','operations-art-v1').replace('gallery_art_sea','operations_art')
s=s.replace("P.art(old,'art_5',(-703.8,-370,192),(0,1,0),50)","P.art(old,'art_4',(142,-560,186),(0,-1,0),44)").replace("P.art(original,'art_5',(0,0,0),(0,1,0),50)","P.art(original,'art_4',(0,0,0),(0,-1,0),44)")
s=s.replace('(703.8,)','(-142,)').replace("f'-370,{y},192'","f'-560,{y},186'").replace('Gallery sea painting','Operations still life').replace('sea.png','still-life.png').replace('sea.vmat','still-life.vmat').replace('exec-f451df6a-7bd1-4dd5-83d5-e61b3b579dff.png','exec-0fa6ceb3-39ea-434b-94d6-a4465cf62822.png').replace('sbox.2026.11.06.16.22.10.png','sbox.2026.11.06.16.36.25.png')
Path('output/veridant/operations-art-v1/prepare.py').write_text(s)

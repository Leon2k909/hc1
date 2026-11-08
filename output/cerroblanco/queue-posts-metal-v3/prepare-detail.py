from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/queue-posts-metal-v3'
s=(o/'capture.py').read_text().replace('1010,-165,58','1028,-180,46').replace("'angles':'14,-33,0'","'angles':'24,-43,0'")
(o/'detail.py').write_text(s)

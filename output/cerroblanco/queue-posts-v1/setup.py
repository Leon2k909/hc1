from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/queue-posts-v1'
s=(R/'output/cerroblanco/cafe-display-v1/capture.py').read_text().replace('515,-655,64','1010,-165,58').replace("'angles':'8,0,0'","'angles':'14,-33,0'")
(o/'capture.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(o/n).write_text((R/'output/cerroblanco/cafe-display-v1'/n).read_text().replace('cafe-display-v1','queue-posts-v1'))

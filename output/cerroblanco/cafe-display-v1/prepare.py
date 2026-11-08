from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/cafe-display-v1';o.mkdir(exist_ok=True)
s=(R/'output/cerroblanco/cafe-grinder-v1/capture.py').read_text().replace('568,-606,62','558,-655,64')
(o/'capture.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(o/n).write_text((R/'output/cerroblanco/cafe-grinder-v1'/n).read_text().replace('cafe-grinder-v1','cafe-display-v1'))

from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'Sources/CerroBlanco/queue-posts-v1'
s=(R/'Sources/CerroBlanco/pan-dulce-v1/verify.py').read_text().replace("'unrelated_faces_preserved':74040","'unrelated_faces_preserved':89504")
(o/'verify.py').write_text(s)

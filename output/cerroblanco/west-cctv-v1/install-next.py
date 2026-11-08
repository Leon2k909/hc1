from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'output/cerroblanco/west-cctv-v1'
s=(R/'output/cerroblanco/courtyard-cctv-v1/install-next.py').read_text();s=s[:s.index("d=R/'Sources/CerroBlanco/west-cctv-v1'")]
s=s.replace('courtyard-cctv-v1','west-cctv-v1').replace('cerroblanco_courtyard_cctv','cerroblanco_west_cctv').replace('(480,-1000,200)','(-1126,-160,200)');(o/'install-approved.py').write_text(s)
d=R/'Sources/CerroBlanco/north-cctv-v1';d.mkdir(exist_ok=True);out=R/'output/cerroblanco/north-cctv-v1';out.mkdir(exist_ok=True)
s=(R/'Sources/CerroBlanco/west-cctv-v1/model.py').read_text().replace('(-1126.,-160.,200.)','(2060.,715.,200.)').replace('out=P.unit((-1,-1,0))','out=P.unit((1,1,0))');(d/'model.py').write_text(s)
s=(R/'Sources/CerroBlanco/west-cctv-v1/build.py').read_text().replace('west-cctv-v1','north-cctv-v1').replace('west_cctv_v1','north_cctv_v1').replace('(-1126,-160,200),(-1,-1)','(2060,715,200),(1,1)');(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(out/n).write_text((R/'output/cerroblanco/west-cctv-v1'/n).read_text().replace('west-cctv-v1','north-cctv-v1'))
(out/'capture.py').write_text((R/'output/cerroblanco/west-cctv-v1/capture.py').read_text().replace('-205,1180,180','760,-2110,180').replace("'angles':'-14,-50,0'","'angles':'-14,130,0'"))

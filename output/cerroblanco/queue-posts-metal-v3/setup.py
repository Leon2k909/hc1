from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');src=R/'Sources/CerroBlanco/queue-posts-metal-v2';dest=R/'Sources/CerroBlanco/queue-posts-metal-v3';dest.mkdir(exist_ok=True)
for n in ['model.py','build.py','verify.py']:(dest/n).write_text((src/n).read_text().replace('queue-posts-metal-v2','queue-posts-metal-v3').replace('queue_posts_metal_v2','queue_posts_metal_v3'))
p=dest/'model.py';s=p.read_text();s=s.replace('uv=[(math.atan2(v[1]-c[1],v[0]-c[0])/math.tau,(v[2])/8) for v in pts]',"uv=([(a/math.tau,(z0-2.65)/33.15),(b/math.tau,(z0-2.65)/33.15),(b/math.tau,(z1-2.65)/33.15),(a/math.tau,(z1-2.65)/33.15)][1:] if r0==0 else [(a/math.tau,(z0-2.65)/33.15),(b/math.tau,(z0-2.65)/33.15),(b/math.tau,(z1-2.65)/33.15)] if r1==0 else [(a/math.tau,(z0-2.65)/33.15),(b/math.tau,(z0-2.65)/33.15),(b/math.tau,(z1-2.65)/33.15),(a/math.tau,(z1-2.65)/33.15)])")
p.write_text(s)
o=R/'output/cerroblanco/queue-posts-metal-v3'
for n in ['import.json','compile.json','show.json','restore.json','capture.py','material-check.json']:(o/n).write_text((R/'output/cerroblanco/queue-posts-metal-v2'/n).read_text().replace('queue-posts-metal-v2','queue-posts-metal-v3'))

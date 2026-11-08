from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');src=R/'Sources/CerroBlanco/queue-posts-v1';dest=R/'Sources/CerroBlanco/queue-posts-metal-v2';dest.mkdir(exist_ok=True)
s=(src/'model.py').read_text().replace("'cbf_chrome'","'queue_metal'")
s=s.replace("P.rod(m,(*p,2.65),(*p,35.8),1.1,'queue_metal',32,True)","lathe([(0,2.65),(1.1,2.65),(1.1,35.8),(0,35.8)],'queue_shaft',p)")
s=s.replace("P.card(m,mat,pts,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals)","P.card(m,mat,pts,(dz*math.cos(mid),dz*math.sin(mid),-dr),normals=normals,uv=[(math.atan2(v[1]-c[1],v[0]-c[0])/math.tau,(v[2])/8) for v in pts])")
s=s.replace("m.tile_overrides.update({k:24. for k in m.polygons});return m","m.material_overrides.update({k:'models/props/cerroblanco/queue_posts_metal_v2/'+k+'.vmat' for k in ('queue_metal','queue_shaft')})\n    m.tile_overrides.update({k:24. for k in m.polygons});return m")
(dest/'model.py').write_text(s)
s=(src/'build.py').read_text().replace('queue-posts-v1','queue-posts-metal-v2').replace('queue_posts_v1','queue_posts_metal_v2')
s=s.replace("    (dest/'fine.vmdl').write_text(after)","    after=after.replace('{ from = \\\"soil.vmat\\\"', ''.join('{ from = \\\"'+k+'.vmat\\\" to = \\\"'+PROP+'/'+k+'.vmat\\\" },\\n' for k in ('queue_metal','queue_shaft'))+'{ from = \\\"soil.vmat\\\"')\n    (dest/'fine.vmdl').write_text(after)")
(dest/'build.py').write_text(s);(dest/'verify.py').write_text((src/'verify.py').read_text())
o=R/'output/cerroblanco/queue-posts-metal-v2'
for n in ['import.json','compile.json','show.json','restore.json','capture.py']:(o/n).write_text((R/'output/cerroblanco/queue-posts-v1'/n).read_text().replace('queue-posts-v1','queue-posts-metal-v2'))

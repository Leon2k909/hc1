from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'Sources/CerroBlanco/queue-posts-v1'
s=(R/'Sources/CerroBlanco/cafe-display-v1/build.py').read_text().replace('cafe-display-v1','queue-posts-v1').replace('cafe_display_v1','queue_posts_v1')
a=s.index('    old=K.Model();');b=s.index('    targets=',a)
s=s[:a]+'''    from model import LANES
    old=K.Model()
    for lane in LANES:F.stanchions(old,lane,0.)
    old.tile_overrides.update({k:24. for k in old.polygons});K.write_obj(OUT/'original.obj',old,'old_queue')
'''+s[b:]
s=s.replace('removed==22','removed==len(keys(OUT/\'original.obj\'))')
s=s.replace("K.write_model(dest,PROP,'display',m)","K.write_model(dest,PROP,'queue',m)")
(o/'build.py').write_text(s)

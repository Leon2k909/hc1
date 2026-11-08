from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'Sources/CerroBlanco/cafe-display-v1'
s=(R/'Sources/CerroBlanco/cafe-grinder-v1/build.py').read_text()
start=s.index('def build():');end=s.index('\ndef keys(',start)
s=s[:start]+'from model import build\n'+s[end:]
s=s.replace('cafe-grinder-v1','cafe-display-v1').replace('cafe_grinder_v1','cafe_display_v1')
a=s.index('    old=K.Model();');b=s.index('    targets=',a)
s=s[:a]+'''    old=K.Model();old.box((628,604,42),(682,626,43.5),'cbf_track');old.box((628,604,43.5),(682,626,56),{'default':'cb_glass','-z':None})
    old.tile_overrides.update({'cbf_track':64.,'cb_glass':64.});K.write_obj(OUT/'original.obj',old,'case_old')
'''+s[b:]
s=s.replace('removed==128','removed==22')
a=s.index("    (dest/'beans.vmat')");b=s.index('    for mat,rows',a);s=s[:a]+s[b:]
# Display geometry is already at its actual world placement.
a=s.index('    for mat,rows in m.polygons.items():');b=s.index("    path=OUT/'placed.obj'",a);s=s[:a]+s[b:]
s=s.replace("K.write_model(dest,PROP,'grinder',m)","K.write_model(dest,PROP,'display',m)")
a=s.index('    marker=');b=s.index("    (dest/'fine.vmdl')",a);s=s[:a]+s[b:]
s=s.replace("+'\\nnewmtl grinder_beans\\nKd 1 1 1\\n'",'')
(o/'build.py').write_text(s)
p=R/'output/cerroblanco/cafe-display-v1/capture.py';p.write_text(p.read_text().replace('558,-655,64','515,-655,64').replace("'angles':'10,0,0'","'angles':'8,0,0'"))

from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');o=R/'Sources/CerroBlanco/pan-dulce-v1'
s=(R/'Sources/CerroBlanco/cafe-display-v1/build.py').read_text().replace('cafe-display-v1','pan-dulce-v1').replace('cafe_display_v1','pan_dulce_v1')
a=s.index('    old=K.Model();');b=s.index('    targets=',a)
s=s[:a]+'''    from model import positions
    old=K.Model()
    for x,y in positions():F.lathe(old,'cbf_pastry',(x,y,43.6),[(0,0),(2.4,0),(2.6,1.2),(1.6,2.4),(0,2.7)],sides=10,cap_top=False)
    old.tile_overrides['cbf_pastry']=64.;K.write_obj(OUT/'original.obj',old,'old_food')
'''+s[b:]
s=s.replace('removed==22','removed==540').replace("K.write_model(dest,PROP,'display',m)","K.write_model(dest,PROP,'pastries',m)")
marker="    (dest/'fine.vmdl').write_text(after)"
s=s.replace(marker,"    after=after.replace('{ from = \\\"soil.vmat\\\"', '{ from = \\\"concha_crust.vmat\\\" to = \\\"'+PROP+'/crust.vmat\\\" },\\n{ from = \\\"soil.vmat\\\"')\n"+marker)
s=s.replace("    for mat,rows", "    for mat,rows")
s=s.replace("    path=OUT/'placed.obj'",'''    dest=OUT/'stage'/PROP
    (dest/'crust.vmat').write_text('"Layer0"\\n{\\n shader "shaders/complex.shader"\\n F_SPECULAR "1"\\n g_flMetalness "0"\\n g_flRoughnessScaleFactor "1"\\n TextureColor "materials/default/default_color.tga"\\n TextureNormal "materials/default/default_normal.tga"\\n TextureRoughness "[0.78 0.78 0.78 0]"\\n TextureAmbientOcclusion "materials/default/default_ao.tga"\\n g_vColorTint "[0.84 0.67 0.43 1]"\\n g_flModelTintAmount "1"\\n}\\n')
    path=OUT/'placed.obj' '''.rstrip())
(o/'build.py').write_text(s)
out=R/'output/cerroblanco/pan-dulce-v1'
for n in ['import.json','compile.json','show.json','restore.json']:(out/n).write_text((R/'output/cerroblanco/cafe-display-v1'/n).read_text().replace('cafe-display-v1','pan-dulce-v1'))
(out/'capture.py').write_text((R/'output/cerroblanco/cafe-display-v1/capture.py').read_text().replace('515,-655,64','552,-650,64').replace("'angles':'8,0,0'","'angles':'17,0,0'"))

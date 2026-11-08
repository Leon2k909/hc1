from pathlib import Path
R=Path('C:/sbox-projects/hc1/forked-shooter-main');d=R/'Sources/CerroBlanco/courtyard-cctv-v1';o=R/'output/cerroblanco/courtyard-cctv-v1'
s=(R/'Sources/CerroBlanco/cafe-pendant-v1/build.py').read_text().replace('cafe-pendant-v1','courtyard-cctv-v1').replace('cafe_pendant_v1','courtyard_cctv_v1');a=s.index('    old=K.Model();');b=s.index('    targets=',a)
s=s[:a]+'''    old=K.Model();F.camera(old,(480,-1000,200),(1,-1));old.tile_overrides.update({k:64. for k in old.polygons});K.write_obj(OUT/'original.obj',old,'old_camera')
'''+s[b:];s=s.replace('removed==110','removed==len(keys(OUT/\'original.obj\'))');s=s.replace("    (dest/'fine.vmdl').write_text(after)","    import riverdale_camera as C\n    after=after.replace('{ from = \\\"soil.vmat\\\"', ''.join('{ from = \\\"'+k+'.vmat\\\" to = \\\"materials/riverdale/cctv_v2/'+k+'.vmat\\\" },\\n' for k in C.MATERIALS)+'{ from = \\\"soil.vmat\\\"')\n    (dest/'fine.vmdl').write_text(after)");(d/'build.py').write_text(s)
for n in ['import.json','compile.json','show.json','restore.json']:(o/n).write_text((R/'output/cerroblanco/cafe-pendant-v1'/n).read_text().replace('cafe-pendant-v1','courtyard-cctv-v1'))
(o/'capture.py').write_text((R/'output/cerroblanco/cafe-pendant-v1/capture.py').read_text().replace('574,-606,103','-1050,-530,180').replace("'angles':'-13,-20,0'","'angles':'-14,45,0'"))

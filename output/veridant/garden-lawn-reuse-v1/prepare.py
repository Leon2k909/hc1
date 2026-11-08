from pathlib import Path
import json
root=Path.cwd();out=root/'output/veridant/garden-lawn-reuse-v1';before=out/'before';before.mkdir(exist_ok=True)
paths=['models/maps/veridant/veridant_ground.vmdl','models/maps/veridant/veridant_dress.vmdl','models/maps/veridant/garden-relief-v1/garden_strip_relief.vmdl']
material='materials/veridant/trials/megascans-lawn-trial-20261105/lawn-balanced.vmat'
for i,rel in enumerate(paths):
 p=root/'Assets'/rel;s=p.read_text();assert s.count('materials/veridant/vr_lawn.vmat')==1
 (before/f'{i}.vmdl').write_bytes(p.read_bytes())
 changed=s.replace('materials/veridant/vr_lawn.vmat',material)
 assert changed.replace(material,'materials/veridant/vr_lawn.vmat')==s
 (out/f'{i}.vmdl').write_text(changed)
 (out/f'compile-{i}.json').write_text(json.dumps({'path':rel,'full':False}))
script='''var root=Sandbox.Project.Current.GetRootPath();var o=System.IO.Path.Combine(root,"output/veridant/garden-lawn-reuse-v1");var paths=PATHS;for(var i=0;i<paths.Length;i++){var live=System.IO.Path.Combine(root,"Assets",paths[i]);if(System.IO.File.ReadAllText(live)!=System.IO.File.ReadAllText(System.IO.Path.Combine(o,"before",i+".vmdl")))throw new Exception("Model changed "+paths[i]);}for(var i=0;i<paths.Length;i++){var live=System.IO.Path.Combine(root,"Assets",paths[i]);System.IO.File.Copy(System.IO.Path.Combine(o,i+".vmdl"),live,true);Editor.AssetSystem.RegisterFile(live);}return paths;'''
script=script.replace('PATHS','new[]{'+','.join(json.dumps(p) for p in paths)+'}')
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/garden-lawn/import.cs');ex.write_text(script);(out/'import.json').write_text(json.dumps({'path':str(ex)}))
(out/'before.png').write_bytes(Path('C:/Program Files (x86)/Steam/steamapps/common/sbox/screenshots/sbox.2026.11.06.19.14.20.png').read_bytes())
print('Prepared three exact lawn material remaps; all other model data unchanged')

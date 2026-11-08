from pathlib import Path
import sys,json,shutil
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');sys.path.insert(0,str(ROOT/'Tools'))
import map_kit as K,veridant_map as V,veridant_gallery_rug as B
OUT=ROOT/'output/veridant/gallery-rug-v3';OUT.mkdir(exist_ok=True)
stage=OUT/'stage';d=stage/'materials/veridant/gallery-rug-v3';d.mkdir(parents=True,exist_ok=True)
shutil.copy2(Path('C:/Users/leon2/.codex/generated_images/01a1ac9b-89d5-7aa3-8fe2-8ad23ca89dc1/exec-89c513dc-6a23-42f4-b8d8-669b52af1cfe.png'),d/'rug-albedo.png')
(d/'generated.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor "materials/veridant/gallery-rug-v3/rug-albedo.png"
 TextureNormal "materials/default/default_normal.tga"
 TextureRoughness "[0.98 0.98 0.98 0]"
 g_flMetalness "0"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
}
''')
m=K.Model();m.uv_source_name='veridant_buildings';B.build_into(m);V.configure(m)
res='models/props/shared/gallery_rug_v1';K.write_model(stage/res,res,'rug',m)
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/gallery-rug-generated');ex.mkdir(parents=True,exist_ok=True)
code='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/veridant/gallery-rug-v3/stage");foreach(var f in System.IO.Directory.GetFiles(stage,"*",System.IO.SearchOption.AllDirectories)){var dst=System.IO.Path.Combine(root,"Assets",System.IO.Path.GetRelativePath(stage,f));System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(dst));System.IO.File.Copy(f,dst,true);Editor.AssetSystem.RegisterFile(dst);}return true;'''
p=ex/'import.cs';p.write_text(code);(OUT/'import.json').write_text(json.dumps({'path':str(p)}));(OUT/'compile-material.json').write_text(json.dumps({'path':'materials/veridant/gallery-rug-v3/generated.vmat','full':True}))
shutil.copy2(ROOT/'output/veridant/gallery-rug-v2/after.png',OUT/'before.png')

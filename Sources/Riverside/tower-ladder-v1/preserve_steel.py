"""Keep the original wooden ladder and add a self-contained galvanized-steel variant/export."""
from pathlib import Path
import sys,json,hashlib,shutil
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];OUT=ROOT/'output/riverside/tower-ladder-v1';STAGE=OUT/'reusable-stage'
RES='models/props/riverside/tower_ladder_v1';MAT='materials/riverside/tower_ladder_legacy_steel'
model=STAGE/'Assets'/RES;mat=STAGE/'Assets'/MAT;model.mkdir(parents=True,exist_ok=True);mat.mkdir(parents=True,exist_ok=True)
original=ROOT/'Assets'/RES
for suffix in ('obj','mtl'):
    data=(original/f'legacy_ladder.{suffix}').read_text().replace('legacy_ladder.mtl','legacy_ladder_steel.mtl')
    (model/f'legacy_ladder_steel.{suffix}').write_text(data)
t=(original/'legacy_ladder.vmdl').read_text().replace(RES+'/legacy_ladder.obj',RES+'/legacy_ladder_steel.obj').replace('materials/riverside/rs_wood.vmat',MAT+'/steel.vmat')
(model/'legacy_ladder_steel.vmdl').write_text(t)
for name in ('zinc_color.png','zinc_normal.png','zinc_rough.png'):shutil.copyfile(ROOT/'Assets/materials/riverside/tv_aerial_v1'/name,mat/name)
(mat/'steel.vmat').write_text('''Layer0
{
 shader "shaders/complex.shader"
 F_SPECULAR 1
 TextureColor "materials/riverside/tower_ladder_legacy_steel/zinc_color.png"
 TextureNormal "materials/riverside/tower_ladder_legacy_steel/zinc_normal.png"
 TextureRoughness "materials/riverside/tower_ladder_legacy_steel/zinc_rough.png"
 g_flMetalness "0.78"
 g_flRoughnessScaleFactor "1"
 g_vColorTint "[1 1 1 1]"
}
''')
files=[p for p in STAGE.rglob('*') if p.is_file()]
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'));from native import Editor
with Editor() as e:
    code='''var root=Sandbox.Project.Current.GetRootPath();var stage=System.IO.Path.Combine(root,"output/riverside/tower-ladder-v1/reusable-stage");
var paths=new[]{'''+','.join(json.dumps(p.relative_to(STAGE).as_posix()) for p in files)+'''};
foreach(var relative in paths){if(relative.Contains("..")||!(relative.StartsWith("Assets/models/props/riverside/tower_ladder_v1/legacy_ladder_steel.")||relative.StartsWith("Assets/materials/riverside/tower_ladder_legacy_steel/")))throw new Exception("Unexpected preservation path");var target=System.IO.Path.Combine(root,relative);System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(target));System.IO.File.Copy(System.IO.Path.Combine(stage,relative),target,true);Editor.AssetSystem.RegisterFile(target);}return new{Files=paths.Length};'''
    e.script(code,'preserve-steel-ladder.cs')
    for p in [MAT+'/steel.vmat',RES+'/legacy_ladder_steel.vmdl']:
        r=e.call('asset_compile',dict(path=p));assert r['Success']
    result=e.script('''var output=System.IO.Path.Combine(Sandbox.Project.Current.GetRootPath(),"output/riverside/tower-ladder-v1");var paths=new System.Collections.Generic.List<string>();
foreach(var variant in new[]{"wood","steel"}){var m=Model.Load("models/props/riverside/tower_ladder_v1/"+(variant=="wood"?"legacy_ladder.vmdl":"legacy_ladder_steel.vmdl"));if(m.IsError||m.MeshInfo.Meshes.Sum(x=>x.Triangles)!=450)throw new Exception("Original geometry changed");var w=new SceneWorld();try{new SceneObject(w,m,Transform.Zero);new SceneLight(w,new Vector3(-90,-100,470),900,Color.White*12);var eye=new Vector3(-95,-115,485);var camera=new SceneCamera("Original ladder finish") {World=w,Position=eye,Rotation=Rotation.LookAt(new Vector3(12,0,480)-eye),FieldOfView=48,ZNear=.1f,ZFar=2000,Size=new Vector2(900,700),AmbientLightColor=Color.White*.25f,BackgroundColor=new Color(.055f,.065f,.075f)};var pix=new Editor.Pixmap(900,700);Sandbox.SandboxToolExtensions.RenderToPixmap(camera,pix,false);var path=System.IO.Path.Combine(output,"preserved-"+variant+".png");pix.SavePng(path);paths.Add(path);}finally{w.Delete();}}
return new{OriginalWoodPreserved=true,SteelVariant=true,Triangles=450,Images=paths};''','verify-preserved-ladder.cs')
export=OUT/'reusable-steel-ladder'
shutil.copytree(STAGE,export,dirs_exist_ok=True)
(export/'README.txt').write_text('Original Riverside ladder geometry, galvanized-steel finish. Copy Assets into another s&box project. Model: '+RES+'/legacy_ladder_steel.vmdl\n450 triangles. No collision or climbing logic. The original wood version remains in the source project. Geometry is identical to the old ladder; finish is independent of shared wood materials.\n')
result['ExportFolder']=str(export);(OUT/'preserved-original.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

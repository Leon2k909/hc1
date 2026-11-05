"""Compare frozen flames with/without heat refraction at matching camera angles in an isolated editor scene."""
import json
from pathlib import Path
import sys
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3]
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
WORK=ROOT/'output/riverside/drum-fire-clipping'
WORK.mkdir(parents=True,exist_ok=True)
code=(ROOT/'Sources/Zombies/cooler-v2/capture_engine.cs.txt').read_text()
code=code.replace('output/asset-improvement-20261030/cooler/engine','output/riverside/drum-fire-clipping')
code=code.replace('var oldCooler = Model.Load("models/compare_old/old_cooler.vmdl");','var oldCooler = cooler;')
a=code.index('var views = ')
b=code.index('\nvar scene = ',a)
code=code[:a]+'''var views = new (string Name,Vector3 Eye,Vector3 Target,float Fov,bool Cooler)[]
{
    ("front",drum+new Vector3(62,-42,48),drum+Vector3.Up*36,55f,false),
    ("back",drum+new Vector3(-62,42,48),drum+Vector3.Up*36,55f,false),
    ("low",drum+new Vector3(65,2,35),drum+Vector3.Up*40,55f,false),
    ("above",drum+new Vector3(38,-34,64),drum+Vector3.Up*36,60f,false),
    ("side",drum+new Vector3(-62,-30,44),drum+Vector3.Up*36,55f,false)
};
'''+code[b:]
code=code.replace('new[] { "before", "after" }','new[] { "heat-on", "heat-off" }')
code=code.replace('newObject.Enabled = variant == "after";\n            oldObject.Enabled = variant == "before";', '''newObject.Enabled=true; oldObject.Enabled=false;
            foreach(var heat in scene.GetAllComponents<ParticleSpriteRenderer>().Where(c=>c.GameObject.Name=="Hot Air"))
                heat.Enabled=variant=="heat-on";
            foreach(var effect in scene.GetAllComponents<ParticleEffect>()) effect.Paused=true;''')
code=code.replace('for (var frame = 0; frame < 24; frame++)','for (var frame = 0; frame < 8; frame++)')
code=code.replace('                    scene.EditorTick(.016f, .016f);','')
code=code.replace('using var bitmap = new Bitmap(1536, 1024);','using var bitmap = new Bitmap(1024,768);')
with Editor() as e:
    result=e.script(code,'fire-clipping-ab.cs')
    (WORK/'capture.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

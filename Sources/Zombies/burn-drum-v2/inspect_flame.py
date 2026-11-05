import json
from pathlib import Path
import sys
sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Sources/Spillway/hose-coil-v2'))
from native import Editor
with Editor() as e:
    result=e.script('''var texture = Texture.Load(Facepunch.FireParticles.Flame);
var sprite=Facepunch.FireParticles.SpriteOf(Facepunch.FireParticles.Flame);
return new { texture.Width,texture.Height,
State=Editor.SceneEditorSession.Active.Scene.GetAllComponents<ParticleSpriteRenderer>().Where(c=>c.GameObject.Name=="Hot Air")
    .Select(c=>new { c.GameObject.Name, Renderer=c.Refraction,
    Normal=c.NormalTexture != null, Count=c.GetComponent<ParticleEffect>().ParticleCount }).ToArray(),
SequenceFrameCounts=Enumerable.Range(0,8).Select(i=>texture.GetSequenceFrameCount(i)).ToArray(),
Properties=typeof(Particle).GetFields().Select(x=>new { x.Name,Type=x.FieldType.Name }).ToArray(),
Sprite=sprite.Animations.Select(a=>new {a.Name,a.FrameRate,a.Origin,a.LoopMode,Frames=a.Frames.Count()}).ToArray() };''', 'inspect-flame-sheet.cs')
    (ROOT/'output/riverside/drum-fire-rooted/texture-metadata.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

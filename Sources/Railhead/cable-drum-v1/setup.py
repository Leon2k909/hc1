"""Derive the isolated native capture from the tested Railhead review harness."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;old=ROOT/'Sources/Railhead/road-barrier-v1'
(HERE/'native.py').write_text((old/'native.py').read_text().replace('road-barrier-v1','cable-drum-v1').replace('railhead-road-barrier','railhead-cable-drum'))
src=(old/'runtime_review.cs.txt').read_text().replace('road-barrier-v1','cable-drum-v1').replace('east_without_barrier','east_without_drum').replace('road_barrier.vmdl','cable_drum.vmdl').replace('road barrier review','cable drum review').replace('Candidate barrier','Candidate reel')
src=src.replace('for(int i=0;i<100;i++){cancellationToken.ThrowIfCancellationRequested();await Task.Delay(25,cancellationToken);}', '''for(int i=0;i<400;i++) {
  cancellationToken.ThrowIfCancellationRequested();
  if(!Game.IsPlaying||Game.ActiveScene!=runtimeScene)throw new InvalidOperationException("Play session changed while waiting for the player");
  if(runtimeScene.GetAllComponents<Facepunch.PlayerPawn>().Any())break;
  await Task.Delay(50,cancellationToken);
 }''')
start=src.index(' var views=new[]');end=src.index(' foreach(var variant in',start)
src=src[:start]+''' var views=new[]{new {Name="drum",Eye=new Vector3(-1570,-2020,72),Target=new Vector3(-1632,-1878,25),Fov=39f}};
'''+src[end:]
(HERE/'runtime_review.cs.txt').write_text(src)
(HERE/'capture.py').write_text((old/'capture.py').read_text().replace("if not started:raise", "if status['SceneHasUnsavedChanges']:raise RuntimeError('Preserve the unsaved editor scene')\nif not started:raise"))
count=json.loads((ROOT/'output/railhead/cable-drum-v1/manifest.json').read_text())['original_triangles']
verify=(old/'verify.py').read_text().replace('road-barrier-v1','cable-drum-v1').replace('east_without_barrier','east_without_drum').replace('== 120',f'== {count}').replace('replaced_triangles=120',f'replaced_triangles={count}').replace("('barrier',)","('drum',)").replace('RAILHEAD / ROADWORKS BARRIER','RAILHEAD / CABLE REEL')
# The public east mesh already includes the approved barrier and extinguisher.
verify=verify.replace("'models/maps/railhead/extinguisher-v2/east-base.obj'","'models/maps/railhead/road-barrier-v1/east_without_barrier.obj'")
verify=verify.replace("assert status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0", "assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0")
verify=verify.replace("assert restored['after']['LastCompileSucceeded'] and restored['after']['LastCompileErrors'] == 0", "assert restored['after']['LastCompileErrors'] == 0\n# Play-stop may trigger a build; the current settled compiler state above is authoritative.\nif not restored['after']['IsCompiling']: assert restored['after']['LastCompileSucceeded']")
verify=verify.replace("Image.open(folder/f'{name}-{v}.png').convert('RGB')", "Image.open(folder/f'{name}-{v}.png').convert('RGB').crop((300,40,1210,895))")
verify=verify.replace('font_path, 38','font_path, 32').replace('font_path, 24','font_path, 20')
verify=verify.replace("sheet.save(OUT/f'{name}-comparison.png')", "sheet.save(OUT/f'{name}-comparison.png')\n    sheet.save(OUT/f'{name}-original-wood-comparison.png')")
verify=verify.replace('report = dict(review_only=True,', 'report = dict(review_only=True, original_wood_material_restored=True, new_shape_unchanged=True,')
verify=verify.replace("folder = OUT/'runtime-review'", '''# The texture revision must keep the first proposal's exact shape and normals.
first = (OUT/'first-review/cable_drum.obj').read_text().splitlines()
revised = (ROOT/'Assets/models/maps/railhead/cable-drum-v1/cable_drum.obj').read_text().splitlines()
assert [l for l in first if not l.startswith('vt ')] == [l for l in revised if not l.startswith('vt ')]
for timber in ('timber_a','timber_b','timber_c'):
    assert (ROOT/f'Assets/materials/railhead/cable-drum-v1/{timber}.vmat').read_text() == (ROOT/'Assets/materials/railhead/rw_wood.vmat').read_text()
folder = OUT/'runtime-review' ''')
(HERE/'verify.py').write_text(verify)

"""Native capture of the actual saved hitch; no map substitution."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OUT=ROOT/'output/riverside/tower-ladder-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
code=(HERE/'context.cs.txt').read_text()
code=code.replace('output/riverside/tower-ladder-v1/context','output/riverside/tower-ladder-v1/installed')
code=code.replace('"Trailer Hitches"','"Trailer Hitches", "Water Tower Tanks", "Guard Tower Ladders"')
code=code.replace('models/props/riverside/tower_ladder_v1/legacy_ladder.vmdl','models/props/riverside/tower_ladder_v1/ladder.vmdl')
a=code.index('var low=scene.GetAllComponents<ModelRenderer>()');b=code.index('        oldObject = ',a)
code=code[:a]+'newObject=scene.GetAllObjects(false).Single(g=>g.Name=="Guard Tower Ladder");\n'+code[b:]
code=code.replace('new[] { "before", "after" }','new[] { "after" }')
with Editor() as e:
    result=e.script(code,'check-installed-hitch.cs')
    (OUT/'installed-capture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
    assert result['SourceUnchanged'] and not result['ErrorModels']

"""Native capture of the actual saved roof; no map substitution."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OUT=ROOT/'output/riverside/tower-roof-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
code=(HERE/'context.cs.txt').read_text()
code=code.replace('output/riverside/tower-roof-v1/context','output/riverside/tower-roof-v1/installed')
code=code.replace('"Trailer Roofes"','"Trailer Roofes", "Guard Tower Roofs"')
code=code.replace('models/props/riverside/tower_roof_v1/legacy_roof.vmdl','models/props/riverside/tower_roof_v1/roof.vmdl')
a=code.index('var low=scene.GetAllComponents<ModelRenderer>()');b=code.index('        oldObject = ',a)
code=code[:a]+'newObject=scene.GetAllObjects(false).Single(g=>g.Name=="Guard Tower Roof");\n'+code[b:]
code=code.replace('new[] { "before", "after" }','new[] { "after" }')
with Editor() as e:
    result=e.script(code,'check-installed-roof.cs')
    assert result['SourceUnchanged'] and not result['ErrorModels']
    (OUT/'installed-capture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

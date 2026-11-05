"""Native capture of the actual saved hitch; no map substitution."""
from pathlib import Path
import sys,json
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OUT=ROOT/'output/riverside/trailer-hitch-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'))
from native import Editor
code=(HERE/'context.cs.txt').read_text()
code=code.replace('output/riverside/trailer-hitch-v1/context','output/riverside/trailer-hitch-v1/installed')
code=code.replace('"Roof TV Aerials"','"Roof TV Aerials", "Trailer Hitches"')
code=code.replace('models/props/riverside/trailer_hitch_v1/legacy_hitch.vmdl','models/props/riverside/trailer_hitch_v1/hitch.vmdl')
a=code.index('var low=scene.GetAllComponents<ModelRenderer>()');b=code.index('        oldObject = ',a)
code=code[:a]+'newObject=scene.GetAllObjects(false).Single(g=>g.Name=="T2 Trailer Hitch");\n'+code[b:]
code=code.replace('new[] { "before", "after" }','new[] { "after" }')
with Editor() as e:
    result=e.script(code,'check-installed-hitch.cs')
    assert result['SourceUnchanged'] and not result['ErrorModels']
    (OUT/'installed-capture.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))

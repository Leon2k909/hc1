"""Native resource import and matched player-height preview; saved map stays untouched."""
from pathlib import Path
import json,sys,hashlib
sys.dont_write_bytecode=True
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent;OUT=ROOT/'output/riverdale/hydrant-v1'
sys.path.insert(0,str(ROOT/'Sources/Spillway/hose-coil-v2'));from native import Editor
mode=sys.argv[1]
with Editor() as e:
 status=e.call('editor_status');assert Path(status['Paths']['ProjectRoot']).resolve()==ROOT.resolve();assert not status['IsCompiling'] and status['LastCompileSucceeded']
 if mode=='import':
  m=json.loads((OUT/'manifest.json').read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();scene='Assets/scenes/maps/Riverdale/riverdale.scene'
  assert all(sha(ROOT/p)==h for p,h in m['protected'].items() if p!=scene)
  m['protected'][scene]=sha(ROOT/scene);(OUT/'manifest.json').write_text(json.dumps(m,indent=2))
  r=e.script((HERE/'import.cs.txt').read_text(),'import-interior-fridges.cs');(OUT/'native-import.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
  paths=[p[7:] for p in m['files'] if p.endswith('.vmat')]+[m['resource'],m['background'],'models/props/riverdale/hydrant_v1/previous.vmdl','models/props/riverdale/hydrant_v1/legacy_hydrant.vmdl']
  results=[dict(path=p,result=e.call('asset_compile',dict(path=p))) for p in paths];(OUT/'native-compile.json').write_text(json.dumps(results,indent=2));assert all(i['result']['Success'] for i in results);print(json.dumps(dict(Compiled=len(results),Success=True)),flush=True)
 elif mode=='context':
  captures=[]
  for variant in ('before','after'):
   code=(HERE/'context.cs.txt').read_text().replace('new[] { "before", "after" }','new[] { "'+variant+'" }')
   if variant=='before':code=code.replace('newObject.Components.Create<ModelRenderer>().Model=cooler','newObject.Components.Create<ModelRenderer>().Model=oldCooler')
   r=e.script(code,'capture-interior-fridges-'+variant+'.cs');captures.append(r)
   (OUT/(variant+'-capture.json')).write_text(json.dumps(r,indent=2))
   print(json.dumps(r,indent=2),flush=True)
  result=dict(SourceUnchanged=all(r['SourceUnchanged'] for r in captures),ErrorModels=[x for r in captures for x in r['ErrorModels']],Captures=captures)
  (OUT/'context-capture.json').write_text(json.dumps(result,indent=2));assert result['SourceUnchanged'] and not result['ErrorModels']

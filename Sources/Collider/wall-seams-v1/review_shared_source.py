"""Review concurrent ceiling/trench hooks without modifying their shared source."""
from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'output/collider-wall-overlap-20261027'
path = ROOT/'Tools/collider_map.py'
text = path.read_text(encoding='utf-8')
original = subprocess.check_output(['rtk','proxy','git','show','HEAD:Tools/collider_map.py'],cwd=ROOT,text=True,encoding='utf-8')
manifest = json.loads((OUT/'stage/manifest.json').read_text())
expected = manifest['sources']['Tools/collider_map.py']
tree = ast.parse(text)
assert any(isinstance(n,ast.Import) and any(a.name=='collider_wall_seams' and a.asname=='W' for a in n.names) for n in tree.body)
build = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='build')
calls = [ast.unparse(n.value) for n in build.body if isinstance(n,ast.Expr) and isinstance(n.value,ast.Call)]
assert calls.count('W.refine_machine(accel)') == 1
assert calls.index('W.refine_machine(accel)') > calls.index('machine(accel)')
machine = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='machine')
original_machine = next(n for n in ast.parse(original).body if isinstance(n,ast.FunctionDef) and n.name=='machine')
assert ast.dump(machine,include_attributes=False) == ast.dump(original_machine,include_attributes=False)
without_ceiling = text.replace('import collider_ceiling as CE\n','').replace(
    '        if paint.startswith("ch_"):\n'
    '            m.material_overrides[paint] = f"{CE.MATERIAL_DIR}/{paint}.vmat"\n'
    '            m.tile_overrides[paint] = CE.TILES[paint]\n'
    '        elif paint.startswith("cc_"):', '        if paint.startswith("cc_"):').replace(
    '    CE.refine_structure(structure)\n','')
old_start = original.index('    # Floor trench strips,')
old_end = original.index('    for e in (-1012,1012):',old_start)
trench = ('    # Continuous fitted trench covers and yellow route markings on the upper gallery.\n'
    '    import collider_gallery_trench\n'
    '    collider_gallery_trench.append(m)\n')
variants = {'ceiling':without_ceiling,'ceiling-and-gallery-trench':without_ceiling.replace(trench,original[old_start:old_end])}
server = ('    for e,n in ((-430,80),SR.POSITION):\n'
    '        if e > 0:\n'
    '            SR.build(m,e,n)\n'
    '        else:\n'
    '            box(m,e-24,e+24,n-30,n+30,0,138,None)\n'
    '            H.server_face(m,e,n)\n')
old_server = ('    for e,n in ((-430,80),(430,80)):\n'
    '        box(m,e-24,e+24,n-30,n+30,0,138,None)\n'
    '        H.server_face(m,e,n)\n')
variants['ceiling-gallery-trench-server-rack'] = variants['ceiling-and-gallery-trench'].replace(
    'import collider_server_rack as SR\n','').replace(server,old_server)
matches = [name for name,value in variants.items() if any(hashlib.sha256(v.encode()).hexdigest()==expected
    for v in (value,value.replace('\n','\r\n')))]
assert matches, 'Shared map changed outside the reviewed ceiling/trench additions'
result = {'file':'Tools/collider_map.py','before':expected,
    'after':hashlib.sha256(path.read_bytes()).hexdigest(),'reviewedConcurrentChanges':matches,
    'wallSeamImportAndBuildHookPreserved':True,'machineFunctionUnchanged':True,'modifiedSharedFile':False}
(OUT/'source-review.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))

from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
def atomic(path,text):
    assert path.resolve().is_relative_to(ROOT)
    incoming=path.with_name(path.name+'.cabinet-incoming');incoming.write_text(text,encoding='utf-8')
    incoming.replace(path)
    assert path.read_text(encoding='utf-8')==text
p=ROOT/'docs/notes/070-collider-accelerator-laboratory-tools-collider-map.md'
old=p.read_text();marker=old.splitlines()[0]+'\n'
entry='''- Maintenance cabinet installed (2026-10-31): the approved right-hand cabinet replaces the case at
  plan (-650,160,0). Exactly 2,420 old render triangles and one full-height box are removed; 23,646 approved
  triangles, 39 boxes and ten hulls are installed. Detail now totals 304,419 triangles. Four tyre hulls were
  simplified to 32 sampled original points after native testing exposed two oversized runtime hulls.
  The visible mesh and materials are unchanged. All 25 installed-model native collision checks pass,
  including tyre contact rays filtered to the detail model so the structure floor cannot create a false pass.
  The model is compiled and up to date. Unrelated render triangles, physics blocks, accepted props and
  the saved scene are preserved. Tools/collider_tool_cabinet.py, accepted-physics.json and the exact selected
  hardcase branch preserve regeneration. Sources/Collider/tool-cabinet-trial-v1/installed.json and
  output/collider-tool-cabinet-accepted-20261031/ retain rollback, hashes, checks and a native offscreen view
  of the installed location. The active play session was not stopped or edited.
'''
if 'Maintenance cabinet installed (2026-10-31)' not in old:atomic(p,old.replace(marker,marker+entry,1))
p=ROOT/'Sources/Collider/tool-cabinet-trial-v1/README.md';old=p.read_text()
intro='''# Collider approved maintenance cabinet

Installed on 2026-10-31 following explicit user approval of the right-hand native comparison. The selected
case at plan (-650,160,0) is replaced, including its old full-height box. Approved visible geometry and
materials are unchanged. The installed 39 boxes and ten hulls keep the underside and handle gaps open.
Four tyre collision hulls now use 32 sampled original points each; all 25 native installed-model checks
pass, including tyre contact rays that exclude the structure floor. The combined model is compiled and
up to date. Unrelated map geometry/physics and the saved scene are unchanged.

Current evidence: installed.json and output/collider-tool-cabinet-accepted-20261031/.
Regeneration: Tools/collider_tool_cabinet.py, accepted-physics.json and the exact selected hardcase branch.
Use finalize_install.py for current source verification; preview verifiers below guard historical inputs.
Rollback is outside Assets in the acceptance output. The active play session was not stopped or edited.

'''
if not old.startswith('# Collider approved maintenance cabinet'):
    body=old.split('\n',1)[1].lstrip('\n').replace('The proposal is not installed; saved map geometry, physics and scene remain unchanged.','This describes the historical preview; the installation is recorded above.')
    atomic(p,intro+body)
print('Installation notes updated and read back successfully')

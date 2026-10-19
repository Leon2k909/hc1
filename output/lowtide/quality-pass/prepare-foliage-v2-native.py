from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = ROOT / 'output/lowtide/quality-pass'
EXCHANGE = Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/c73825d7161f4693a4393151653dea16')

def save(name, text):
    target = OUTPUT / name
    target.write_text(text, encoding='utf-8')
    shutil.copy2(target, EXCHANGE / name)

text = (OUTPUT / 'import-foliage-candidate.cs').read_text()
text = text.replace('candidate-manifest.json', 'v2-manifest.json').replace('candidate-stage', 'v2-stage')
text = text.replace('materials/lowtide/foliage/', 'materials/lowtide/foliage-v2/')
text = text.replace('shaders/hc1_lowtide_foliage', 'shaders/hc1_lowtide_foliage_v2')
text = text.replace('lt_oak_branch.vmat', 'lt_oak_branch_v2.vmat')
text = text.replace('candidate-compile.json', 'v2-compile.json')
save('import-foliage-v2.cs', text)

text = (OUTPUT / 'preview-foliage-material.cs').read_text()
text = text.replace('Editor.SceneEditorSession.All.SingleOrDefault(s=>s.Scene.Source?.ResourcePath=="scenes/maps/belltower/belltower.scene")??Editor.SceneEditorSession.Active', 'Editor.SceneEditorSession.Active')
text = text.replace('materials/lowtide/foliage/lt_oak_branch.vmat', 'materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat')
text = text.replace('-material-candidate', '-v2-candidate').replace('-material-before', '-v2-before')
text = text.replace('material-preview.json', 'v2-preview.json')
save('preview-foliage-v2.cs', text)
print('Native import and guarded normal-viewport comparison scripts prepared.')

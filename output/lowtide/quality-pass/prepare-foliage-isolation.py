from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[3]
source = root / 'output/lowtide/quality-pass/preview-foliage-material.cs'
text = source.read_text(encoding='utf-8')
text = text.replace('Editor.SceneEditorSession.All.SingleOrDefault(s=>s.Scene.Source?.ResourcePath=="scenes/maps/belltower/belltower.scene")??Editor.SceneEditorSession.Active', 'Editor.SceneEditorSession.Active')
text = text.replace('var candidate=Material.Load("materials/lowtide/foliage/lt_oak_branch.vmat");', '''var compiled=Material.Load("materials/lowtide/foliage/lt_oak_branch.vmat");
var candidate=original.CreateCopy();
candidate.Set("g_tColor",compiled.GetTexture("g_tColor"));''')
text = text.replace('-material-candidate', '-albedo-only').replace('-material-before', '-isolation-before')
text = text.replace('material-preview.json', 'isolation-preview.json')
destination = root / 'output/lowtide/quality-pass/preview-foliage-isolation.cs'
destination.write_text(text, encoding='utf-8')
exchange = Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/c73825d7161f4693a4393151653dea16')
shutil.copy2(destination, exchange / destination.name)
print(destination)

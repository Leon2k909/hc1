from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[3]
folder = root / 'output/lowtide/quality-pass'
exchange = Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/c73825d7161f4693a4393151653dea16')
text = (folder / 'preview-foliage-v2.cs').read_text()
old = 'var candidate=Material.Load("materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat");'
assert text.count(old) == 1
text = text.replace(old, '''var candidate=Material.Load("materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat").CreateCopy();
candidate.Set("g_flTintColor",new Vector3(.48f,.66f,.54f));''')
text = text.replace('-v2-candidate', '-v2-tint').replace('-v2-before', '-v2-tint-before')
text = text.replace('v2-preview.json', 'v2-tint-preview.json')
target = folder / 'preview-foliage-v2-tint.cs'
target.write_text(text)
shutil.copy2(target, exchange / target.name)

inspect = (folder / 'inspect-foliage-candidate.cs').read_text()
inspect = inspect.replace('materials/lowtide/foliage/lt_oak_branch.vmat', 'materials/lowtide/foliage-v2/lt_oak_branch_v2.vmat')
inspect = inspect.replace('"g_tColor","g_tNormal"', '"g_tColor","g_tCoverage","g_tNormal"')
inspect = inspect.replace('compiled-candidate-atlas.png', 'compiled-v2-atlas.png').replace('candidate-bindings.json', 'v2-bindings.json')
target = folder / 'inspect-foliage-v2.cs'
target.write_text(inspect)
shutil.copy2(target, exchange / target.name)

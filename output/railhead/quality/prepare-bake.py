from pathlib import Path

root = Path(__file__).resolve().parents[3]
exchange = Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/72171ce964804002b26c34a6d0c99adf')
source = (root / 'Sources/Belltower/editor/bake-editor-lighting.cs.txt').read_text(encoding='utf-8')
source = source.replace('belltower', 'railhead').replace('Belltower', 'Railhead')
source = source.replace('"30,21,8"', '"30,21,8"')
source = source.replace('"28,39,5" || reflections.Length != 3', '"30,21,8" || reflections.Length != 11')
source = source.replace('p.BakedTexture.ResourcePath', 'p.BakedTexture?.ResourcePath')
(exchange / 'railhead-bake.cs').write_text(source, encoding='utf-8')
print(exchange / 'railhead-bake.cs')

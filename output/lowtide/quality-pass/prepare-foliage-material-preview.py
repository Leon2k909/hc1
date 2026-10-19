from pathlib import Path
folder = Path(__file__).resolve().parent
text = (folder / 'preview-foliage-atlas.cs').read_text()
start = text.index('var candidate=')
end = text.index('var slots=', start)
text = text[:start] + '''var candidate=Material.Load("materials/lowtide/foliage/lt_oak_branch.vmat");
if(candidate.IsError||candidate.GetTexture("g_tColor")?.Width!=1254)throw new Exception("Private candidate is not ready");
''' + text[end:]
text = text.replace('"-atlas-candidate":"-atlas-before"','"-material-candidate":"-material-before"')
text = text.replace('new{atlasWidth=atlas.Width,atlasHeight=atlas.Height,captures,','new{candidate=candidate.ResourcePath,captures,')
text = text.replace('"atlas-preview.json"','"material-preview.json"')
(folder / 'preview-foliage-material.cs').write_text(text)

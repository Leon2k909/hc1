from pathlib import Path
folder = Path(__file__).resolve().parent
text = (folder / 'preview-foliage-response.cs').read_text()
start = text.index('var parameters=')
end = text.index('var slots=', start)
text = text[:start] + '''using var sourceBitmap=Bitmap.CreateFromBytes(System.IO.File.ReadAllBytes(System.IO.Path.Combine(root,"Sources/Lowtide/foliage/oak-branch-candidate.png")));
var atlas=sourceBitmap.ToTexture(true);
candidate.Set("g_tColor",atlas);
''' + text[end:]
text = text.replace('lowtide-foliage-response-preview','lowtide-foliage-atlas-preview')
text = text.replace('"-response-candidate":"-response-before"','"-atlas-candidate":"-atlas-before"')
text = text.replace('new{parameters,captures,','new{atlasWidth=atlas.Width,atlasHeight=atlas.Height,captures,')
text = text.replace('"response-preview.json"','"atlas-preview.json"')
assert 'candidate.Set(parameter' not in text
(folder / 'preview-foliage-atlas.cs').write_text(text)

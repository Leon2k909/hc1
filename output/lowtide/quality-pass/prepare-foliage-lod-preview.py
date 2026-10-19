from pathlib import Path
folder = Path(__file__).resolve().parent
text = (folder / 'preview-foliage-response.cs').read_text()
start = text.index('var original=')
end = text.index('var captures=', start)
text = text[:start] + '''var slots=session.Scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.Contains("trees/oak/")==true).Select(r=>(renderer:r,previous:r.LodOverride)).ToArray();
if(slots.Length!=4)throw new Exception("Expected four trees");
''' + text[end:]
text = text.replace('foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,useCandidate?candidate:slot.previous);slot.renderer.Materials.Apply();}',
                    'foreach(var slot in slots)slot.renderer.LodOverride=useCandidate?0:slot.previous;')
text = text.replace('foreach(var slot in slots){slot.renderer.Materials.SetOverride(slot.slot,slot.previous);slot.renderer.Materials.Apply();}',
                    'foreach(var slot in slots)slot.renderer.LodOverride=slot.previous;')
text = text.replace('"-response-candidate":"-response-before"', '"-lod0":"-automatic-lod"')
text = text.replace('new{parameters,captures,slots=slots.Count,overridesRestored=slots.All(s=>s.renderer.Materials.GetOverride(s.slot)==s.previous)',
                    'new{captures,slots=slots.Length,overridesRestored=slots.All(s=>s.renderer.LodOverride==s.previous)')
text = text.replace('"response-preview.json"','"lod-preview.json"')
assert 'candidate.Set' not in text and 'Materials.SetOverride' not in text
(folder / 'preview-foliage-lod.cs').write_text(text)

from pathlib import Path
p=Path('Sources/Belltower/editor/capture-viewport.cs.txt')
data=p.read_text()
anchor='var forestTrial = config["forest_trial"]?.GetValue<bool>()==true;'
replacement=anchor+'''
var forestBrightness = config["forest_brightness"]?.GetValue<float>();
if(forestBrightness is float brightness && (!forestTrial || brightness<.05f || brightness>1.5f))
    throw new InvalidOperationException("Forest brightness requires a trial and a value from .05 to 1.5.");'''
assert data.count(anchor)==1 and 'var forestBrightness' not in data
data=data.replace(anchor,replacement)
anchor='            trialForest.Flags |= GameObjectFlags.EditorOnly;'
replacement=anchor+'''
            if(forestBrightness is float canopyBrightness)
            {
                var material=Material.Load("materials/belltower/forest/forest_trees.vmat").CreateCopy("forest-canopy-trial-"+Guid.NewGuid());
                material.Set("g_flCanopyBrightness",canopyBrightness);
                foreach(var renderer in scene.GetAllComponents<ModelRenderer>().Where(r=>r.Model?.ResourcePath?.StartsWith("models/maps/belltower/forest/",StringComparison.OrdinalIgnoreCase)==true))
                    renderer.Materials.SetOverride(0,material);
            }'''
assert data.count(anchor)==1
data=data.replace(anchor,replacement)
anchor='        SourceScene=scene.Source?.ResourcePath, SceneHasUnsavedChanges=session.HasUnsavedChanges,'
assert data.count(anchor)==1
data=data.replace(anchor,'        TrialForestBrightness=forestBrightness,\n'+anchor)
temporary=p.with_name(p.name+'.rewrite')
temporary.write_text(data)
temporary.replace(p)
print('Forest-only material trial added; preview cleanup still removes the whole temporary group.')

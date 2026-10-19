from pathlib import Path
folder=Path(__file__).resolve().parent
text=(folder/'production.cs').read_text().replace('structure-timber-v2/production','structure-timber-v2/production-reloaded')
needle='if(session.HasUnsavedChanges)throw new Exception("Unsaved Lowtide");'
assert text.count(needle)==1
text=text.replace(needle,needle+'\nusing(session.Scene.Push())session.Scene.Load(ResourceLibrary.Get<SceneFile>("scenes/maps/lowtide/lowtide.scene"));\nawait Task.Delay(1500,cancellationToken);')
text=text.replace('var report=new{bindings,', 'var report=new{Volumes=session.Scene.GetAllComponents<IndirectLightVolume>().Select(v=>new{v.GameObject.Name,v.Active,v.Enabled,v.ProbeCounts,Path=v.IrradianceTexture?.ResourcePath,Error=v.IrradianceTexture?.IsError}).ToArray(),bindings,')
(folder/'production-reloaded.cs').write_text(text,encoding='utf-8')
Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/9b705a7fa05c489fbc772f40a41b8e93/structure-v2-reloaded.cs').write_text(text,encoding='utf-8')

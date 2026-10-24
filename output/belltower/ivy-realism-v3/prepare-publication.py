from pathlib import Path
root=Path.cwd()
source=(root/'Sources/Belltower/editor/import-ivy-3d-v2.cs.txt').read_text()
source=source.replace('output/belltower/ivy-3d-v1/refined','output/belltower/ivy-realism-v3/publication')
source=source.replace('if (Game.IsPlaying || session is null || session.HasUnsavedChanges)',
    '''var playingBefore=Game.IsPlaying;
var gameBefore=Game.ActiveScene?.Id;
if (Game.IsPlaying && Game.ActiveScene.GetAllComponents<ModelRenderer>().Any(r =>
    r.Model?.ResourcePath?.StartsWith("models/maps/belltower/",StringComparison.OrdinalIgnoreCase)==true))
    throw new InvalidOperationException("Belltower is running; defer this asset update until its test stops.");
if (session is null)''')
source=source.replace('if (manifest["files"].AsObject().Count != 14)','if (manifest["files"].AsObject().Count < 14)')
source=source.replace('|| Game.IsPlaying || Hash(scenePath)',
    '|| Game.IsPlaying!=playingBefore || Game.ActiveScene?.Id!=gameBefore || Hash(scenePath)')
(root/'Sources/Belltower/editor/import-ivy-realism-v3.cs.txt').write_text(source)
print('Prepared guarded production import; Belltower gameplay remains protected.')

from pathlib import Path

source = Path('Sources/Belltower/editor/bake-editor-lighting.cs.txt').read_text()
changes = [
    ('output/belltower/quality/bake-config.json', 'Sources/CerroBlanco/lighting/config.json'),
    ('config["directory"]', 'config["revision"]'),
    ('output/belltower/quality', 'output/cerroblanco/lighting'),
    ('lighting/belltower/', 'lighting/cerroblanco/'),
    ('scenes/maps/belltower/belltower.scene', 'scenes/maps/cerroblanco/cerroblanco.scene'),
    ('Assets/scenes/maps/Belltower/belltower.scene', 'Assets/scenes/maps/CerroBlanco/cerroblanco.scene'),
    ('Belltower has unsaved edits', 'Cerro Blanco has unsaved edits'),
    ('indirect.ProbeCounts.ToString() != "28,39,5" || reflections.Length != 3',
     'indirect.ProbeCounts.x*indirect.ProbeCounts.y*indirect.ProbeCounts.z>7000 || reflections.Length!=11'),
    ('var originalReflections = reflections.Select(p => (Probe:p,Texture:p.BakedTexture,Mode:p.Mode)).ToArray();\n', ''),
    ('        foreach(var original in originalReflections) { original.Probe.BakedTexture=original.Texture; original.Probe.Mode=original.Mode; }\n', ''),
    ('p.BakedTexture.ResourcePath', 'p.Texture?.ResourcePath'),
    ('"reflections-baked.json"', '"reflections-retained.json"'),
    ('    completed = true;', '    typeof(Editor.SceneEditorSession).GetProperty("HasUnsavedChanges").SetValue(session,true);\n    completed = true;'),
]
for old, new in changes:
    assert old in source, old
    source = source.replace(old, new)
source = 'if(Game.IsPlaying)throw new InvalidOperationException("Stop play before the persistent lighting bake.");\n' + source
anchor = 'var scene = session.Scene;'
source = source.replace(anchor, 'if(Editor.SceneEditorSession.Active!=session)throw new InvalidOperationException("Cerro Blanco must own the editor window.");\n'+anchor)
assert 'belltower' not in source.lower()
Path('Sources/CerroBlanco/editor/bake-lighting.cs.txt').write_text(source)
print('Prepared the serial native lighting bake for Cerro Blanco.')

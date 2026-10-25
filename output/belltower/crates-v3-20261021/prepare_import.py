"""Freeze source guards and prepare a native editor publication of 16 crate files."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).parent
path = OUT/'stage-current/manifest.json'
manifest = json.loads(path.read_text())
assert manifest['revision'] == 'market-crates-v3' and len(manifest['files']) == 16
def sha(path):
    with path.open('rb') as stream: return hashlib.file_digest(stream, 'sha256').hexdigest()
for name, row in manifest['files'].items():
    assert sha(ROOT/row['source']) == row['after']
    actual = ROOT/name
    assert sha(actual) == row['before'] if row['before'] else not actual.exists()
for name, value in manifest['source_sha256'].items(): assert sha(ROOT/name) == value
map_path = ROOT/'Tools/belltower_map.py'
text = map_path.read_text()
assert text.count('MarketCratesV3.stack( model, rng, Place, WOOD )') == 1
assert text.count('import belltower_market_crates_v3 as MarketCratesV3') == 1
manifest['map_source_at_publication_preparation'] = sha(map_path)
manifest['source_hook'] = 'Only the Market Street call selects MarketCratesV3; all other crate calls retain the shared builder.'
path.write_text(json.dumps(manifest, indent=2)+'\n')
allowed = ',\n'.join('    '+json.dumps(p) for p in manifest['files'])
script = r'''// Publish only this mirrored Market Street group through the active native editor.
var root = Sandbox.Project.Current.GetRootPath();
if (!System.IO.Path.GetFullPath(root).TrimEnd('\\').Equals(@"C:\sbox-projects\hc1\forked-shooter-main", StringComparison.OrdinalIgnoreCase))
    throw new InvalidOperationException("Unexpected project root.");
var folder = System.IO.Path.Combine(root, "output/belltower/crates-v3-20261021");
var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(folder, "stage-current/manifest.json")));
if (manifest["revision"].GetValue<string>() != "market-crates-v3" || manifest["crates"].GetValue<int>() != 6)
    throw new InvalidOperationException("Unexpected manifest.");
var allowed = new System.Collections.Generic.HashSet<string>(StringComparer.Ordinal) {
__ALLOWED__
};
var selected = Editor.SceneEditorSession.Active;
var playing = Game.IsPlaying;
var game = Game.ActiveScene?.Id;
var dirty = selected?.HasUnsavedChanges;
if (playing || dirty != false || selected?.Scene?.Source?.ResourcePath?.Equals("scenes/maps/belltower/belltower.scene", StringComparison.OrdinalIgnoreCase) != true)
    throw new InvalidOperationException("Publication requires the current saved, stopped Belltower document.");
string Hash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
void CheckInputs() {
    var mapSource = System.IO.File.ReadAllText(System.IO.Path.Combine(root, "Tools/belltower_map.py"));
    if (!mapSource.Contains("import belltower_market_crates_v3 as MarketCratesV3") || !mapSource.Contains("MarketCratesV3.stack( model, rng, Place, WOOD )"))
        throw new InvalidOperationException("The Market Street source hook changed.");
    foreach (var group in new[] { "source_sha256", "protected_sha256" })
        foreach (var pair in manifest[group].AsObject())
            if (Hash(System.IO.Path.Combine(root, pair.Key)) != pair.Value.GetValue<string>())
                throw new InvalidOperationException("A shared input changed: " + pair.Key);
}
CheckInputs();
var plans = new System.Collections.Generic.List<(string Source, string Target, string Backup, string After, int Order)>();
foreach (var pair in manifest["files"].AsObject()) {
    if (!allowed.Contains(pair.Key) || pair.Key.Contains("..")) throw new InvalidOperationException("Unexpected publication target.");
    var source = System.IO.Path.Combine(root, pair.Value["source"].GetValue<string>());
    var target = System.IO.Path.Combine(root, pair.Key);
    var after = pair.Value["after"].GetValue<string>();
    var before = pair.Value["before"]?.GetValue<string>();
    var backup = before is null ? null : System.IO.Path.Combine(root, pair.Value["backup"].GetValue<string>());
    if (Hash(source) != after || (backup is not null && Hash(backup) != before)) throw new InvalidOperationException("Staged source or backup changed.");
    if (System.IO.File.Exists(target) && Hash(target) == after) continue;
    if (before is null ? System.IO.File.Exists(target) : !System.IO.File.Exists(target) || Hash(target) != before)
        throw new InvalidOperationException("A shared resource changed: " + pair.Key);
    var order = pair.Key.Contains("/market-crates-v3/") || pair.Key.Contains("/compiler-safe/") ? 0 : pair.Key.EndsWith(".vmdl") ? 1 : 2;
    plans.Add((source, target, backup, after, order));
}
if (manifest["files"].AsObject().Count != allowed.Count) throw new InvalidOperationException("Publication set differs.");
var changed = new System.Collections.Generic.List<(string Target, string Backup)>();
try {
    foreach (var item in plans.OrderBy(p => p.Order)) {
        System.IO.Directory.CreateDirectory(System.IO.Path.GetDirectoryName(item.Target));
        var incoming = item.Target + ".market-crates-v3-incoming";
        try {
            System.IO.File.Copy(item.Source, incoming, true);
            if (Hash(incoming) != item.After) throw new InvalidOperationException("Incoming checksum failed.");
            System.IO.File.Move(incoming, item.Target, true);
            changed.Add((item.Target, item.Backup));
        }
        finally { if (System.IO.File.Exists(incoming)) System.IO.File.Delete(incoming); }
    }
}
catch {
    foreach (var item in changed.AsEnumerable().Reverse())
        if (item.Backup is not null) System.IO.File.Copy(item.Backup, item.Target, true);
        else if (System.IO.File.Exists(item.Target)) System.IO.File.Delete(item.Target);
    throw;
}
foreach (var item in plans.OrderBy(p => p.Order)) Editor.AssetSystem.RegisterFile(item.Target);
CheckInputs();
var preserved = ReferenceEquals(selected, Editor.SceneEditorSession.Active) && playing == Game.IsPlaying && game == Game.ActiveScene?.Id && dirty == selected?.HasUnsavedChanges;
var result = new { Revision = "market-crates-v3", Imported = plans.Count, EditorStatePreserved = preserved,
    Crates = 6, CoverBoxesRelocated = 6, SceneChanged = false, UnrelatedObjBytesExact = true };
System.IO.File.WriteAllText(System.IO.Path.Combine(folder, "native-import.json"), System.Text.Json.JsonSerializer.Serialize(result));
if (!preserved) throw new InvalidOperationException("Editor state changed during publication; inspect the completed result.");
return result;
'''.replace('__ALLOWED__', allowed)
(OUT/'import.cs.txt').write_text(script)
for side in ('west', 'east'):
    (OUT/f'compile-{side}.json').write_text(json.dumps({'path': f'models/maps/belltower/belltower_{side}.vmdl', 'full': False})+'\n')
print(json.dumps({'guarded_targets': len(manifest['files']), 'source_guards': len(manifest['source_sha256'])}))

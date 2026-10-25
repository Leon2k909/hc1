"""Extend the natively exercised exposure diagnostic with reversible art trials."""
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "Sources/Belltower/editor/capture-preview-consistent.cs.txt"
TARGET = ROOT / "Sources/Belltower/editor/capture-art-trials-oct19.cs.txt"
BASE_SHA = "8d2c601cfb1c36fbc9596e3fda305f95bf9227dd3893902c46805da027a37bc2"


def main():
    data = BASE.read_bytes()
    assert hashlib.sha256(data).hexdigest() == BASE_SHA, "Review a changed capture base before extending it."
    archive = ROOT / "output/belltower/quality/camera-consistency-v1/capture-helper-8d2c601c.cs.txt"
    archive.write_bytes(data)
    text = data.decode("utf-8")

    def insert(before, after):
        nonlocal text
        assert text.count(before) == 1, before
        text = text.replace(before, after)

    insert("// Diagnostic capture of an existing, saved Belltower document. No scene creation,\n// selection changes, asset trials, frame callbacks or saved-map changes.",
           "// Capture temporary surface/woodland trials in the existing saved Belltower document.\n// No scene creation, selected-document changes, frame callbacks or saved-map writes.")
    insert("output/belltower/quality/consistent-preview.json", "output/belltower/quality/art-preview-oct19.json")
    insert("Sources/Belltower/editor/capture-preview-consistent.cs.txt", "Sources/Belltower/editor/capture-art-trials-oct19.cs.txt")
    anchor = "// Match the established capture's distinct-material prewarm."
    setup = r'''var surfaceFinish = config["surface_finish"]?.GetValue<bool>() == true;
var forestVariant = config["forest_variant"]?.GetValue<string>() ?? "accepted";
if (forestVariant != "accepted" && forestVariant != "control" && forestVariant != "shapes")
    throw new InvalidOperationException("Unknown woodland variant.");
if (settleMilliseconds < 3000 || !ReferenceEquals(previous, session) || playing)
    throw new InvalidOperationException("Art comparisons require the active, stopped document and settled viewport.");
var trialManifests = new System.Collections.Generic.Dictionary<string, string>();
var surfaceMaterials = new System.Collections.Generic.Dictionary<string, Material>(StringComparer.OrdinalIgnoreCase);
var forestModels = new System.Collections.Generic.Dictionary<string, Model>(StringComparer.OrdinalIgnoreCase);
foreach (var revision in new[] { "surface-finish-v1", "forest-shapes-v1" })
{
    var file = System.IO.Path.Combine(root, "output/belltower/quality", revision, "manifest.json");
    var manifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(file));
    if (manifest["revision"].GetValue<string>() != revision) throw new InvalidOperationException("Wrong art revision.");
    foreach (var input in manifest["source_sha256"].AsObject())
        if (Hash(System.IO.Path.Combine(root, input.Key)) != input.Value.GetValue<string>())
            throw new InvalidOperationException("An art input changed: " + input.Key);
    foreach (var item in manifest[revision == "surface-finish-v1" ? "records" : "files"].AsArray())
        if (Hash(System.IO.Path.Combine(root, "Assets", item["path"].GetValue<string>())) != item["sha256"].GetValue<string>())
            throw new InvalidOperationException("A private art asset changed.");
    if (revision == "surface-finish-v1")
        foreach (var item in manifest["records"].AsArray())
            surfaceMaterials.Add(item["target"].GetValue<string>(), Material.Load(item["path"].GetValue<string>()));
    else
        foreach (var item in manifest["model_overrides"].AsArray())
            forestModels.Add(item["original"].GetValue<string>(), Model.Load(item["candidate"].GetValue<string>()));
    trialManifests.Add(revision, Hash(file));
}
var forestControl = Material.Load("materials/belltower/forest/shapes-v1/forest_control.vmat");
var forestShapes = Material.Load("materials/belltower/forest/shapes-v1/forest_trees.vmat");
if (surfaceMaterials.Count != 9 || forestModels.Count != 8 || surfaceMaterials.Values.Any(m => m is null || m.IsError)
    || forestModels.Values.Any(m => m is null || m.IsError) || forestControl is null || forestControl.IsError || forestShapes is null || forestShapes.IsError)
    throw new InvalidOperationException("An art resource did not load.");
var surfaceSlots = 0;
var forestSlots = 0;
var modelChanges = new System.Collections.Generic.List<(ModelRenderer Renderer, Model Original)>();
var materialChanges = new System.Collections.Generic.List<(ModelRenderer Renderer, int Slot, Material Original)>();
var rendererSnapshots = new System.Collections.Generic.Dictionary<ModelRenderer, string>();
void StoreRenderer(ModelRenderer renderer)
{
    if (!rendererSnapshots.ContainsKey(renderer))
        rendererSnapshots.Add(renderer, renderer.Serialize().ToJsonString());
}
'''
    insert(anchor, setup + anchor)
    insert("var materials = new System.Collections.Generic.HashSet<Material>();",
           "var materials = new System.Collections.Generic.HashSet<Material>(surfaceMaterials.Values);\nmaterials.Add(forestControl);\nmaterials.Add(forestShapes);")
    anchor = "try\n{\n    if (settleMilliseconds > 0)"
    application = r'''try
{
    using (scene.Push())
    {
    if (forestVariant == "shapes")
        foreach (var renderer in scene.GetAllComponents<ModelRenderer>())
        {
            if (renderer.Model?.ResourcePath is not string path || !forestModels.TryGetValue(path, out var replacement)) continue;
            StoreRenderer(renderer);
            modelChanges.Add((renderer, renderer.Model));
            renderer.Model = replacement;
            if (renderer.Materials.Count != 1) throw new InvalidOperationException("Unexpected woodland material slots.");
        }
    if (forestVariant == "shapes" && modelChanges.Count != 8) throw new InvalidOperationException("Expected eight woodland models.");
    foreach (var renderer in scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath?.Contains("models/maps/belltower/", StringComparison.OrdinalIgnoreCase) == true))
    {
        var woodland = renderer.Model.ResourcePath.StartsWith("models/maps/belltower/forest/", StringComparison.OrdinalIgnoreCase);
        for (var slot = 0; slot < renderer.Materials.Count; slot++)
        {
            Material replacement = null;
            if (woodland && forestVariant != "accepted")
                replacement = renderer.Model.ResourcePath.StartsWith("models/maps/belltower/forest/shapes-v1/", StringComparison.OrdinalIgnoreCase) ? forestShapes : forestControl;
            else if (surfaceFinish)
            {
                var path = renderer.Materials.GetOriginal(slot)?.ResourcePath;
                if (path is not null) surfaceMaterials.TryGetValue(path, out replacement);
            }
            if (replacement is null) continue;
            StoreRenderer(renderer);
            materialChanges.Add((renderer, slot, renderer.Materials.GetOverride(slot)));
            renderer.Materials.SetOverride(slot, replacement);
            if (woodland) forestSlots++; else surfaceSlots++;
        }
    }
    if (surfaceFinish && surfaceSlots == 0) throw new InvalidOperationException("No surface materials matched.");
    if (forestVariant != "accepted" && forestSlots != 88) throw new InvalidOperationException("Expected all 88 woodland slots.");
    }
    if (settleMilliseconds > 0)'''
    insert(anchor, application)
    insert("RequestedExposure = exposure, NativeEnabled", "TrialSurfaceSlots = surfaceSlots, TrialForestVariant = forestVariant, TrialForestSlots = forestSlots,\n            TrialModels = modelChanges.Count, TrialManifestSha256 = trialManifests,\n            RequestedExposure = exposure, NativeEnabled")
    insert("        try\n        {\n            tone.MinimumExposure = oldTone.MinimumExposure;",
           "        try\n        {\n            foreach (var item in modelChanges) if (item.Renderer.IsValid()) item.Renderer.Model = item.Original;\n            foreach (var item in materialChanges) if (item.Renderer.IsValid()) item.Renderer.Materials.SetOverride(item.Slot, item.Original);\n            tone.MinimumExposure = oldTone.MinimumExposure;")
    insert("    restored = new { MainCameraRestored", "    var assetsRestored = rendererSnapshots.All(s => s.Key.IsValid() && s.Key.Serialize().ToJsonString() == s.Value);\n    restored = new { AssetsRestored = assetsRestored, MainCameraRestored")
    insert("if (!mainRestored || !toneRestored || !camerasRestored || !objectsRestored || !statePreserved)",
           "if (!assetsRestored || !mainRestored || !toneRestored || !camerasRestored || !objectsRestored || !statePreserved)")
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    record = {"base": BASE.relative_to(ROOT).as_posix(), "base_sha256": BASE_SHA,
              "source": TARGET.relative_to(ROOT).as_posix(), "source_sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
              "native_trial_execution_pending": True}
    (ROOT / "output/belltower/quality/oct19-editor-slot/capture-source.json").write_text(json.dumps(record, indent=2)+"\n", encoding="utf-8")
    print(json.dumps(record))


if __name__ == "__main__":
    main()

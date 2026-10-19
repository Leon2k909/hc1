"""Derive the geometry study from the verified viewport capture implementation."""
import hashlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Sources/Belltower/editor/capture-viewport.cs.txt'
EXPECTED = '613d00218c3d9039e7fe46d7fa17cbe054322799e30de024e37158d37c1fff96'


def main():
    assert hashlib.sha256(BASE.read_bytes()).hexdigest() == EXPECTED, 'Review capture changes before regenerating'
    source = BASE.read_text(encoding='utf-8')
    def replace(old, new):
        nonlocal source
        assert source.count(old) == 1, old[:100]
        source = source.replace(old, new)
    replace('"output/belltower/quality/viewport-capture.json"', '"output/belltower/quality/forest-distribution-v1/capture.json"')
    replace('var mainCamera = scene.Camera;', '''
if(!forestCoverageTrial || forestCoverageStrength!=0 || groundEdgeTrial || forestTrial || streetTrial || weatheredPlasterTrial)
    throw new InvalidOperationException("The distribution study holds coverage strength at zero and uses no other asset trial.");
var distributionVariant=config["distribution_variant"].GetValue<string>();
if(distributionVariant!="accepted" && distributionVariant!="control" && distributionVariant!="clumped")
    throw new InvalidOperationException("Unknown distribution variant.");
string DistributionHash(string path) => Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(System.IO.File.ReadAllBytes(path))).ToLowerInvariant();
var distributionPath=System.IO.Path.Combine(root,"output/belltower/quality/forest-distribution-v1/manifest.json");
var distribution=System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(distributionPath));
foreach(var input in distribution["source_sha256"].AsObject())
    if(DistributionHash(System.IO.Path.Combine(root,input.Key))!=input.Value.GetValue<string>())
        throw new InvalidOperationException("A distribution input changed: "+input.Key);
foreach(var file in distribution["files"].AsArray())
    if(DistributionHash(System.IO.Path.Combine(root,"Assets",file["path"].GetValue<string>()))!=file["sha256"].GetValue<string>())
        throw new InvalidOperationException("Installed distribution source differs.");
var distributionModels=new System.Collections.Generic.List<(ModelRenderer Renderer,Model Original)>();
var distributionOverrides=new System.Collections.Generic.Dictionary<ModelRenderer,Material[]>();
var distributionTargets=new System.Collections.Generic.Dictionary<string,Model>(StringComparer.OrdinalIgnoreCase);
if(distributionVariant!="accepted")
foreach(var item in distribution["model_overrides"].AsArray())
{
    var model=Model.Load(item[distributionVariant].GetValue<string>());
    if(model is null || model.IsError) throw new InvalidOperationException("A private forest model failed to load.");
    distributionTargets.Add(item["original"].GetValue<string>(),model);
}
var mainCamera = scene.Camera;''')
    replace('    camera = scene.GetAllComponents<CameraComponent>()', '''
    if(Game.ActiveScene?.Id!=gameId || Game.IsPlaying!=playing || !ReferenceEquals(previous,Editor.SceneEditorSession.Active))
        throw new InvalidOperationException("Shared state changed during prewarm; inspect before continuing.");
    camera = scene.GetAllComponents<CameraComponent>()''')
    replace('        if(forestTrial)\n', '''
        if(distributionVariant!="accepted")
        {
            foreach(var renderer in scene.GetAllComponents<ModelRenderer>())
            {
                if(renderer.Model?.ResourcePath is not string path || !distributionTargets.TryGetValue(path,out var model)) continue;
                trialSnapshots.Add(renderer,renderer.Serialize().ToJsonString());
                distributionModels.Add((renderer,renderer.Model));
                distributionOverrides.Add(renderer,Enumerable.Range(0,renderer.Materials.Count).Select(renderer.Materials.GetOverride).ToArray());
                renderer.Model=model;
                if(renderer.Materials.Count!=1) throw new InvalidOperationException("A forest model changed its material layout.");
            }
            if(distributionModels.Count!=8) throw new InvalidOperationException("Expected eight original forest sector renderers.");
        }
        if(forestTrial)
''')
    replace('        TrialForestSectors=trialForest is null ? 0 : trialForest.Children.Count,', '''
        DistributionVariant=distributionVariant,DistributionModels=distributionModels.Count,DistributionManifestSha256=DistributionHash(distributionPath),
        TrialForestSectors=trialForest is null ? 0 : trialForest.Children.Count,''')
    replace('"Sources/Belltower/editor/capture-viewport.cs.txt"', '"Sources/Belltower/editor/capture-forest-distribution.cs.txt"')
    replace('    foreach(var item in trialOverrides) if(item.Renderer.IsValid()) item.Renderer.Materials.SetOverride(item.Slot,item.Original);', '''
    foreach(var item in distributionModels) if(item.Renderer.IsValid()) item.Renderer.Model=item.Original;
    foreach(var item in trialOverrides) if(item.Renderer.IsValid()) item.Renderer.Materials.SetOverride(item.Slot,item.Original);
    foreach(var pair in distributionOverrides)
    {
        if(!pair.Key.IsValid() || pair.Key.Materials.Count!=pair.Value.Length) throw new InvalidOperationException("Original model material layout did not restore.");
        for(var slot=0;slot<pair.Value.Length;slot++) pair.Key.Materials.SetOverride(slot,pair.Value[slot]);
    }''')
    replace('    if (camera.IsValid()) { camera.WorldPosition=oldPosition;', '''
    var distributionRestored=distributionModels.All(x=>x.Renderer.IsValid() && x.Renderer.Model?.ResourcePath==x.Original.ResourcePath) && materialsRestored;
    System.IO.File.WriteAllText(System.IO.Path.Combine(destination,name+"-distribution-restore.json"),System.Text.Json.JsonSerializer.Serialize(new{ModelsRestored=distributionRestored,Models=distributionModels.Count}));
    if (camera.IsValid()) { camera.WorldPosition=oldPosition;''')
    replace('    if(!forestRestored || !groundEdgesRestored)', '''
    if(!distributionRestored) throw new InvalidOperationException("Original woodland renderer state differs; inspect before further work.");
    if(!forestRestored || !groundEdgesRestored)''')
    target = ROOT / 'Sources/Belltower/editor/capture-forest-distribution.cs.txt'
    target.write_text('// Derived from verified capture helper ' + EXPECTED + '\n' + source, encoding='utf-8')
    print(hashlib.sha256(target.read_bytes()).hexdigest())


if __name__ == '__main__':
    main()

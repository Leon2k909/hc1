"""Extend the verified active-viewport comparison with zero/rounded crown controls."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'Sources/Belltower/editor/capture-art-trials-oct19.cs.txt'
EXPECTED='ec5a70db517b6cb59295a14a01a556d1a259f87175557666eabe923f49cb9791'
TARGET=ROOT/'Sources/Belltower/editor/capture-art-trials-oct20.cs.txt'
OUT=ROOT/'output/belltower/quality/forest-volume-v1'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert sha(SOURCE)==EXPECTED,'Review a changed capture base before deriving it.'
    archive=OUT/'capture-base-oct19.cs.txt'
    if not archive.exists():archive.write_bytes(SOURCE.read_bytes())
    source=SOURCE.read_text()
    def replace(old,new):
        nonlocal source
        assert source.count(old)==1,old[:100]
        source=source.replace(old,new,1)
    replace('output/belltower/quality/art-preview-oct19.json','output/belltower/quality/art-preview-oct20.json')
    replace('Sources/Belltower/editor/capture-art-trials-oct19.cs.txt','Sources/Belltower/editor/capture-art-trials-oct20.cs.txt')
    replace('if (forestVariant != "accepted" && forestVariant != "control" && forestVariant != "shapes")',
            'if (!new[] { "accepted", "control", "shapes", "volume-control", "volume" }.Contains(forestVariant))')
    replace('var surfaceSlots = 0;', '''var useShapeModels = forestVariant == "shapes" || forestVariant == "volume-control" || forestVariant == "volume";
var volumeFile = System.IO.Path.Combine(root, "output/belltower/quality/forest-volume-v1/manifest.json");
var volumeManifest = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(volumeFile));
foreach (var input in volumeManifest["source_sha256"].AsObject())
    if (Hash(System.IO.Path.Combine(root, input.Key)) != input.Value.GetValue<string>())
        throw new InvalidOperationException("A volume trial source changed: " + input.Key);
foreach (var item in volumeManifest["files"].AsArray())
    if (Hash(System.IO.Path.Combine(root, "Assets", item["path"].GetValue<string>())) != item["sha256"].GetValue<string>())
        throw new InvalidOperationException("An imported volume asset changed.");
var forestVolumeControl = Material.Load(volumeManifest["control_material"].GetValue<string>());
var forestRounded = Material.Load(volumeManifest["candidate_material"].GetValue<string>());
if (forestVolumeControl is null || forestVolumeControl.IsError || forestRounded is null || forestRounded.IsError)
    throw new InvalidOperationException("A volume material did not load.");
trialManifests.Add("forest-volume-v1", Hash(volumeFile));
var surfaceSlots = 0;''')
    replace('materials.Add(forestShapes);','materials.Add(forestShapes);\nmaterials.Add(forestVolumeControl);\nmaterials.Add(forestRounded);')
    replace('if (forestVariant == "shapes")','if (useShapeModels)')
    replace('if (forestVariant == "shapes" && modelChanges.Count != 8)',
            'if (useShapeModels && modelChanges.Count != 8)')
    replace('''            if (woodland && forestVariant != "accepted")
                replacement = renderer.Model.ResourcePath.StartsWith("models/maps/belltower/forest/shapes-v1/", StringComparison.OrdinalIgnoreCase) ? forestShapes : forestControl;''',
            '''            if (woodland && forestVariant != "accepted")
            {
                var changedSector = renderer.Model.ResourcePath.StartsWith("models/maps/belltower/forest/shapes-v1/", StringComparison.OrdinalIgnoreCase);
                replacement = !changedSector ? forestControl : forestVariant == "volume" ? forestRounded
                    : forestVariant == "volume-control" ? forestVolumeControl : forestShapes;
            }''')
    replace('TrialModels = modelChanges.Count, TrialManifestSha256 = trialManifests,',
            'TrialModels = modelChanges.Count, TrialManifestSha256 = trialManifests,\n            TrialCrownVolumeStrength = forestVariant == "volume" ? .42f : 0f,')
    TARGET.write_text(source,encoding='utf8',newline='\n')
    record={'base_sha256':EXPECTED,'source':TARGET.relative_to(ROOT).as_posix(),'sha256':sha(TARGET),
            'requires_active_stopped_saved_belltower':True,'settle_ms':5000,
            'temporary_shape_models':8,'all_forest_slots':88,'additional_temporary_game_objects':0,
            'native_render_run':False,'static_api_compile_pending':True,
            'restoration':'Inherited model/material/camera/tone/scene/object identity checks. No await retains Scene.Push or a camera pin.'}
    (OUT/'capture-source.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf8')
    print(json.dumps(record,indent=2))


if __name__=='__main__':main()

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("phase", choices=("before", "preview", "after", "tree"))
args = parser.parse_args()
root = Path(__file__).resolve().parents[3]
work = Path(__file__).resolve().parent
text = (root / "Sources/Veridant/editor/capture.cs.txt").read_text(encoding="utf-8")
destination = f"output/veridant/stone-pine-v2/captures/{args.phase}"
text = text.replace("output/veridant/captures", destination)
if args.phase == "preview":
    text = text.replace("scene.Deserialize(root);", '''scene.Deserialize(root);
        foreach (var renderer in scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath == "models/maps/veridant/veridant_foliage.vmdl"))
            renderer.Model = Model.Load("models/maps/veridant/stone-pine-v2/veridant_foliage_preview.vmdl");''')
if args.phase == "tree":
    text = text.replace('"Sun", "Sky", "Fog", "Look", "Veridant", "Lights", "Reflection Probes", "Volumetric Fog"',
                        '"Sun", "Sky", "Fog", "Look"')
    text = text.replace("scene.Deserialize(root);", '''scene.Deserialize(root);
        var tree = new GameObject(true, "Stone pine preview");
        tree.Components.Create<ModelRenderer>().Model = Model.Load("models/maps/veridant/stone-pine-v2/veridant_stone_pine.vmdl");
        var ground = new GameObject(true, "Preview ground");
        var groundRenderer = ground.Components.Create<ModelRenderer>();
        groundRenderer.Model = Model.Cube;
        var size = Model.Cube.Bounds.Size;
        ground.WorldPosition = new Vector3(676,0,125);
        ground.WorldScale = new Vector3(1000/size.x,1000/size.y,6/size.z);
        groundRenderer.MaterialOverride = Material.Load("materials/veridant/vr_stone.vmat");''')
(work / f"capture-{args.phase}.cs.txt").write_text(text, encoding="utf-8")
folder = root / destination
folder.mkdir(parents=True, exist_ok=True)
(folder / "config.json").write_text((work / "capture-config.json").read_text(encoding="utf-8"), encoding="utf-8")
print(folder)

"""Old and new hose reel cabinet in the real map, under its own light, in an isolated editor scene: no tab or play state is touched and nothing is saved.
python compare_hose.py <project root> [old]

The old cabinet's faces are in the hall's merged models and can't be hidden here, and the new one is deeper and glazed, so it would show the old box through its glass.
So the new one is shot on the bare wall 100 in along (engine y -580, between the old box and the extinguisher), from the same offsets.
A first pass of shots is thrown away, as the first shots after loading come out darker while exposure settles.
"""
import json
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = sys.argv[1]
OLD_ONLY = len(sys.argv) > 2 and sys.argv[2] == "old"
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/hose-reel"
FULL = os.path.join(ROOT, OUT.replace("/", os.sep))
os.makedirs(FULL, exist_ok=True)
MODEL = "models/maps/riverdale/hose_reel_v2/hose_reel.vmdl"
# The hall's north wall at engine x 2000 faces -x: the cabinet at y -680, its bottom at z 28.5.
POS, YAW = (2000.0, -680.0, 28.5), 180.0
NEW_POS = (2000.0, -580.0, 28.5)
# In the board's frame: out from the wall, the viewer's right, height above its bottom.
SHOTS = [("front", (70, 0, 34), (0, 0, 17)), ("angle", (36, 40, 30), (2, 0, 16)), ("close", (20, -6, 26), (2, 0, 16)), ("eye", (110, -30, 36), (0, 0, 18))]

TEMPLATE = r'''
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "%OUT%");
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Sun", "Sky", "Fog", "Look", "Riverdale", "Lights", "Reflection Probes", "Indirect Light" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Riverdale/riverdale.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
root["GameObjects"] = objects;
if (root["SceneProperties"]?["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject sceneProperties) sceneProperties["WantsSystemScene"] = false;
Model model = %LOADMODEL%;
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    GameObject board = null;
    var exposures = new System.Collections.Generic.List<string>();
    var frame = Rotation.FromYaw(%YAW%f);
    var origin = %POS%;
    var originNew = %NEWPOS%;
    using (scene.Push())
    {
        scene.Deserialize(root);
        foreach (var tonemap in scene.GetAllComponents<Tonemapping>())
        {
            var hold = ( tonemap.MinimumExposure + tonemap.MaximumExposure ) / 2f;
            exposures.Add( tonemap.Mode + " " + tonemap.MinimumExposure + ".." + tonemap.MaximumExposure );
            tonemap.AutoExposureEnabled = true;
            tonemap.MinimumExposure = tonemap.MaximumExposure = hold;
            tonemap.Rate = 10;
        }
        if (model is not null)
        {
            board = new GameObject(false, "New hose reel");
            board.WorldPosition = originNew;
            board.WorldRotation = frame;
            board.Components.Create<ModelRenderer>().Model = model;
        }
        var holder = new GameObject(false, "Capture camera");
        camera = holder.Components.Create<CameraComponent>();
        camera.ZNear = 1;
        camera.ZFar = 30000;
        holder.Enabled = true;
        scene.EditorTick(.016f, .016f);
        preRender.Invoke(scene, null);
        preCameraRender.Invoke(scene, null);
    }
    var textureNames = new[] { "g_tColor", "g_tNormal", "g_tRoughness", "g_tAmbientOcclusion", "SkyTexture" };
    foreach (var material in scene.GetAllComponents<ModelRenderer>().Where(r => r.Model is not null).SelectMany(r => r.Model.Materials).Distinct())
        foreach (var texture in textureNames.Select(material.GetTexture).Append(material.FirstTexture).Where(t => t is not null).Distinct())
            texture.MarkUsed(1024);
    for (var wait = 0; wait < 240; wait++)
    {
        using (scene.Push()) { scene.EditorTick(.016f, .016f); preRender.Invoke(scene, null); }
        if (model is not null)
            foreach (var material in model.Materials)
                foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                    texture.MarkUsed(4096);
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target)[] { %SHOTS% };
    foreach (var variant in new[] { "settling", "old", "new" })
    {
        if (variant == "new" && board is null) break;
        using (scene.Push()) { if (board is not null) board.Enabled = variant != "old"; }
        var at = variant == "new" ? originNew : origin;
        foreach (var shot in shots)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var bitmap = new Bitmap(1600, 900);
            for (var f = 0; f < 12; f++)
            {
                using (scene.Push())
                {
                    camera.WorldPosition = at + frame * shot.eye;
                    camera.WorldRotation = Rotation.LookAt(frame * shot.target - frame * shot.eye);
                    camera.FieldOfView = 75;
                    scene.EditorTick(.016f, .016f);
                    preRender.Invoke(scene, null);
                    preCameraRender.Invoke(scene, null);
                    camera.RenderToBitmap(bitmap);
                }
                if (model is not null)
                    foreach (var material in model.Materials)
                        foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                            texture.MarkUsed(4096);
                await Task.Delay(16, cancellationToken);
            }
            if (variant != "settling") System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, variant + "_" + shot.name + ".png"), bitmap.ToPng());
        }
    }
    return new { Renderers = scene.GetAllComponents<ModelRenderer>().Count(), Exposures = exposures, Model = model?.ResourcePath, Error = model?.IsError };
}
finally { scene.Destroy(); }
'''


def v(p):
    return f"new Vector3({p[0]}f, {p[1]}f, {p[2]}f)"


load = "null" if OLD_ONLY else f'Model.Load("{MODEL}")'
code = TEMPLATE.replace("%OUT%", OUT).replace("%YAW%", str(YAW)).replace("%POS%", v(POS)).replace("%NEWPOS%", v(NEW_POS)).replace("%LOADMODEL%", load)
code = code.replace("%SHOTS%", ", ".join(f'("{n}", {v(e)}, {v(t)})' for n, e, t in SHOTS))
path = os.path.join(FULL, "compare_hose.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
run = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": path})], cwd=ROOT, capture_output=True, timeout=175)
print(" ".join((run.stdout + run.stderr).decode("utf-8", "replace").split())[:500])

if not OLD_ONLY:
    W, H = 800, 450
    sheet = Image.new("RGB", (W * 2, H * len(SHOTS) + 60), (16, 16, 18))
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 30)
    d = ImageDraw.Draw(sheet)
    d.text((W // 2, 30), "OLD", font=font, fill=(235, 235, 235), anchor="mm")
    d.text((W + W // 2, 30), "NEW", font=font, fill=(235, 235, 235), anchor="mm")
    for r, (name, _, _) in enumerate(SHOTS):
        for c, variant in enumerate(("old", "new")):
            p = os.path.join(FULL, f"{variant}_{name}.png")
            if os.path.exists(p):
                sheet.paste(Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS), (c * W, 60 + r * H))
    sheet.save(os.path.join(FULL, "before_after.png"))

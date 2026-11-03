"""Old and new lawn chairs in the real map, under its own light, in an isolated editor scene: no tab or play state is touched and nothing is saved.
python compare_chair.py <project root> [old|new]

The old chairs are in the map's merged models and can't be hidden here, so the new ones are shot on open ground 50 in to the old yard chair's left, from the same
offsets: the green one where the old one would be, the red one (the porch's colours) beside it.
A first pass of shots is thrown away, as the first shots after loading come out darker while exposure settles.
"""
import json
import math
import os
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

ROOT = sys.argv[1]
OLD_ONLY = len(sys.argv) > 2 and sys.argv[2] == "old"
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/lawn-chair"
FULL = os.path.join(ROOT, OUT.replace("/", os.sep))
os.makedirs(FULL, exist_ok=True)
GREEN = "models/props/riverside/lawn_chair_v2/lawn_chair_green.vmdl"
RED = "models/props/riverside/lawn_chair_v2/lawn_chair_red.vmdl"
SET = "yard"
# The yard's chair at engine (1060, 420, 0), facing plan (0.7, 0.7): engine yaw 315. Shots are in its frame: x the way it faces, y its left.
POS, YAW = (1060.0, 420.0, 0.0), 315.0


def frame(p):
    c, s = math.cos(math.radians(YAW)), math.sin(math.radians(YAW))
    return (c * p[0] - s * p[1], s * p[0] + c * p[1], p[2])


NEW_POS = tuple(a + b for a, b in zip(POS, frame((0.0, 50.0, 0.0))))
NEW = [(GREEN, (0.0, 0.0, 0.0), YAW), (RED, frame((-4.0, 30.0, 0.0)), YAW + 24.0)]  # World offsets from NEW_POS, yaw.
SHOTS = [("front", (70, -6, 40), (0, 4, 18)), ("angle", (42, -36, 46), (0, 6, 17)), ("close", (24, -8, 34), (-2, 0, 18)), ("back", (-48, -30, 44), (0, 4, 20)),
         ("eye", (120, -50, 64), (0, 10, 18))]
ORDER = ["front", "angle", "close", "back", "eye"]

TEMPLATE = r'''
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "%OUT%");
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Moon", "Sky", "Fog", "Look", "Riverside", "Lights", "Fires", "Burn Drums", "Cooler", "Teddy", "Propane Cylinders", "Reflection Probes", "Volumetric Fog" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Riverside/riverside.scene"))).AsObject();
var objects = new System.Text.Json.Nodes.JsonArray();
foreach (var item in root["GameObjects"].AsArray())
    if (visual.Contains(item["Name"]?.GetValue<string>() ?? "")) objects.Add(item.DeepClone());
root["GameObjects"] = objects;
if (root["SceneProperties"]?["NavMesh"] is System.Text.Json.Nodes.JsonObject nav) nav["Enabled"] = false;
if (root["SceneProperties"] is System.Text.Json.Nodes.JsonObject sceneProperties) sceneProperties["WantsSystemScene"] = false;
var news = new (string path, Vector3 offset, float yaw)[] { %NEWS% };
var models = new System.Collections.Generic.List<Model>();
if (%WANTNEW%) foreach (var n in news) models.Add(Model.Load(n.path));
Model model = models.FirstOrDefault();
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
            board = new GameObject(false, "New lawn chairs");
            board.WorldPosition = originNew;
            for (var k = 0; k < news.Length; k++)
            {
                var piece = new GameObject(board, true, "Chair");
                piece.LocalPosition = news[k].offset;
                piece.LocalRotation = Rotation.FromYaw(news[k].yaw);
                piece.Components.Create<ModelRenderer>().Model = models[k];
            }
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
        foreach (var m in models)
            foreach (var material in m.Materials)
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
                foreach (var m in models)
                    foreach (var material in m.Materials)
                        foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                            texture.MarkUsed(4096);
                await Task.Delay(16, cancellationToken);
            }
            if (variant != "settling") System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, variant + "_" + shot.name + ".png"), bitmap.ToPng());
        }
    }
    return new { Renderers = scene.GetAllComponents<ModelRenderer>().Count(), Exposures = exposures, Models = models.Select(m => m.ResourcePath + (m.IsError ? " ERROR" : "")).ToArray() };
}
finally { scene.Destroy(); }
'''


def v(p):
    return f"new Vector3({p[0]}f, {p[1]}f, {p[2]}f)"


code = TEMPLATE.replace("%OUT%", OUT).replace("%YAW%", str(YAW)).replace("%POS%", v(POS)).replace("%NEWPOS%", v(NEW_POS)).replace("%WANTNEW%", "false" if OLD_ONLY else "true").replace("%NEWS%", ", ".join(f'("{p}", {v(o)}, {y}f)' for p, o, y in NEW))
code = code.replace("%SHOTS%", ", ".join(f'("{n}", {v(e)}, {v(t)})' for n, e, t in SHOTS))
path = os.path.join(FULL, "compare_chair.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
run = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": path})], cwd=ROOT, capture_output=True, timeout=175)
print(" ".join((run.stdout + run.stderr).decode("utf-8", "replace").split())[:500])

if not OLD_ONLY:
    names = [n for n in ORDER if os.path.exists(os.path.join(FULL, f"old_{n}.png")) and os.path.exists(os.path.join(FULL, f"new_{n}.png"))]
    W, H = 800, 450
    sheet = Image.new("RGB", (W * 2, H * len(names) + 60), (16, 16, 18))
    font = ImageFont.truetype(r"C:\Windows\Fonts\arialbd.ttf", 30)
    d = ImageDraw.Draw(sheet)
    d.text((W // 2, 30), "OLD", font=font, fill=(235, 235, 235), anchor="mm")
    d.text((W + W // 2, 30), "NEW", font=font, fill=(235, 235, 235), anchor="mm")
    for r, name in enumerate(names):
        for c, variant in enumerate(("old", "new")):
            sheet.paste(Image.open(os.path.join(FULL, f"{variant}_{name}.png")).convert("RGB").resize((W, H), Image.LANCZOS), (c * W, 60 + r * H))
    sheet.save(os.path.join(FULL, "before_after.png"))

"""Old and new propane cylinders in the real map, under its own light, in an isolated editor scene: no tab or play state is touched and nothing is saved.
python compare_propane.py <project root> [old]

The old bottles are in the pad's merged model and can't be hidden here, so the new row is shot on open ground beside the old one, from the same offsets.
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
OUT = "output/asset-improvement-20261030/propane"
FULL = os.path.join(ROOT, OUT.replace("/", os.sep))
os.makedirs(FULL, exist_ok=True)
BIG = "models/props/riverside/propane_v2/propane_100.vmdl"
SMALL = "models/props/riverside/propane_v2/propane_20.vmdl"
SET = sys.argv[3] if len(sys.argv) > 3 else "row"
if SET == "row":
    # The pad's row of three at engine x -560, y 380 / 362 / 344, on the ground at z 96, the south fence behind them. Shots look south at the middle one.
    POS, YAW = (-560.0, 362.0, 96.0), 0.0
    NEW_POS = (-560.0, 362.0 - 80.0, 96.0)
    NEW = [(BIG, (0.0, 18.0, 0.0), 23.0), (BIG, (0.0, 0.0, 0.0), 141.0), (BIG, (0.0, -18.0, 0.0), 278.0)]  # Offsets from NEW_POS, yaw.
    SHOTS = [("front", (80, 0, 40), (0, 0, 24)), ("angle", (50, 45, 50), (0, 0, 22)), ("close", (24, -10, 50), (0, 0, 42)), ("top", (16, -6, 66), (0, 0, 45)),
             ("eye", (140, -40, 64), (0, 0, 24))]
else:
    # The 20 lb pair on the camper's tongue at engine x -130, y -255 / -237, standing at z 114. The new pair is shot standing on the pad's ground beside the new row.
    POS, YAW = (-130.0, -246.0, 114.0), 0.0
    NEW_POS = (-560.0, 362.0 - 140.0, 96.0)
    NEW = [(SMALL, (0.0, 9.0, 0.0), 40.0), (SMALL, (0.0, -9.0, 0.0), 205.0)]
    SHOTS = [("pair", (44, 0, 26), (0, 0, 10)), ("pair_angle", (26, 30, 34), (0, 0, 10))]
ORDER = ["front", "angle", "close", "top", "eye", "pair", "pair_angle"]

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
            board = new GameObject(false, "New propane");
            board.WorldPosition = originNew;
            for (var k = 0; k < news.Length; k++)
            {
                var piece = new GameObject(board, true, "Bottle");
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
path = os.path.join(FULL, f"compare_propane_{SET}.cs")
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

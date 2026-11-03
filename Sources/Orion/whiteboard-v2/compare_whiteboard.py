"""Old and new whiteboard in the real map, under its own light, in an isolated editor scene: no tab or play state is touched and nothing is saved.
python compare_whiteboard.py <project root> [old]

The old board is one quad in orion_fuel's merged model, 0.5 in off the wall. The new one's face stands 0.62 in off the wall, so it covers the old quad where it stands.
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
OUT = "output/asset-improvement-20261030/whiteboard"
FULL = os.path.join(ROOT, OUT.replace("/", os.sep))
os.makedirs(FULL, exist_ok=True)
MODEL = "models/maps/orion/whiteboard_v2/whiteboard.vmdl"
# On the OPS room's north wall: the wall's face at engine x 823, the board's middle at y -900, its bottom at z 340. The room is to -x.
POS, YAW = (823.0, -900.0, 340.0), 180.0
# In the board's frame: out from the wall, the viewer's right, height above its bottom.
SHOTS = [("front", (78, 0, 34), (0, 0, 28)), ("angle", (60, 58, 30), (0, -8, 26)), ("close", (30, -26, 22), (0, -26, 18)), ("tray", (20, 18, 10), (1.5, 10, 1))]

TEMPLATE = r'''
var projectRoot = Sandbox.Project.Current.GetRootPath();
var destination = System.IO.Path.Combine(projectRoot, "%OUT%");
var visual = new System.Collections.Generic.HashSet<string>(new[] { "Sun", "Sky", "Fog", "Look", "Orion", "Lights", "Reflection Probes" }, StringComparer.OrdinalIgnoreCase);
var root = System.Text.Json.Nodes.JsonNode.Parse(System.IO.File.ReadAllText(System.IO.Path.Combine(projectRoot, "Assets/scenes/maps/Orion/orion.scene"))).AsObject();
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
            board = new GameObject(false, "New whiteboard");
            board.WorldPosition = origin;
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
        foreach (var shot in shots)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var bitmap = new Bitmap(1600, 900);
            for (var f = 0; f < 12; f++)
            {
                using (scene.Push())
                {
                    camera.WorldPosition = origin + frame * shot.eye;
                    camera.WorldRotation = Rotation.LookAt((origin + frame * shot.target) - (origin + frame * shot.eye));
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
code = TEMPLATE.replace("%OUT%", OUT).replace("%YAW%", str(YAW)).replace("%POS%", v(POS)).replace("%LOADMODEL%", load)
code = code.replace("%SHOTS%", ", ".join(f'("{n}", {v(e)}, {v(t)})' for n, e, t in SHOTS))
path = os.path.join(FULL, "compare_whiteboard.cs")
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

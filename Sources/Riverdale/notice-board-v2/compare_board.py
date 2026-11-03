"""Old and new notice board in the real map, under its own light, in an isolated editor scene: no tab or play state is touched and nothing is saved.
python compare_board.py <project root> [board index]

The old board can't be hidden, as its faces are in merged models, so the "after" stands the new one 1.3 in out from the wall, just covering it.
"""
import json
import os
import subprocess
import sys

from PIL import Image

ROOT = sys.argv[1]
INDEX = int(sys.argv[2]) if len(sys.argv) > 2 else 3
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/notice-board"
FULL = os.path.join(ROOT, OUT.replace("/", os.sep))

# Bottom centre on the wall, and the yaw that faces the room.
BOARDS = [((1205, 1000, 46), -90), ((1205, -1000, 46), 90), ((2000, -95, 46), 180), ((1200, 670, 346), 0), ((1200, -670, 346), 0)]
pos, yaw = BOARDS[INDEX]
# Shots in the board's own frame: out from the wall, the viewer's right, height above its bottom.
SHOTS = [("front", (120, 0, 18), (0, 0, 12)), ("close", (34, -6, 15), (0, -6, 12)), ("angle", (46, 62, 20), (0, 2, 12)), ("detail", (15, 9, 9), (0.5, 9, 7)), ("far", (500, 0, 18), (0, 0, 12)), ("further", (780, 40, 40), (0, 0, 12))]

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
var model = Model.Load("models/maps/riverdale/notice_board_v2/notice_board.vmdl");
if (model is null || model.IsError) throw new InvalidOperationException("The new board hasn't compiled.");
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    GameObject board;
    var exposures = new System.Collections.Generic.List<string>();
    var frame = Rotation.FromYaw(%YAW%f);
    var origin = %POS%;
    using (scene.Push())
    {
        scene.Deserialize(root);
        foreach (var tonemap in scene.GetAllComponents<Tonemapping>())
        {
            // The top of the map's range: the exposure this dim corner settles at when a player looks at it.
            var hold = tonemap.MaximumExposure;
            exposures.Add( tonemap.Mode + " " + tonemap.MinimumExposure + ".." + tonemap.MaximumExposure );
            tonemap.AutoExposureEnabled = true;
            tonemap.MinimumExposure = tonemap.MaximumExposure = hold;
            tonemap.Rate = 10;
        }
        board = new GameObject(false, "New board");
        board.WorldPosition = origin + frame * new Vector3(1.3f, 0, 0);
        board.WorldRotation = frame;
        board.Components.Create<ModelRenderer>().Model = model;
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
        foreach (var material in model.Materials)
            foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                texture.MarkUsed(4096);
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target)[] { %SHOTS% };
    foreach (var variant in new[] { "settling", "old", "new" })
    {
        using (scene.Push()) { board.Enabled = variant != "old"; }
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
                    camera.FieldOfView = 70;
                    scene.EditorTick(.016f, .016f);
                    preRender.Invoke(scene, null);
                    preCameraRender.Invoke(scene, null);
                    camera.RenderToBitmap(bitmap);
                }
                foreach (var material in model.Materials)
                    foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                        texture.MarkUsed(4096);
                await Task.Delay(16, cancellationToken);
            }
            System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, variant + "_" + shot.name + ".png"), bitmap.ToPng());
        }
    }
    return new { Renderers = scene.GetAllComponents<ModelRenderer>().Count(), Exposures = exposures, Materials = model.Materials.Select(m => m.ResourcePath + " " + m.GetTexture("g_tColor")?.Width).ToArray() };
}
finally { scene.Destroy(); }
'''


def v(p):
    return f"new Vector3({p[0]}f, {p[1]}f, {p[2]}f)"


code = TEMPLATE.replace("%OUT%", OUT).replace("%YAW%", str(yaw)).replace("%POS%", v(pos))
code = code.replace("%SHOTS%", ", ".join(f'("{n}", {v(e)}, {v(t)})' for n, e, t in SHOTS))
path = os.path.join(FULL, "compare_board.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
run = subprocess.run([CLI, "--call", "run_csharp", json.dumps({"path": path})], cwd=ROOT, capture_output=True, timeout=175)
print((run.stdout + run.stderr).decode("utf-8", "replace")[:700])

# Old above new for each shot worth comparing.
for name in ("front", "close", "angle", "detail", "far"):
    a, b = os.path.join(FULL, f"old_{name}.png"), os.path.join(FULL, f"new_{name}.png")
    if os.path.exists(a) and os.path.exists(b):
        sheet = Image.new("RGB", (1600, 1800))
        sheet.paste(Image.open(a).convert("RGB"), (0, 0))
        sheet.paste(Image.open(b).convert("RGB"), (0, 900))
        sheet.save(os.path.join(FULL, f"compare_{name}.png"))

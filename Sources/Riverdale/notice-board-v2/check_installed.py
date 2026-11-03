"""See the installed boards where the scene puts them, with nothing added: python check_installed.py <project root>

Waits for the open editor to recompile the two OBJs the install cut, since a look before that shows the old faces. Renders the real scene in an isolated editor scene, so no
tab or play state is touched and nothing is saved. Writes installed_<k>.png and one sheet, and says which of the boards draw the new model.
"""
import json
import math
import os
import subprocess
import sys
import time

from PIL import Image

ROOT = sys.argv[1]
CLI = r"C:\Program Files (x86)\Steam\steamapps\common\sbox\bin\managed\sbox-cli.exe"
OUT = "output/asset-improvement-20261030/notice-board"
FULL = os.path.join(ROOT, OUT.replace("/", os.sep))
BASE = os.path.join(ROOT, "Assets", "models", "maps", "riverdale")


def call(tool, args=None, timeout=170):
    cmd = [CLI, "--call", tool] + ([json.dumps(args)] if args is not None else [])
    run = subprocess.run(cmd, cwd=ROOT, capture_output=True, timeout=timeout)
    return (run.stdout + run.stderr).decode("utf-8", "replace")


for name in ("riverdale_hall_detail", "riverdale_hall_fine"):
    source = os.path.join(BASE, name + ".obj")
    built = os.path.join(BASE, name + ".vmdl_c")
    started = time.time()
    while os.path.getmtime(built) < os.path.getmtime(source):
        if time.time() - started > 420:
            print(name, "still hasn't recompiled after 7 minutes", flush=True)
            sys.exit(1)
        time.sleep(10)
    print(name, f"recompiled, waited {time.time() - started:.0f}s", flush=True)

scene = json.loads(open(os.path.join(ROOT, "Assets", "scenes", "maps", "Riverdale", "riverdale.scene"), encoding="utf-8").read())
world = next(o for o in scene["GameObjects"] if o.get("Name") == "Riverdale")
group = next(c for c in world["Children"] if c.get("Name") == "Notice Boards")
shots = []
for k, item in enumerate(group["Children"]):
    x, y, z = map(float, item["Position"].split(","))
    qx, qy, qz, qw = map(float, item["Rotation"].split(","))
    yaw = 2 * math.atan2(qz, qw)
    out = (math.cos(yaw), math.sin(yaw))
    right = (-math.sin(yaw) * -1, math.cos(yaw))
    right = (-out[1], out[0])
    eye = (x + out[0] * 72 + right[0] * 22, y + out[1] * 72 + right[1] * 22, z + 24)
    target = (x, y, z + 12)
    shots.append((f"installed_{k}", eye, target))
    print(k, item["Position"], f"yaw {math.degrees(yaw):.0f}", flush=True)


def v(p):
    return f"new Vector3({p[0]:.2f}f, {p[1]:.2f}f, {p[2]:.2f}f)"


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
var scene = Scene.CreateEditorScene();
var flags = System.Reflection.BindingFlags.Instance | System.Reflection.BindingFlags.Public | System.Reflection.BindingFlags.NonPublic;
var preRender = typeof(Scene).GetMethod("PreRender", flags, null, Type.EmptyTypes, null);
var preCameraRender = typeof(Scene).GetMethod("PreCameraRender", flags, null, Type.EmptyTypes, null);
try
{
    CameraComponent camera;
    using (scene.Push())
    {
        scene.Deserialize(root);
        foreach (var tonemap in scene.GetAllComponents<Tonemapping>())
        {
            var hold = tonemap.MaximumExposure;
            tonemap.AutoExposureEnabled = true;
            tonemap.MinimumExposure = tonemap.MaximumExposure = hold;
            tonemap.Rate = 10;
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
        foreach (var material in model.Materials)
            foreach (var texture in textureNames.Select(material.GetTexture).Where(t => t is not null))
                texture.MarkUsed(4096);
        await Task.Delay(33, cancellationToken);
    }
    var shots = new (string name, Vector3 eye, Vector3 target)[] { %SHOTS% };
    for (var pass = 0; pass < 2; pass++)
    {
        foreach (var shot in shots)
        {
            cancellationToken.ThrowIfCancellationRequested();
            using var bitmap = new Bitmap(1600, 900);
            for (var f = 0; f < 10; f++)
            {
                using (scene.Push())
                {
                    camera.WorldPosition = shot.eye;
                    camera.WorldRotation = Rotation.LookAt(shot.target - shot.eye);
                    camera.FieldOfView = 70;
                    scene.EditorTick(.016f, .016f);
                    preRender.Invoke(scene, null);
                    preCameraRender.Invoke(scene, null);
                    camera.RenderToBitmap(bitmap);
                }
                await Task.Delay(16, cancellationToken);
            }
            if (pass == 1) System.IO.File.WriteAllBytes(System.IO.Path.Combine(destination, shot.name + ".png"), bitmap.ToPng());
        }
    }
    var boards = scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath?.Contains("notice_board_v2") == true).ToArray();
    return new { Boards = boards.Length, Errors = boards.Count(r => r.Model.IsError), Positions = boards.Select(r => r.WorldPosition.ToString()).ToArray() };
}
finally { scene.Destroy(); }
'''
code = TEMPLATE.replace("%OUT%", OUT).replace("%SHOTS%", ", ".join(f'("{n}", {v(e)}, {v(t)})' for n, e, t in shots))
path = os.path.join(FULL, "check_installed.cs")
with open(path, "w", encoding="utf-8") as h:
    h.write(code)
print(" ".join(call("run_csharp", {"path": path})[:500].split()), flush=True)

W, H = 800, 450
rows = (len(shots) + 1) // 2
sheet = Image.new("RGB", (W * 2, H * rows), (15, 15, 15))
for k, shot in enumerate(shots):
    p = os.path.join(FULL, shot[0] + ".png")
    if os.path.exists(p):
        sheet.paste(Image.open(p).convert("RGB").resize((W, H), Image.LANCZOS), ((k % 2) * W, (k // 2) * H))
sheet.save(os.path.join(FULL, "installed_all.png"))

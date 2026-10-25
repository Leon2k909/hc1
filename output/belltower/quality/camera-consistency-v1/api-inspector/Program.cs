using Mono.Cecil;
using System.Text.Json;
using System.Security.Cryptography;

var engine = args.Single();
IEnumerable<TypeDefinition> Flatten(TypeDefinition type) => new[] { type }.Concat(type.NestedTypes.SelectMany(Flatten));
var results = new List<object>();
var inventories = new List<object>();
var assemblies = new List<object>();
foreach (var file in new[] { "Sandbox.Engine.dll", "Sandbox.Tools.dll" })
{
    var path = Path.Combine(engine, "bin/managed", file);
    using var assembly = AssemblyDefinition.ReadAssembly(path);
    assemblies.Add(new { File = file, Sha256 = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(path))) });
    var types = assembly.MainModule.Types.SelectMany(Flatten).ToArray();
    foreach (var type in types)
    {
        bool cameraType = type.FullName is "Sandbox.Scene" or "Sandbox.CameraComponent" or "Sandbox.PostProcessSystem"
            || type.FullName.Contains("SceneViewportWidget");
        if (cameraType)
            inventories.Add(new { File = file, Type = type.FullName, Methods = type.Methods.Select(m => m.FullName).ToArray() });
        foreach (var method in type.Methods)
        {
            bool selected = type.FullName == "Sandbox.Scene" && new[] { "get_Camera", "set_Camera", "UpdateMainCamera", "PreCameraRender" }.Contains(method.Name)
                || type.FullName.StartsWith("Sandbox.Scene/") && method.Name.StartsWith("<UpdateMainCamera>")
                || type.FullName == "Sandbox.CameraComponent" && new[] { "get_IsMainCamera", "set_IsMainCamera", "RenderToBitmap", "InitializeRendering", "UpdateSceneCamera", "CopyPostProcessing" }.Contains(method.Name)
                || type.FullName == "Sandbox.PostProcessSystem" && method.Name == "UpdateCamera"
                || type.FullName.Contains("SceneViewportWidget") && method.HasBody && method.Body.Instructions.Any(i => i.Operand is MethodReference reference && (reference.Name.Contains("PostProcess") || reference.Name == "get_Camera"));
            if (selected)
                results.Add(new { File = file, Method = method.FullName, method.IsPublic, method.IsAssembly, Instructions = method.HasBody ? method.Body.Instructions.Select(i => i.ToString()).ToArray() : Array.Empty<string>() });
        }
    }
}
var text = JsonSerializer.Serialize(new { engine, assemblies, inventories, results }, new JsonSerializerOptions { WriteIndented = true });
File.WriteAllText(Path.Combine(Environment.CurrentDirectory, "output/belltower/quality/camera-consistency-v1/engine-api.json"), text);
Console.WriteLine($"Recorded {results.Count} methods from {assemblies.Count} installed assemblies.");

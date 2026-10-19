using Mono.Cecil;
using Mono.Cecil.Cil;
using System.Text.Json;

var engine = @"D:\SteamLibrary\steamapps\common\sbox\bin\managed";
using var assembly = AssemblyDefinition.ReadAssembly(Path.Combine(engine, "Sandbox.Tools.dll"));
IEnumerable<TypeDefinition> Flatten(TypeDefinition type) => new[] { type }.Concat(type.NestedTypes.SelectMany(Flatten));
var types = assembly.MainModule.Types.SelectMany(Flatten).ToArray();
var session = types.Single(t => t.FullName == "Editor.SceneEditorSession");
object Describe(MethodDefinition method) => new {
    Method = method.FullName, method.IsStatic, method.IsPublic,
    Calls = method.HasBody ? method.Body.Instructions.Where(i => i.OpCode.Code is Code.Call or Code.Callvirt or Code.Newobj)
        .Select(i => i.Operand.ToString()).ToArray() : Array.Empty<string>()
};
var methods = session.Methods.Where(m => m.Name is "CreateFromPath" or ".ctor" or "CreateSceneDock" or "Dispose" or "Close" or "MakeActive").Select(Describe).ToArray();
var open = types.Where(t => t.FullName.Contains("Mcp")).SelectMany(t => t.Methods).Where(m => m.Name == "OpenScene").Select(Describe).ToArray();
var tabs = types.Where(t => t.FullName == "Editor.SceneTabWidget").SelectMany(t => t.Methods).Where(m => m.Name == "Open").Select(Describe).ToArray();
Console.WriteLine(JsonSerializer.Serialize(new { methods, open, tabs }, new JsonSerializerOptions { WriteIndented = true }));

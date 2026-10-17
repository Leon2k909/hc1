"""Type-check Riverdale's lighting editor scripts against the installed engine; never runs them.

    python Sources/Riverdale/lighting/check-scripts.py [--out DIR]

Each Sources/Riverdale/editor/*.cs.txt below is compiled as the body of the async method run_csharp wraps it in
(Belltower's check-native-script-types.py: string exchangeDirectory, CancellationToken cancellationToken, the engine's
global usings) with the .NET 10 reference pack and every managed engine assembly ($FACEPUNCH_ENGINE/bin/managed).
The scripts also reach internal engine members by reflection (the serial relocation, the cubemapper, the camera's
view), which a compile can't see, so a second pass reads Sandbox.Engine.dll's metadata (System.Reflection.Metadata,
nothing is loaded or run) and checks that each one is there with the parameter count the scripts pass (REFLECTED).
A pass proves the names and types exist in this build, not that the scripts behave: that needs the editor.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCRIPTS = ("prepare-lighting.cs.txt", "bake-lighting.cs.txt", "capture-reflections.cs.txt",
           "import-reflections.cs.txt", "apply-reflections.cs.txt")

# What the scripts find by reflection: ( type, kind, name, parameter count or None ). Nested types use '+'.
REFLECTED = [
    ("Sandbox.IndirectLightVolume", "property", "Probes", None),
    ("Sandbox.IndirectLightVolume", "property", "GeneratedRelocationTexture", None),
    ("Sandbox.IndirectLightVolume", "property", "InsideGeometry", None),
    ("Sandbox.IndirectLightVolume", "field", "_bakePreview", None),
    ("Sandbox.IndirectLightVolume", "method", "MarkDirty", 0),
    ("Sandbox.IndirectLightVolume", "method", "ComputeSpacing", 1),
    ("Sandbox.IndirectLightVolume", "method", "GenerateSphericalDirections", 1),
    ("Sandbox.IndirectLightVolume", "method", "TraceProbeRays", 3),
    ("Sandbox.IndirectLightVolume", "method", "ComputeRelocationOffset", 6),
    ("Sandbox.IndirectLightVolume", "method", "GetProbeWorldPosition", 1),
    ("Sandbox.IndirectLightVolume", "method", "UpdateRelocationTexture", 0),
    ("Sandbox.IndirectLightVolume+ProbeTraceResult", "property", "BackfaceRatio", None),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "method", ".ctor", 1),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "method", "RunAsync", 1),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "method", "Dispose", 0),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "property", "GeneratedIrradianceTexture", None),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "property", "GeneratedDistanceTexture", None),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "field", "_pass", None),
    ("Sandbox.DDGIProbeUpdaterCubemapper", "field", "_renderedIndex", None),
    ("Sandbox.DDGIVolumeSystem", "method", "MarkDirty", 0),
    ("Sandbox.DDGIVolumeSystem", "method", "UpdateVolumes", 0),
    ("Sandbox.Scene", "method", "PreRender", 0),
    ("Sandbox.Scene", "method", "PreCameraRender", 0),
    ("Sandbox.Scene", "method", "GetSystem", 0),
    ("Sandbox.PostProcessSystem", "method", "UpdateCamera", 1),
    ("Sandbox.CameraComponent", "method", "ComposeView", 0),
    ("Sandbox.EnvmapProbe", "property", "Projection", None),
    ("Sandbox.EnvmapProbe", "property", "Mode", None),
    ("Sandbox.EnvmapProbe", "property", "Texture", None),
]

MEMBER_CHECK = r'''
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Text.Json;

public static class MemberCheck
{
    public static int Main(string[] args)
    {
        using var stream = File.OpenRead(args[0]);
        using var pe = new PEReader(stream);
        var md = pe.GetMetadataReader();
        string Name(TypeDefinition t)
        {
            var own = md.GetString(t.Name);
            var declaring = t.GetDeclaringType();
            if(!declaring.IsNil) return Name(md.GetTypeDefinition(declaring))+"+"+own;
            var ns = md.GetString(t.Namespace);
            return ns.Length>0 ? ns+"."+own : own;
        }
        var types = new Dictionary<string,TypeDefinition>();
        foreach(var handle in md.TypeDefinitions) types[Name(md.GetTypeDefinition(handle))] = md.GetTypeDefinition(handle);
        var spec = JsonSerializer.Deserialize<List<object[]>>(File.ReadAllText(args[1]));
        var results = new List<object>();
        var missing = 0;
        foreach(var row in spec)
        {
            var typeName = row[0].ToString(); var kind = row[1].ToString(); var member = row[2].ToString();
            int? count = row[3] is JsonElement e && e.ValueKind==JsonValueKind.Number ? e.GetInt32() : null;
            var found = new List<string>();
            if(types.TryGetValue(typeName,out var type))
            {
                if(kind=="property")
                    foreach(var h in type.GetProperties()) { var p = md.GetPropertyDefinition(h); if(md.GetString(p.Name)==member) found.Add("property"); }
                if(kind=="field")
                    foreach(var h in type.GetFields()) { var f = md.GetFieldDefinition(h); if(md.GetString(f.Name)==member) found.Add("field"); }
                if(kind=="method")
                    foreach(var h in type.GetMethods())
                    {
                        var m = md.GetMethodDefinition(h);
                        if(md.GetString(m.Name)!=member) continue;
                        var parameters = m.GetParameters().Select(md.GetParameter).Count(p => p.SequenceNumber>0);
                        var blob = md.GetBlobReader(m.Signature);
                        var header = blob.ReadSignatureHeader();
                        if(header.IsGeneric) blob.ReadCompressedInteger();
                        var declared = blob.ReadCompressedInteger();
                        found.Add($"{declared} parameter(s), {m.Attributes}");
                        if(count is null || declared==count) found.Add("match");
                    }
            }
            var ok = types.ContainsKey(typeName) && (kind=="method" ? found.Contains("match") : found.Count>0);
            if(!ok) missing++;
            results.Add(new { Type=typeName, Kind=kind, Member=member, Parameters=count, Found=ok, Detail=found.Where(x => x!="match").ToArray() });
        }
        Console.WriteLine(JsonSerializer.Serialize(new { Assembly=Path.GetFileName(args[0]), Missing=missing, Members=results }, new JsonSerializerOptions{ WriteIndented=true }));
        return missing==0 ? 0 : 2;
    }
}
'''


def engine_path():
    value = os.environ.get("FACEPUNCH_ENGINE")
    if not value:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
            value = winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0]
    return Path(value)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(ROOT / "output/riverdale/aaa/lighting/native-script-types"))
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    managed = engine_path() / "bin/managed"
    dotnet = Path(shutil.which("dotnet"))
    listing = subprocess.run([str(dotnet), "--list-sdks"], capture_output=True, text=True, check=True).stdout
    sdks = [(version, Path(folder) / version) for version, folder in re.findall(r"^(10\.[^ ]+) \[([^\]]+)\]", listing, re.M)]
    assert sdks, "A .NET 10 SDK is required by the installed engine."
    sdk_version, sdk = max(sdks, key=lambda item: tuple(map(int, re.findall(r"\d+", item[0]))))
    packs = list((dotnet.parent / "packs/Microsoft.NETCore.App.Ref").glob("10.*/ref/net10.0"))
    assert packs, "No .NET 10 reference pack."
    reference_pack = max(packs, key=lambda path: tuple(map(int, path.parts[-3].split("."))))
    references = list(reference_pack.glob("*.dll"))
    references += [path for path in managed.glob("*.dll")
                   if not path.name.startswith(("System.", "Microsoft.Win32.")) and path.name not in ("mscorlib.dll", "netstandard.dll")]
    references = sorted(set(references))
    scripts = [ROOT / "Sources/Riverdale/editor" / name for name in SCRIPTS]
    source = ("using System;\nusing System.Linq;\nusing System.Threading;\nusing System.Threading.Tasks;\nusing Sandbox;\n"
              "using static Sandbox.Internal.GlobalGameNamespace;\nusing static Sandbox.Internal.GlobalToolsNamespace;\n")
    for index, path in enumerate(scripts):
        source += f"public static class RiverdaleScript{index}\n{{\n"
        source += "public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)\n{\n"
        source += f'#line 1 "{path.as_posix()}"\n' + path.read_text(encoding="utf-8")
        source += "\n#line default\n}\n}\n"
    wrapper = out / "ScriptBodies.cs"
    wrapper.write_text(source, encoding="utf-8")
    response = out / "compile.rsp"
    arguments = ["/nologo", "/target:library", "/langversion:14", "/nullable:disable", "/nostdlib+", "/parallel-",
                 "/deterministic", '/out:"' + str(out / "ScriptBodies.dll") + '"', '"' + str(wrapper) + '"']
    arguments += ['/reference:"' + str(path) + '"' for path in references]
    response.write_text("\n".join(arguments) + "\n", encoding="utf-8")
    result = subprocess.run([str(dotnet), str(sdk / "Roslyn/bincore/csc.dll"), "@" + str(response)],
                            cwd=ROOT, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (out / "compiler.log").write_text(log, encoding="utf-8")

    # The reflected members, from the engine assembly's metadata.
    checker = out / "MemberCheck.cs"
    checker.write_text(MEMBER_CHECK, encoding="utf-8")
    pack_refs = sorted(reference_pack.glob("*.dll"))
    member_rsp = out / "member-check.rsp"
    member_rsp.write_text("\n".join(["/nologo", "/target:exe", "/langversion:14", "/nostdlib+", "/nullable:disable",
                                     '/out:"' + str(out / "MemberCheck.dll") + '"', '"' + str(checker) + '"']
                                    + ['/reference:"' + str(p) + '"' for p in pack_refs]) + "\n", encoding="utf-8")
    built = subprocess.run([str(dotnet), str(sdk / "Roslyn/bincore/csc.dll"), "@" + str(member_rsp)], cwd=ROOT,
                           capture_output=True, text=True)
    (out / "MemberCheck.runtimeconfig.json").write_text(json.dumps({"runtimeOptions": {
        "tfm": "net10.0", "rollForward": "LatestPatch",
        "framework": {"name": "Microsoft.NETCore.App", "version": "10.0.0"}}}), encoding="utf-8")
    spec = out / "reflected.json"
    spec.write_text(json.dumps([list(row) for row in REFLECTED]), encoding="utf-8")
    members = {"state": "not built", "build_log": (built.stdout + built.stderr).splitlines()}
    if built.returncode == 0:
        ran = subprocess.run([str(dotnet), str(out / "MemberCheck.dll"), str(managed / "Sandbox.Engine.dll"), str(spec)],
                             cwd=ROOT, capture_output=True, text=True)
        try:
            members = json.loads(ran.stdout)
            members["state"] = "all reflected members found" if ran.returncode == 0 else "reflected members missing"
        except json.JSONDecodeError:
            members = {"state": "member check failed", "log": (ran.stdout + ran.stderr).splitlines()}
    passed = result.returncode == 0 and members.get("state") == "all reflected members found"
    report = {"state": "type check passed" if result.returncode == 0 else "type check failed",
              "reflection": members.get("state"), "passed": passed, "executed": False,
              "native_validation_required": True, "sdk": sdk_version, "reference_pack": str(reference_pack),
              "engine_managed": str(managed), "references": len(references),
              "scripts": {path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest() for path in scripts},
              "exit_code": result.returncode, "diagnostics": log.splitlines(), "reflected_members": members}
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "reflected_members"}, indent=2), flush=True)
    missing = [m for m in members.get("Members", []) if not m["Found"]]
    for m in missing:
        print(f"missing: {m['Type']} {m['Kind']} {m['Member']} ({m['Parameters']}) {m['Detail']}")
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()

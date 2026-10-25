"""Compile the pending preview diagnostic against the installed engine, offline."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Sources/Belltower/editor/capture-preview-consistent.cs.txt"
OUTPUT = ROOT / "output/belltower/quality/camera-consistency-v1"
ASSEMBLIES = (
    "Sandbox.System", "Sandbox.Engine", "Sandbox.Filesystem",
    "Sandbox.Reflection", "Sandbox.Mounting", "Sandbox.Tools",
)


def engine_root() -> Path:
    candidates = [os.environ.get("FACEPUNCH_ENGINE")]
    if os.name == "nt":
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment") as key:
                candidates.append(winreg.QueryValueEx(key, "FACEPUNCH_ENGINE")[0])
        except FileNotFoundError:
            pass
    for candidate in candidates:
        if candidate and (Path(candidate) / "bin/managed/Sandbox.Engine.dll").is_file():
            return Path(candidate).resolve()
    raise RuntimeError("Resolve the installed engine through FACEPUNCH_ENGINE first.")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    engine = engine_root()
    folder = OUTPUT / "helper-compile"
    folder.mkdir(parents=True, exist_ok=True)
    wrapped = (
        "using System;\nusing System.Linq;\nusing System.Threading;\n"
        "using System.Threading.Tasks;\nusing Sandbox;\n"
        "public static class BelltowerPreviewCapture {\n"
        "public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken) {\n"
        + SOURCE.read_text(encoding="utf-8") + "\n}\n}\n"
    )
    (folder / "CaptureScript.cs").write_text(wrapped, encoding="utf-8")
    project = ET.Element("Project", Sdk="Microsoft.NET.Sdk")
    group = ET.SubElement(project, "PropertyGroup")
    for key, value in {
        "TargetFramework": "net10.0", "OutputType": "Library", "ImplicitUsings": "disable",
        "Nullable": "disable", "EnableDefaultItems": "false", "UseSharedCompilation": "false",
        "GenerateAssemblyInfo": "false", "CopyLocalLockFileAssemblies": "false",
    }.items():
        ET.SubElement(group, key).text = value
    items = ET.SubElement(project, "ItemGroup")
    for assembly in ASSEMBLIES:
        reference = ET.SubElement(items, "Reference", Include=assembly)
        ET.SubElement(reference, "HintPath").text = f"$(EnginePath)/bin/managed/{assembly}.dll"
        ET.SubElement(reference, "Private").text = "false"
    ET.SubElement(items, "Compile", Include="CaptureScript.cs")
    project_path = folder / "CaptureScript.csproj"
    ET.ElementTree(project).write(project_path, encoding="utf-8", xml_declaration=True)
    env = os.environ.copy()
    env["MSBUILDDISABLENODEREUSE"] = "1"
    command = [
        "dotnet", "build", str(project_path), "--disable-build-servers", "-m:1",
        "-p:UseSharedCompilation=false", "-p:BuildInParallel=false", f"-p:EnginePath={engine}",
    ]
    result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    (folder / "build.log").write_text(result.stdout + result.stderr, encoding="utf-8")
    report = {
        "status": "offline-api-compile-passed-native-validation-pending" if result.returncode == 0 else "offline-api-compile-failed",
        "exit_code": result.returncode,
        "source": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": sha256(SOURCE),
        "engine": str(engine),
        "engine_assembly_sha256": {name: sha256(engine / f"bin/managed/{name}.dll") for name in ASSEMBLIES},
        "native_capture_run": False,
        "scene_mutations_performed_by_this_tool": False,
        "scope": "API binding only; pixel consistency, effective exposure and restoration require a native run.",
    }
    (OUTPUT / "helper-static-compile.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if result.returncode:
        print((result.stdout + result.stderr)[-6000:])
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

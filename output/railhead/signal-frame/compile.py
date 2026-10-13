"""Compile with the stock compiler's core mount, then remove the temporary copies."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[3]
SDK = Path("D:/SteamLibrary/steamapps/common/sbox")
CORE = SDK / "core"
paths = ("models/props/railhead/signal_frame", "materials/railhead/signal_frame")
destinations = [CORE / p for p in paths]
assert all(not p.exists() for p in destinations), "Never replace an existing SDK asset."
created = []
try:
    for relative, destination in zip(paths, destinations):
        destination.mkdir(parents=True)
        created.append(destination)
        for p in (ROOT / "Assets" / relative).iterdir():
            if p.suffix in (".vmdl", ".obj", ".mtl", ".vmat", ".png"):
                shutil.copy2(p, destination / p.name)
    inputs = sorted(destinations[1].glob("*.vmat")) + [destinations[0] / "signal_frame.vmdl"]
    filelist = Path(__file__).parent / "compile_inputs.txt"
    filelist.write_text("\n".join(p.as_posix() for p in inputs))
    command = ["rtk", "proxy", str(SDK / "bin/win64/resourcecompiler.exe"), "-filelist", str(filelist)]
    result = subprocess.run(command, cwd=SDK, capture_output=True, text=True, errors="replace", timeout=120)
    log = result.stdout + result.stderr
    (Path(__file__).parent / "compile.log").write_text(log)
    print(log[-6500:])
    print("Compiler exit:", result.returncode)
    import json
    report = {"exit_code": result.returncode, "assets": {p.name: p.with_name(p.name + "_c").exists() for p in inputs}}
    (Path(__file__).parent / "compile.json").write_text(json.dumps(report, indent=2))
    assert result.returncode == 0 and all(report["assets"].values()), report
finally:
    for destination in reversed(created):
        resolved = destination.resolve()
        assert resolved.is_relative_to(CORE.resolve()) and resolved.name == "signal_frame"
        shutil.rmtree(resolved)

"""Compile only the staged reflection component against local engine assemblies."""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[4]
manifest = json.loads((OUT/'manifest.json').read_text())
assert Path(manifest['project_root']).resolve() == ROOT


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def unchanged():
    assert all(sha(ROOT/p) == h for p, h in manifest['sources'].items())
    assert all(sha(OUT/'stage'/p) == h for p, h in manifest['staged_files'].items())


unchanged()
env = os.environ.copy()
env.update(DOTNET_CLI_UI_LANGUAGE='en-US', DOTNET_CLI_TELEMETRY_OPTOUT='1')
command = ['rtk', 'proxy', 'dotnet', 'build', str(OUT/'compile/WaterCheck.csproj'),
           '--nologo', '--disable-build-servers', '-v:minimal']
result = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
log = result.stdout + result.stderr
(OUT/'compile/build-output.txt').write_text(log, encoding='utf-8')
if result.returncode:
    print(log[-12000:])
    sys.exit(result.returncode)
assert 'Build succeeded.' in log
warnings = re.findall(r'(\d+) Warning\(s\)', log)
errors = re.findall(r'(\d+) Error\(s\)', log)
assert warnings and errors and int(warnings[-1]) == int(errors[-1]) == 0, log
sdk_result = subprocess.run(['rtk', 'proxy', 'dotnet', '--version'], cwd=ROOT, env=env,
                            capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
sdk = re.findall(r'^\d+\.\d+\.\d+[^\r\n]*$', sdk_result.stdout, re.M)[-1]
references = [Path(node.text) for node in ET.parse(OUT/'compile/WaterCheck.csproj').findall('.//HintPath')]
unchanged()
files = ['compile/WaterCheck.csproj', 'compile/NuGet.Config', 'compile/build-output.txt',
         'compile/bin/Debug/net10.0/LowtideWaterOfflineCheck.dll']
report = dict(status='isolated_csharp_api_compile_passed', project_root=str(ROOT),
              manifest_sha256=sha(OUT/'manifest.json'), source='Code/Map/LowtideWaterReflections.cs',
              source_sha256=sha(OUT/'stage/Code/Map/LowtideWaterReflections.cs'),
              files={p:sha(OUT/p) for p in files}, sdk=sdk,
              reference_files={p.as_posix():sha(p) for p in references}, warnings=0, errors=0,
              loaded_into_engine=False, shader_compiled=False,
              limitations=['Isolated net10.0 API compilation only; no sandbox analyzers or source generators',
                           'No native shader compilation, hotload, GPU rendering, lifecycle or performance verification'])
(OUT/'compile-verification.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('files', 'reference_files')}, indent=2))

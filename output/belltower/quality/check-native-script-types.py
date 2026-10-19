"""Type-check editor method bodies against installed assemblies; never execute them."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import winreg

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT/'output/belltower/quality/native-script-types'
OUT.mkdir(exist_ok=True)
engine_value = os.environ.get('FACEPUNCH_ENGINE')
if not engine_value:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        engine_value = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
engine = Path(engine_value)
managed = engine/'bin/managed'
dotnet = Path(shutil.which('dotnet'))
sdk_output = subprocess.run([str(dotnet), '--list-sdks'], capture_output=True, text=True, check=True).stdout
sdks = [(version, Path(folder)/version) for version, folder in re.findall(r'^(10\.[^ ]+) \[([^\]]+)\]', sdk_output, re.M)]
assert sdks, 'A .NET 10 SDK is required by the installed engine.'
sdk_version, sdk = max(sdks, key=lambda item:tuple(map(int, re.findall(r'\d+', item[0]))))
packs = list((dotnet.parent/'packs/Microsoft.NETCore.App.Ref').glob('10.*/ref/net10.0'))
assert packs
reference_pack = max(packs, key=lambda path:tuple(map(int, path.parts[-3].split('.'))))
references = list(reference_pack.glob('*.dll'))
references.extend(path for path in managed.glob('*.dll')
                  if not path.name.startswith(('System.', 'Microsoft.Win32.'))
                  and path.name not in ('mscorlib.dll', 'netstandard.dll'))
references = sorted(set(references))

scripts = [ROOT/'Sources/Belltower/editor'/name for name in (
    'capture-viewport.cs.txt', 'inspect-capture-cameras.cs.txt',
    'import-canopy-trial.cs.txt', 'verify-canopy-trial.cs.txt',
    'import-gardens.cs.txt', 'verify-gardens.cs.txt',
    'import-farfield-v3.cs.txt',
)]
source = '''using System;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using Sandbox;
using static Sandbox.Internal.GlobalGameNamespace;
using static Sandbox.Internal.GlobalToolsNamespace;
'''
for index, path in enumerate(scripts):
    source += f'public static class BelltowerScript{index}\n{{\n'
    source += 'public static async Task<object> Run(string exchangeDirectory, CancellationToken cancellationToken)\n{\n'
    source += f'#line 1 "{path.as_posix()}"\n'+path.read_text(encoding='utf-8')
    source += '\n#line default\n}\n}\n'
wrapper = OUT/'ScriptBodies.cs'
wrapper.write_text(source, encoding='utf-8')
response = OUT/'compile.rsp'
arguments = ['/nologo', '/target:library', '/langversion:14', '/nullable:disable',
             '/nostdlib+', '/parallel-', '/deterministic',
             '/out:"'+str(OUT/'ScriptBodies.dll')+'"', '"'+str(wrapper)+'"']
arguments += ['/reference:"'+str(path)+'"' for path in references]
response.write_text('\n'.join(arguments)+'\n', encoding='utf-8')
result = subprocess.run([str(dotnet), str(sdk/'Roslyn/bincore/csc.dll'), '@'+str(response)],
                        cwd=ROOT, capture_output=True, text=True)
log = result.stdout+result.stderr
(OUT/'compiler.log').write_text(log, encoding='utf-8')
report = {'state':'type check passed' if result.returncode == 0 else 'type check failed',
          'executed':False, 'native_validation_required':True,
          'sdk':sdk_version, 'reference_pack':str(reference_pack), 'references':len(references),
          'scripts':{path.relative_to(ROOT).as_posix():hashlib.sha256(path.read_bytes()).hexdigest() for path in scripts},
          'exit_code':result.returncode, 'diagnostics':log.splitlines()}
(OUT/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
print(json.dumps(report, indent=2), flush=True)
raise SystemExit(result.returncode)

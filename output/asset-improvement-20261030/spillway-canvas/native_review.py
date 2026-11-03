import json
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
ENGINE = os.environ.get('FACEPUNCH_ENGINE')
if not ENGINE:
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, 'Environment') as key:
        ENGINE = winreg.QueryValueEx(key, 'FACEPUNCH_ENGINE')[0]
CLI = Path(ENGINE) / 'bin/managed/sbox-cli.exe'
p = subprocess.Popen([str(CLI), '--connect'], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
counter = 0

def request(method, params):
    global counter
    counter += 1
    p.stdin.write(json.dumps(dict(jsonrpc='2.0', id=counter, method=method, params=params)) + '\n')
    p.stdin.flush()
    while True:
        line = p.stdout.readline()
        if not line:
            raise RuntimeError(p.stderr.read())
        message = json.loads(line)
        if message.get('id') == counter:
            if 'error' in message:
                raise RuntimeError(message['error'])
            return message['result']

def call(name, arguments=None):
    result = request('tools/call', dict(name=name, arguments=arguments or {}))
    for block in result.get('content', []):
        if block.get('type') == 'text':
            print(name + ': ' + block['text'], flush=True)
    if result.get('isError'):
        raise RuntimeError(name + ' failed')
    return result

exchange = None
try:
    init = request('initialize', dict(protocolVersion='2025-11-25', capabilities={}, clientInfo=dict(name='codex-canvas-review', version='1')))
    exchange = Path(init['_meta']['exchangeDirectory'])
    print(json.dumps(init['_meta']), flush=True)
    p.stdin.write(json.dumps(dict(jsonrpc='2.0', method='notifications/initialized')) + '\n')
    p.stdin.flush()
    mode = sys.argv[1]
    if mode == 'discover':
        for query in ('compile_status', 'read_console', 'scene_find'):
            call('search_tools', dict(query=query))
    elif mode == 'cleanup_schema':
        result = request('tools/call', dict(name='search_tools', arguments=dict(query='delete')))
        for block in result.get('content', []):
            if block.get('type') == 'text':
                catalog = json.loads(block['text'])
                for tool in catalog['tools']:
                    if 'asset' in tool['name']:
                        print(json.dumps(tool, indent=2))
        call('read_console', dict(minimumLevel='Error', limit=5))
        call('compile_status')
    elif mode == 'cleanup':
        script = exchange / 'archive_comparison.cs'
        script.write_text('''var project = Sandbox.Project.Current.GetRootPath();
var source = System.IO.Path.Combine(project, "Assets/models/compare_old");
var archive = System.IO.Path.Combine(project, "output/asset-improvement-20261030/spillway-canvas/retired/comparison_sources");
System.IO.Directory.CreateDirectory(archive);
var removed = new System.Collections.Generic.List<string>();
foreach (var stem in new[] { "spillway_canvas_old", "spillway_east_dark_rest" })
    foreach (var suffix in new[] { ".mtl", ".obj", ".obj.meta", ".vmdl", ".vmdl.meta", ".vmdl_c" })
    {
        var name = stem + suffix;
        var path = System.IO.Path.Combine(source, name);
        if (!System.IO.File.Exists(path)) continue;
        System.IO.File.Copy(path, System.IO.Path.Combine(archive, name), false);
        System.IO.File.Delete(path);
        removed.Add(name);
    }
return new { ArchivedAndRemoved = removed, SharedHiddenMaterialKept = true };''', encoding='utf-8')
        call('run_csharp', dict(path=str(script)))
        call('read_console', dict(minimumLevel='Error', since=10604, limit=5))
        call('editor_status')
    elif mode == 'validate':
        source = ROOT / 'Sources/Spillway/canvas-cover-v2'
        sys.path.insert(0, str(source))
        # Importing check_install would run it; fill its template directly instead.
        cameras = {
            'north': ((1600, -1440, 194), (1550, -1705, 168), 55),
            'northeast': ((1800, -1560, 200), (1550, -1705, 160), 55),
            'east_low': ((1770, -1720, 160), (1550, -1705, 170), 60),
            'far': ((1720, -1180, 200), (1550, -1705, 170), 40),
        }
        def pos(v):
            e, n, z = v
            return f'new Vector3({n}f, {-e}f, {z}f)'
        shots = ', '.join(f'("installed_{name}", {pos(eye)}, {pos(target)}, {fov}f)' for name, (eye, target, fov) in cameras.items())
        code = (source / 'check_install.cs.txt').read_text(encoding='utf-8')
        code = code.replace('%OUT%', 'output/asset-improvement-20261030/spillway-canvas/installed').replace('%SHOTS%', shots).replace('%HIDE%', 'false').replace('%PLACE%', '')
        script = exchange / 'check_install.cs'
        script.write_text(code, encoding='utf-8')
        result = call('run_csharp', dict(path=str(script)))
        (Path(__file__).parent / 'installed' / 'native-validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        script = exchange / 'live_cover.cs'
        script.write_text('''var scene = Editor.SceneEditorSession.Active.Scene;
return scene.GetAllComponents<ModelRenderer>().Where(r => r.Model?.ResourcePath == "models/maps/spillway/canvas_cover_v2/canvas_cover.vmdl").Select(r => new { r.GameObject.Name, r.GameObject.WorldPosition, Error = r.Model.IsError, Collider = r.GameObject.Components.Get<ModelCollider>() is not null }).ToArray();''', encoding='utf-8')
        call('run_csharp', dict(path=str(script)))
    elif mode == 'call':
        call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else {})
finally:
    p.stdin.close()
    p.wait(timeout=20)
    diagnostics = p.stderr.read()
    if diagnostics:
        print(diagnostics, file=sys.stderr)
    if exchange and exchange.is_dir():
        import shutil
        shutil.rmtree(exchange)

"""Prepare project-local source and isolated comparison views, no live asset edits."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
generation = json.loads((SOURCE / 'generation.json').read_text(encoding='utf-8'))
shutil.copy2(generation['original'], SOURCE / 'inland-v1.png')
coastal = SOURCE / 'coastal-generation.json'
if coastal.exists():
    shutil.copy2(json.loads(coastal.read_text(encoding='utf-8'))['original'], SOURCE / 'coastal-v2.png')
script = (ROOT / 'Sources/Veridant/editor/capture.cs.txt').read_text(encoding='utf-8')
script = script.replace('output/veridant/captures', 'output/veridant/inland-vista-v1/captures')
script = script.replace('var source = Editor.SceneEditorSession.Active?.Scene;',
    'var pngFolder = System.IO.Path.Combine(projectRoot, configuration["folder"].GetValue<string>());\n'
    'System.IO.Directory.CreateDirectory(pngFolder);\n'
    'var source = Editor.SceneEditorSession.Active?.Scene;')
script = script.replace('foreach (var probe in scene.GetAllComponents<EnvmapProbe>()) probe.Mode = EnvmapProbe.EnvmapProbeMode.Realtime;',
                        '// Preserve saved probes; no cubemap rendering in the shared editor.')
a = script.index('    var renderProbe =')
b = script.index('    // Plan ( e, n, z )', a)
script = script[:a] + script[b:]
script = script.replace('System.IO.Path.Combine(destination, name + ".png")',
                        'System.IO.Path.Combine(pngFolder, name + ".png")')
(SOURCE / 'capture.cs.txt').write_text(script, encoding='utf-8')
folder = ROOT / 'output/veridant/inland-vista-v1/captures'
folder.mkdir(parents=True, exist_ok=True)
views = [
    {'name': 'east', 'eye': [1000,-600,270], 'target': [6500,-600,1100], 'fov': 80},
    {'name': 'north', 'eye': [220,1350,280], 'target': [4500,6500,1400], 'fov': 80},
    {'name': 'south', 'eye': [-1200,-1300,100], 'target': [4500,-6500,1200], 'fov': 80},
    {'name': 'hillside-detail', 'eye': [2400,-100,650], 'target': [6500,-100,1350], 'fov': 80},
    {'name': 'bay-control', 'eye': [-1650,200,100], 'target': [-6000,1200,40], 'fov': 80},
]
config = {'folder': 'output/veridant/inland-vista-v1/before', 'width': 1536, 'height': 864,
          'fixed_exposure': 2.4, 'settle_frames': 10, 'stream_frames': 40, 'views': views}
(folder / 'config.json').write_text(json.dumps(config, indent=2), encoding='utf-8')
print('Prepared original RGBA source, isolated capture script, and five-view config.')

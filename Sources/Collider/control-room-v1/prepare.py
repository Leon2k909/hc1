"""Prepare private references and a scoped native camera review, without touching assets."""
from pathlib import Path
import json
import shutil

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).parent
OUTPUT = ROOT / 'output/collider-control-room-v1-20261027'


def prepare(folder='before'):
    OUTPUT.mkdir(parents=True, exist_ok=True)
    refs = SOURCE / 'references'
    refs.mkdir(exist_ok=True)
    generated = Path('C:/Users/leon2/.codex/generated_images/01a17e51-cbc1-70c0-95e2-5b838efdc22e')
    for name, original in (
        ('operator-chair.png', 'exec-70f40fd0-2403-49a3-8134-e73204cc217d.png'),
        ('control-room.png', 'exec-5d5770f7-5024-4319-b9b5-35c575095aee.png'),
    ):
        if not (refs / name).exists():
            shutil.copyfile(generated / original, refs / name)
    config = dict(width=1600, height=1000, supersample=2, folder=folder, views=[
        dict(name='east-row', eye=[1625, -210, 344], target=[1815, 100, 303], fov=78),
        dict(name='west-row', eye=[-1625, -210, 344], target=[-1815, 100, 303], fov=78),
        dict(name='chair-close', eye=[1730, -130, 312], target=[1789, -55, 281], fov=61),
        dict(name='console-close', eye=[1770, -115, 326], target=[1840, -55, 299], fov=65),
    ])
    (OUTPUT / 'capture-config.json').write_text(json.dumps(config, indent=2) + '\n')
    script = (ROOT / 'Sources/Collider/editor/capture.cs.txt').read_text()
    script = script.replace('output/collider', 'output/collider-control-room-v1-20261027')
    # Also fingerprint this revision's material sources once installed.
    script = script.replace('var inputHashes=inputFiles.ToDictionary', '''
var operatorMaterials=System.IO.Path.Combine(root,"Assets/materials/collider/control-room-v1");
if(System.IO.Directory.Exists(operatorMaterials))
    inputFiles=inputFiles.Concat(System.IO.Directory.EnumerateFiles(operatorMaterials)
        .Where(p=>p.EndsWith(".png")||p.EndsWith(".vmat"))
        .Select(p=>System.IO.Path.GetRelativePath(System.IO.Path.Combine(root,"Assets"),p).Replace('\\\\','/'))).OrderBy(p=>p).ToArray();
var inputHashes=inputFiles.ToDictionary''')
    (SOURCE / 'capture.cs.txt').write_text(script)
    print(json.dumps(dict(folder=folder, views=len(config['views']), output=str(OUTPUT))))


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--folder', default='before')
    prepare(parser.parse_args().folder)

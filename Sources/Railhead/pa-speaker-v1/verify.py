"""Validate the isolated preview and compose the actual play-mode comparison."""
import collections
import hashlib
import json
from PIL import Image, ImageDraw, ImageFont
from native import ROOT, OUT, call

sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
guard = json.loads((OUT/'source-guard.json').read_text())
changed = [p for p, h in guard.items() if sha(ROOT/p) != h]
assert not changed, changed
manifest = json.loads((OUT/'manifest.json').read_text())
assert all(sha(ROOT/p) == h for p, h in manifest['files'].items())
old = (ROOT/manifest['source']).read_text().splitlines()
new = (ROOT/'Assets/models/maps/railhead/pa-speaker-v1/centre_without_speaker.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ', 'vt ', 'vn '))] == [l for l in new if l.startswith(('v ', 'vt ', 'vn '))]
a = collections.Counter(l for l in old if l.startswith('f '))
b = collections.Counter(l for l in new if l.startswith('f '))
assert not b-a and sum((a-b).values()) == manifest['original_triangles'] == 36
original = (ROOT/'Assets/models/maps/railhead/railhead_dress_centre.vmdl').read_text()
preview = (ROOT/'Assets/models/maps/railhead/pa-speaker-v1/centre_without_speaker.vmdl').read_text()
marker = '_class = "PhysicsShapeList"'
assert original[original.index(marker):] == preview[preview.index(marker):]
assert preview.replace('models/maps/railhead/pa-speaker-v1/centre_without_speaker.obj','models/maps/railhead/clock-v1/dressing_without_clock.obj') == original
folder = OUT/'runtime-review'
capture = json.loads((folder/'checked.json').read_text())
camera = json.loads((folder/'camera.json').read_text())
assert {'PhotographicResponse', 'Tonemapping'} <= set(camera['Effects'])
assert capture['ActualPlayMode'] and capture['ActiveRuntimeMap'] == 'scenes/maps/railhead/railhead.scene'
assert capture['PlayerCount'] > 0 and not capture['ErrorModels']
restored = json.loads((OUT/'play-state-restored.json').read_text())
assert restored['restored']
for field in ('ActiveScenePath', 'IsPlaying', 'SceneHasUnsavedChanges'):
    assert restored['before'][field] == restored['after'][field]
status = call('editor_status')
assert status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0
assert status['ActiveScenePath'] == restored['before']['ActiveScenePath']
assert status['IsPlaying'] == restored['before']['IsPlaying']
font_path = str(ROOT/'Assets/fonts/Dinish-Bold.ttf')
font = ImageFont.truetype(font_path, 38)
small = ImageFont.truetype(font_path, 24)
for name in ('speaker', 'side'):
    imgs = [Image.open(folder/f'{name}-{v}.png').convert('RGB') for v in ('before', 'after')]
    assert imgs[0].size == imgs[1].size
    w, h = imgs[0].size
    sheet = Image.new('RGB', (w*2+24, h+116), (18, 23, 26))
    d = ImageDraw.Draw(sheet)
    for i, (im, title) in enumerate(zip(imgs, ('BEFORE', 'AFTER'))):
        x = i*(w+24)
        sheet.paste(im, (x, 60))
        d.text((x+24, 8), title, font=font, fill=(230, 237, 235))
    d.text((24, h+78), 'RAILHEAD / PA SPEAKER     Actual play mode · matching camera, lighting and exposure', font=small, fill=(171, 190, 187))
    sheet.save(OUT/f'{name}-comparison.png')
report = dict(review_only=True, new_triangles=manifest['triangles'], replaced_triangles=36,
              guarded_original_files=len(guard), original_assets_unchanged=True,
              unrelated_geometry_unchanged=True, physics_unchanged=True,
              actual_play_mode_checked=True, player_present=True, native_error_models=[],
              editor_state_restored=True, forced_texture_residency=False,
              camera=camera, capture=capture, editor_status=status)
(OUT/'validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('camera', 'capture', 'editor_status')}, indent=2))

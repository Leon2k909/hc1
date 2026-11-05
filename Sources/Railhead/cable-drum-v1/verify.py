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
new = (ROOT/'Assets/models/maps/railhead/cable-drum-v1/east_without_drum.obj').read_text().splitlines()
assert [l for l in old if l.startswith(('v ', 'vt ', 'vn '))] == [l for l in new if l.startswith(('v ', 'vt ', 'vn '))]
a = collections.Counter(l for l in old if l.startswith('f '))
b = collections.Counter(l for l in new if l.startswith('f '))
assert not b-a and sum((a-b).values()) == manifest['original_triangles'] == 260
original = (ROOT/'Assets/models/maps/railhead/railhead_dress_east.vmdl').read_text()
preview = (ROOT/'Assets/models/maps/railhead/cable-drum-v1/east_without_drum.vmdl').read_text()
marker = '_class = "PhysicsShapeList"'
assert original[original.index(marker):] == preview[preview.index(marker):]
assert preview.replace('models/maps/railhead/cable-drum-v1/east_without_drum.obj','models/maps/railhead/road-barrier-v1/east_without_barrier.obj') == original
# The texture revision must keep the first proposal's exact shape and normals.
first = (OUT/'first-review/cable_drum.obj').read_text().splitlines()
revised = (ROOT/'Assets/models/maps/railhead/cable-drum-v1/cable_drum.obj').read_text().splitlines()
assert [l for l in first if not l.startswith('vt ')] == [l for l in revised if not l.startswith('vt ')]
for timber in ('timber_a','timber_b','timber_c'):
    assert (ROOT/f'Assets/materials/railhead/cable-drum-v1/{timber}.vmat').read_text() == (ROOT/'Assets/materials/railhead/rw_wood.vmat').read_text()
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
assert not status['IsCompiling'] and status['LastCompileSucceeded'] and status['LastCompileErrors'] == 0
# Use the immediate restoration receipt: another user may change scenes afterward.
assert restored['after']['LastCompileErrors'] == 0
# Play-stop may trigger a build; the current settled compiler state above is authoritative.
if not restored['after']['IsCompiling']: assert restored['after']['LastCompileSucceeded']
font_path = str(ROOT/'Assets/fonts/Dinish-Bold.ttf')
font = ImageFont.truetype(font_path, 32)
small = ImageFont.truetype(font_path, 20)
for name in ('drum',):
    imgs = [Image.open(folder/f'{name}-{v}.png').convert('RGB').crop((300,40,1210,895)) for v in ('before', 'after')]
    assert imgs[0].size == imgs[1].size
    w, h = imgs[0].size
    sheet = Image.new('RGB', (w*2+24, h+116), (18, 23, 26))
    d = ImageDraw.Draw(sheet)
    for i, (im, title) in enumerate(zip(imgs, ('BEFORE', 'AFTER'))):
        x = i*(w+24)
        sheet.paste(im, (x, 60))
        d.text((x+24, 8), title, font=font, fill=(230, 237, 235))
    d.text((24, h+78), 'RAILHEAD / CABLE REEL     Actual play mode · matching camera, lighting and exposure', font=small, fill=(171, 190, 187))
    sheet.save(OUT/f'{name}-comparison.png')
    sheet.save(OUT/f'{name}-original-wood-comparison.png')
report = dict(review_only=True, original_wood_material_restored=True, new_shape_unchanged=True, new_triangles=manifest['triangles'], replaced_triangles=260,
              guarded_original_files=len(guard), original_assets_unchanged=True,
              unrelated_geometry_unchanged=True, physics_unchanged=True,
              actual_play_mode_checked=True, player_present=True, native_error_models=[],
              editor_state_restored=True, forced_texture_residency=False,
              camera=camera, capture=capture, editor_status=status)
(OUT/'validation.json').write_text(json.dumps(report, indent=2))
print(json.dumps({k:v for k,v in report.items() if k not in ('camera', 'capture', 'editor_status')}, indent=2))

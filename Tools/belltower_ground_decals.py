"""Stage native albedo-only decals from the existing ground atlas and placements."""
import copy
import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / 'output/belltower/quality/ground-edge-v2'
GROUND = ROOT / 'output/belltower/quality/ground-edge-v1/manifest.json'
ATLAS = 'materials/belltower/ground-edge-v1/ground_edge.png'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ground = json.loads(GROUND.read_text(encoding='utf-8'))
    checks = json.loads(GROUND.with_name('geometry-checks.json').read_text())
    assert checks['passed'] and checks['manifest_sha256'] == sha(GROUND)
    for path, expected in ground['source_sha256'].items():
        assert sha(ROOT / path) == expected, path
    atlas_sha = sha(ROOT / 'Sources/Belltower/generated/ground-edge-v2.png')
    assert sha(ROOT / 'Assets' / ATLAS) == atlas_sha
    native = json.loads((STAGE / 'native-api.json').read_text())
    assert native['GamePreserved'] and native['SelectedDocumentPreserved']
    assert 'Multiply' in native['DecalBlendModes']
    defaults = json.loads(native['ImageFileGeneratorDefaults'])
    width, height = ground['actual_source_dimensions']
    files, regions = [], []
    for index, region in enumerate(ground['atlas_regions']):
        u0, v0, u1, v1 = region['uv']
        left, top, right, bottom = round(u0 * width), round((1 - v1) * height), round(u1 * width), round((1 - v0) * height)
        assert 0 <= left < right <= width and 0 <= top < bottom <= height
        assert math.isclose((right - left) / (bottom - top), region['aspect'])
        data = copy.deepcopy(defaults)
        data.pop('FormatOverride', None)
        data.update(FilePath=ATLAS, Cropping=dict(Left=left, Top=top, Right=width - right, Bottom=height - bottom))
        definition = dict(
            ColorTexture={'$compiler': 'texture', '$source': 'imagefile', 'data': data, 'compiled': None},
            NormalTexture=None, RoughMetalOcclusionTexture=None, HeightTexture=None, EmissiveTexture=None,
            ParallaxStrength=0, Tint='1,1,1,1', BlendMode='Multiply', ColorMix=1,
            Width=1, Height=1, __references=[], __version=0)
        relative = f'decals/belltower/ground-edge-v2/ground_{index}.decal'
        target = STAGE / 'Assets' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(definition, indent=2) + '\n'
        if target.exists():
            assert target.read_text(encoding='utf-8') == text, 'Use a new revision for changed definitions'
        else:
            target.write_text(text, encoding='utf-8')
        live = ROOT / 'Assets' / relative
        assert not live.exists() or sha(live) == sha(target)
        files.append(dict(path=relative, source=target.relative_to(ROOT).as_posix(), sha256=sha(target)))
        regions.append(dict(definition=relative, dimensions=[right - left, bottom - top],
                            source_rectangle=[left, top, right, bottom]))
    placements = []
    for side in ('west', 'east'):
        for index, patch in enumerate(ground['patches']):
            points = copy.deepcopy(patch['points'])
            if side == 'east':
                for point in points:
                    point[0] *= -1
            dx, dy = points[3][0] - points[0][0], points[3][1] - points[0][1]
            length = math.hypot(dx, dy)
            e = sum(point[0] for point in points) / 4
            n = sum(point[1] for point in points) / 4
            placements.append(dict(name=f'{side}-{index}', side=side, front=patch['front'],
                                   definition=regions[patch['atlas']]['definition'],
                                   position=[n, -e, .5], forward=[0, 0, -1], up=[-dy / length, dx / length, 0],
                                   size=[patch['width'], patch['depth']], projection_depth=2,
                                   source_footprint=points))
    assert len(placements) == ground['patches_per_half'] * 2 == 116
    probes = []
    for front, centre in (('house-9/+e', [-1393.323, 379.7965]), ('house-8/-e', [-1856.32457, 627.60665])):
        choice = min((p for p in placements if p['side'] == 'west' and p['front'] == front),
                     key=lambda p: math.hypot(-p['position'][1] - centre[0], p['position'][0] - centre[1]))
        probes.append(choice['name'])
    source_paths = [Path(__file__), GROUND, GROUND.with_name('geometry-checks.json'),
                    ROOT / 'Assets' / ATLAS, ROOT / 'Assets/scenes/maps/Belltower/belltower.scene']
    engine = Path('D:/SteamLibrary/steamapps/common/sbox')
    manifest = dict(revision='ground-edge-v2', method='Native Decal, Multiply albedo, inherited surface PBR',
                    files=files, regions=regions, placements=placements, probe_names=probes,
                    source_sha256={**ground['source_sha256'], **{path.relative_to(ROOT).as_posix(): sha(path) for path in source_paths}},
                    engine_source_sha256={'core/shaders/common/classes/Decals.hlsl': sha(engine / 'core/shaders/common/classes/Decals.hlsl')},
                    source_atlas_sha256=atlas_sha, source_pixels_or_alpha_changed=False,
                    normal_roughness_metalness_ao_overrides=False, extra_meshes=0, collision_changes=False,
                    live_assets_written=False, native_verified=False,
                    limitations=['Still requires native crop/orientation, inherited-relief and visual review.',
                                 'Native decal count and gameplay cost are not yet measured.'])
    (STAGE / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(staged_definitions=len(files), total_placements=len(placements), probes=probes,
                          source_pixels_changed=False, live_assets_written=False)))


if __name__ == '__main__':
    main()

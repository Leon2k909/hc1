"""Stage sparse, doorway-safe ground details without editing live assets.

The photographic ImageGen atlas stays byte-identical. Its four pockets retain
their original aspect ratios. Frontages and door/shop gaps come from the map's
authored house definitions; candidate quads must lie wholly on existing paving.
Run this script, then render ground-edge-v1-studio for an offline comparison.
Publication and native visual/performance acceptance remain separate steps.
"""
import hashlib
import json
import math
from pathlib import Path
import re
import shutil

import numpy as np
from PIL import Image
from scipy import ndimage

from map_kit import Model, Wall, write_model, write_obj

ROOT = Path(__file__).resolve().parents[1]
QUALITY = ROOT / 'output/belltower/quality'
STAGE = QUALITY / 'ground-edge-v1'
STUDIO = QUALITY / 'ground-edge-v1-studio'
SOURCE = ROOT / 'Sources/Belltower/generated/ground-edge-v2.png'
PAINT = 'ground_edge_atlas'
RESOURCE = 'models/maps/belltower/ground-edge-v1'
MATERIAL = 'materials/belltower/ground-edge-v1/ground_edge.vmat'
SHADER = 'shaders/belltower_ground_edge_trial.shader'
TEXTURE = 'materials/belltower/ground-edge-v1/ground_edge.png'
HEIGHT = .045  # 1.14 mm above the existing paving crest; no collision.

SHADER_SOURCE = '''HEADER
{
    Description = "Belltower sparse ground pockets: original RGBA albedo";
}
FEATURES
{
    #include "common/features.hlsl"
    Feature( F_ALPHA_TEST, 0..1, "Rendering" );
}
MODES
{
    Forward();
    Depth( S_MODE_DEPTH );
    ToolsShadingComplexity( "tools_shading_complexity.shader" );
}
COMMON
{
    #include "common/shared.hlsl"
}
struct VertexInput
{
    #include "common/vertexinput.hlsl"
};
struct PixelInput
{
    #include "common/pixelinput.hlsl"
};
VS
{
    #include "common/vertex.hlsl"
    PixelInput MainVs( VertexInput i ) { return FinalizeVertex( ProcessVertex( i ) ); }
}
PS
{
    #include "common/utils/Material.CommonInputs.hlsl"
    CreateInputTexture2D( TextureDetail, Srgb, 8, "", "_color", "Ground detail", Default4( 1, 1, 1, 1 ) );
    Texture2D g_tDetail < Channel( RGBA, Box( TextureDetail ), Srgb ); OutputFormat( BC7 ); SrgbRead( true ); >;
    SamplerState DetailSampler < Filter( ANISOTROPIC ); AddressU( CLAMP ); AddressV( CLAMP ); >;
    #undef MATERIAL_ALPHA_TEXTURE
    #define MATERIAL_ALPHA_TEXTURE g_tDetail
    #include "common/pixel.hlsl"
    StaticCombo( S_ALPHA_TEST, F_ALPHA_TEST, Sys( ALL ) );
    float g_flDetailFadeStart < Default( 900 ); Range( 100, 3000 ); UiGroup( "Ground detail,20/10" ); >;
    float g_flDetailFadeEnd < Default( 1600 ); Range( 101, 4000 ); UiGroup( "Ground detail,20/20" ); >;

    float4 MainPs( PixelInput i ) : SV_Target0
    {
        Material m = Material::From( i );
        float4 detail = g_tDetail.Sample( DetailSampler, i.vTextureCoords.xy );
        float distanceToCamera = length( m.WorldPosition - g_vCameraPositionWs );
        float fade = 1.0 - smoothstep( g_flDetailFadeStart, max( g_flDetailFadeStart + 1.0, g_flDetailFadeEnd ), distanceToCamera );
        m.Opacity = detail.a * fade;
        AdjustAlphaToCoverage( m );
        m.Albedo = detail.rgb;
        m.Roughness = .96;
        m.Metalness = 0;
        return ShadingModelStandard::Shade( i, m );
    }
}
'''


def sha(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atlas_regions():
    """Read/crop UV bounds only; preserve original image pixels and alpha."""
    with Image.open(SOURCE) as image:
        assert image.mode == 'RGBA'
        alpha = np.asarray(image.getchannel('A'))
    height, width = alpha.shape
    regions = []
    for row in range(2):
        for col in range(2):
            x0, x1 = col * width // 2, (col + 1) * width // 2
            y0, y1 = row * height // 2, (row + 1) * height // 2
            cell = alpha[y0:y1, x0:x1]
            # Ignore isolated specks that the generator placed between atlas
            # cells. UV selection keeps the main deposit intact without
            # rewriting any pixels or sampling a neighbouring strip.
            labels, count = ndimage.label(cell > 81)
            sizes = np.bincount(labels.ravel())
            sizes[0] = 0
            assert count and sizes.max() > 1000
            ys, xs = np.where(labels == sizes.argmax())
            # A stray disconnected grain can sit on a fixed four-pixel crop
            # border. Choose nearby clear source rows/columns instead, keeping
            # the entire connected deposit and its original proportions.
            column_alpha, row_alpha = cell.max(axis=0), cell.max(axis=1)
            left = next((x for x in range(int(xs.min()) - 4, -1, -1) if column_alpha[x] < 80), None)
            right_edge = next((x for x in range(int(xs.max()) + 4, cell.shape[1]) if column_alpha[x] < 80), None)
            top = next((y for y in range(int(ys.min()) - 4, -1, -1) if row_alpha[y] < 80), None)
            bottom_edge = next((y for y in range(int(ys.max()) + 4, cell.shape[0]) if row_alpha[y] < 80), None)
            assert all(value is not None for value in (left, right_edge, top, bottom_edge)), 'Atlas needs transparent padding'
            right, bottom = right_edge + 1, bottom_edge + 1
            assert 0 <= left < right <= cell.shape[1] and 0 <= top < bottom <= cell.shape[0]
            crop = cell[top:bottom, left:right]
            border_max = int(max(crop[0].max(), crop[-1].max(), crop[:, 0].max(), crop[:, -1].max()))
            assert border_max < 80, 'An opaque atlas edge would make a rectangular patch'
            regions.append(dict(uv=[(x0 + left) / width, 1 - (y0 + bottom) / height,
                                    (x0 + right) / width, 1 - (y0 + top) / height],
                                aspect=(right - left) / (bottom - top), border_alpha_max=border_max))
    return regions


def frontages():
    import belltower_map as B
    fronts = []
    for index, row in enumerate(B.HOUSES):
        e0, e1, n0, n1, eave, _, faces = row[:7]
        for face, (letters, run) in sorted(faces.items()):
            wall = B.face_wall(e0, e1, n0, n1, face, 0, eave, run=run, corners=True)
            depth, sign = wall.outer()
            normal = [0, sign] if wall.axis == 'e' else [sign, 0]
            bay = (wall.run[1] - wall.run[0]) / len(letters)
            holes = []
            for k, letter in enumerate(letters):
                width = min(bay - 20, 132) if letter == 's' else 48 if letter == 'd' else min(bay - 16, 110) if letter == 'g' else 0
                if width:
                    centre = wall.run[0] + bay * (k + .5)
                    holes.append([centre - width / 2 - 12, centre + width / 2 + 12])
            fronts.append(dict(key=f'house-{index}/{face}', axis=wall.axis, run=list(wall.run),
                               depth=depth, normal=normal, protected_openings=holes))
    return fronts


def paving_rectangles():
    import belltower_map as B
    ground = Model()
    B.ground(ground)
    rectangles = []
    for paint in ('setts', 'flagstones'):
        for points, _ in ground.polygons[paint]:
            points = np.asarray(points)
            if np.all(np.abs(points[:, 2]) < 1e-8):
                rectangles.append([points[:, :2].min(axis=0), points[:, :2].max(axis=0)])
    return rectangles


def make_patches(fronts, regions, paving=None):
    model, records = Model(), []
    model.material_overrides[PAINT] = MATERIAL
    model.tile_overrides[PAINT] = 1
    for front in fronts:
        seed = int.from_bytes(hashlib.sha256(front['key'].encode()).digest()[:8], 'little')
        rng = np.random.default_rng(seed)
        along = np.array([1., 0.]) if front['axis'] == 'e' else np.array([0., 1.])
        out = np.asarray(front['normal'], dtype=float)
        origin = np.array([0., front['depth']]) if front['axis'] == 'e' else np.array([front['depth'], 0.])
        segments = [(front['run'][0] + 7, front['run'][1] - 7)]
        for lo, hi in sorted(front['protected_openings']):
            segments = [(a, min(b, lo)) for a, b in segments if lo > a] + [(max(a, hi), b) for a, b in segments if hi < b]
        for start, end in sorted(segments):
            cursor = start + rng.uniform(3, 15)
            while cursor + 17 < end:
                kind = int(rng.choice(4, p=[.45, .24, .10, .21]))
                width = min(float(rng.uniform(19, 30)), end - cursor)
                depth = width / regions[kind]['aspect']
                angle = math.radians(rng.uniform(-4, 4))
                tangent = along * math.cos(angle) + out * math.sin(angle)
                away = out * math.cos(angle) - along * math.sin(angle)
                half_run = abs(np.dot(tangent, along)) * width / 2 + abs(np.dot(away, along)) * depth / 2
                half_depth = abs(np.dot(tangent, out)) * width / 2 + abs(np.dot(away, out)) * depth / 2
                centre_r = cursor + half_run
                if centre_r + half_run > end:
                    break
                centre = origin + along * centre_r + out * (2.55 + half_depth)
                plan = [centre - tangent * width / 2 - away * depth / 2,
                        centre + tangent * width / 2 - away * depth / 2,
                        centre + tangent * width / 2 + away * depth / 2,
                        centre - tangent * width / 2 + away * depth / 2]
                # A single convex paving rectangle must contain the entire
                # quad. This also excludes corner slivers and sloping roads.
                on_paving = paving is None or any(all(np.all(p >= lo - 1e-7) and np.all(p <= hi + 1e-7) for p in plan) for lo, hi in paving)
                if on_paving:
                    points = [np.r_[p, HEIGHT] for p in plan]
                    u0, v0, u1, v1 = regions[kind]['uv']
                    # The photograph's upper edge is the dense wall side.
                    uv = [(u0, v1), (u1, v1), (u1, v0), (u0, v0)]
                    if np.cross(points[1] - points[0], points[2] - points[0])[2] < 0:
                        points.reverse()
                        uv.reverse()
                    model.polygon(PAINT, points, (0, 0, 1), uv=uv)
                    records.append(dict(front=front['key'], atlas=kind, width=width, depth=depth,
                                        centre=centre.tolist(), run_bounds=[centre_r - half_run, centre_r + half_run],
                                        closest_distance_to_wall=2.55, points=[p.tolist() for p in points]))
                cursor = centre_r + half_run + rng.uniform(31, 70)
    return model, records


def material_text(texture=TEXTURE, studio=False):
    return ('"Layer0"\n{\n'
            f'    shader "{"shaders/complex.shader" if studio else SHADER}"\n'
            '    F_ALPHA_TEST "1"\n    g_flAlphaTestReference "0.32"\n'
            f'    {"TextureColor" if studio else "TextureDetail"} "{texture}"\n'
            '    g_flRoughnessScaleFactor "1"\n    g_flMetalness "0"\n}\n')


def studio(regions):
    import belltower_detail as D
    before, after = Model(), Model()
    front = dict(key='studio/+n', axis='e', run=[-100, 100], depth=0,
                 normal=[0, 1], protected_openings=[[-36, 36]])
    for model in (before, after):
        wall = Wall('e', (-100, 100), (-8, 0), (0, 70), '+n')
        wall.add(0, 44, 0, 64, 'shut')
        wall.build(model, 'render_rose', None, 'ashlar_grey', 'ashlar_grey', surface=None)
        model.box((-22, -4, 0), (22, -2, 64), 'planks_dark')
        for a, b in ((-100, -22), (22, 100)):
            model.box((a, 0, 0), (b, 2.5, 12), 'ashlar_grey')
        model.polygon('setts', [(-100, 0, 0), (100, 0, 0), (100, 84, 0), (-100, 84, 0)], (0, 0, 1))
        D.configure(model)
        # The generic Blender material reader does not run the stone shader's
        # UV multiplier. Bake only that known coordinate transform into this
        # disposable studio mesh so its photographed stones stay at real scale.
        cobbles = (ROOT / 'Assets' / D.MATERIALS['setts']).read_text(encoding='utf-8')
        uv_scale = re.search(r'g_vStoneUvScale\s+"\[([0-9.]+)', cobbles)
        assert uv_scale, 'Review the studio paving conversion after a material change'
        model.tile_overrides['setts'] /= float(uv_scale.group(1))
    detail, records = make_patches([front], regions)
    for points, normal in detail.polygons[PAINT]:
        index = len(after.polygons[PAINT])
        after.polygon(PAINT, points, normal, uv=detail.polygon_uvs[(PAINT, index)])
    preview_material = STUDIO / 'ground-edge-studio.vmat'
    preview_material.write_text(material_text(SOURCE.as_posix(), studio=True), encoding='utf-8')
    after.material_overrides[PAINT] = preview_material.as_posix()
    after.tile_overrides[PAINT] = 1
    entries = []
    for name, model in (('ground-edge-before', before), ('ground-edge-after', after)):
        write_obj(STUDIO / (name + '.obj'), model, 'belltower_west')
        # Preview cameras use engine world (n,-e,z), while authored geometry
        # and placement records use plan coordinates (e,n,z).
        entries.append(dict(name=name, review_bounds=[[-8, -100, 0], [84, 100, 70]],
                            camera_offset=[1.4, .85, 1.0],
                            materials={paint: model.material_overrides[paint] for paint in model.polygons},
                            alpha_color_materials={PAINT: {'source': SOURCE.as_posix(), 'threshold': .32, 'roughness': .96}} if name.endswith('after') else {}))
        close = dict(entries[-1])
        close['name'] = name + '-close'
        centre = np.asarray(records[0]['centre'])
        close['review_bounds'] = [[centre[1] - 18, -centre[0] - 32, 0], [centre[1] + 32, -centre[0] + 32, 26]]
        close['camera_offset'] = [1.45, .65, .95]
        write_obj(STUDIO / (close['name'] + '.obj'), model, 'belltower_west')
        entries.append(close)
    (STUDIO / 'models.json').write_text(json.dumps(entries, indent=2) + '\n', encoding='utf-8')
    return len(records)


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    STUDIO.mkdir(parents=True, exist_ok=True)
    provenance = json.loads(SOURCE.with_suffix('.json').read_text(encoding='utf-8'))
    assert sha(SOURCE) == provenance['sha256']
    before_rng = np.random.get_state()
    regions, fronts, paving = atlas_regions(), frontages(), paving_rectangles()
    west, records = make_patches(fronts, regions, paving)
    assert records and not west.boxes and not west.hulls
    east = west.mirrored({})
    assets = STAGE / 'Assets'
    model_dir = assets / RESOURCE
    model_dir.mkdir(parents=True, exist_ok=True)
    for side, model in (('west', west), ('east', east)):
        write_model(model_dir, RESOURCE, 'belltower_ground_edge_' + side, model)
    for relative, text in ((SHADER, SHADER_SOURCE), (MATERIAL, material_text())):
        target = assets / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding='utf-8', newline='\n')
    shutil.copy2(SOURCE, assets / TEXTURE)
    sources = [Path(__file__), ROOT / 'Tools/belltower_map.py', ROOT / 'Tools/map_kit.py',
               SOURCE, SOURCE.with_suffix('.json'), ROOT / 'Assets/shaders/belltower_forest.shader',
               ROOT / 'Assets/scenes/maps/Belltower/belltower.scene']
    files = []
    for path in sorted(p for p in assets.rglob('*') if p.is_file()):
        relative = path.relative_to(assets).as_posix()
        live = ROOT / 'Assets' / relative
        assert not live.exists() or sha(live) == sha(path), f'A different trial resource already exists: {relative}'
        files.append(dict(path=relative, source=path.relative_to(ROOT).as_posix(), sha256=sha(path)))
    after_rng = np.random.get_state()
    assert before_rng[0] == after_rng[0] and np.array_equal(before_rng[1], after_rng[1]) and before_rng[2:] == after_rng[2:]
    report = dict(revision='ground-edge-v1', state='staged offline; native import, visual and performance review pending',
                  files=files, source_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in sources},
                  atlas_regions=regions, frontages=fronts, patches=records,
                  patches_per_half=len(records), triangles_per_half=west.triangle_count(),
                  material_count=1, collision_shapes=0, shadow_casting=False,
                  protected_opening_margin_inches=12, shared_rng_unchanged=True,
                  actual_source_dimensions=provenance['dimensions'], original_rgba_unchanged=True,
                  live_assets_written=False, native_verified=False, studio_patches=studio(regions),
                  limitations=['Small details use a flat albedo surface; no per-grain geometry or measured normal map.',
                               'Native alpha edges, paving overlap, distance fade and runtime cost need review.'])
    (STAGE / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({key: report[key] for key in ('patches_per_half', 'triangles_per_half', 'material_count', 'collision_shapes', 'live_assets_written', 'studio_patches')}))


if __name__ == '__main__':
    main()

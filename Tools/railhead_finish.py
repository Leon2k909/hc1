"""Railhead's finish materials: the booking hall's lime plaster and the goods sheds' and signal box's brick.

    python Tools/railhead_finish.py --stage <dir>      # draw them under <dir>/materials/railhead/finish (and the
                                                        # surfaces stage() lists under <dir>/materials/railhead)

Every writer takes its output folder; nothing here writes Assets except ensure_materials(), which only fills in
files that are missing there during a full offline regeneration (railhead_map.py calls it).

- rw_lime (the paint "render_cream" in the station's models, 256 in a tile): c.1900 lime plaster under mineral paint.
  rw_lime_dark is the same plaster sooted (the vault and above the gallery); rw_lime_dado the lowest 1.5 m, scuffed and
  grimy, anchored at z 0 (railhead_materials.ANCHORED).
- rw_brick (the paint "brick", whose UVs tile at 64 in): Reichsformat brick in English cross bond, drawn over a
  133.3 in tile (44 courses of 77 mm, 26 headers across) and scaled to it by g_vTexCoordScale. rw_brick_dark is the
  sooted top courses.
"""
from pathlib import Path
import argparse
import json
import math
import numpy as np
from PIL import Image
import railhead_materials as RM
import building_textures as BT
import terrain_textures as T

ROOT = Path(__file__).resolve().parents[1]
RESOURCE = 'materials/railhead/finish'
LIME_TILE = 256.0                       # building_textures' tile units for render_cream
BRICK_UV_TILE = 64.0                    # building_textures' tile units for brick (the models' UVs)
BRICK_COURSES = 44
BRICK_HEADERS = 26                      # headers across a tile; a stretcher is two
BRICK_COURSE = 3.0303                   # inches a course (77 mm: a 65 mm Reichsformat brick and its 12 mm joint)
BRICK_TILE = BRICK_COURSES * BRICK_COURSE

smoothstep = T.smoothstep


def _vmat(paint, colour, normal, rough, comment, scale=None, rough_exp=1.0):
    lines = ['// Tools/railhead_finish.py: ' + comment, '"Layer0"', '{', '    shader "shaders/complex.shader"',
             '    F_SPECULAR "1"', '    g_flMetalness "0"', f'    g_flRoughnessScaleFactor "{rough_exp:g}"',
             '    g_vColorTint "[1 1 1 1]"', '    g_flModelTintAmount "1"']
    if scale is not None:
        lines.append(f'    g_vTexCoordScale "[{scale:.7f} {scale:.7f}]"')
    lines += [f'    TextureColor "{RESOURCE}/{colour}"', f'    TextureNormal "{RESOURCE}/{normal}"',
              f'    TextureRoughness "{RESOURCE}/{rough}"',
              '    TextureAmbientOcclusion "materials/default/default_ao.tga"', '}']
    return '\n'.join(lines) + '\n'


def _soft_patches(rng, n, count, size_px, softness):
    """count soft-edged blobs about size_px across (wrapping), 0..1."""
    field = np.zeros((n, n))
    for _ in range(count):
        r = rng.uniform(.6, 1.0) * size_px
        RM.stamp(field, rng.uniform(0, n), rng.uniform(0, n), r, r * rng.uniform(.5, 1.0), 1.0,
                 rng.uniform(0, 3.2), soft=softness)
    return T.warp(rng, n, field, size_px * .25)


def _trowel_marks(rng, n, p):
    """The float's and trowel's marks in a hand-finished lime coat, as a height field in inches: thousands of
    overlapping arcs 10-24 in long and 4-8 in wide, each a shallow scoop with a lip where its edge stopped, laid in
    sweeps that follow the plasterer's arm, so the wall catches raking light in soft scales."""
    field = np.zeros((n, n))
    sweep = RM.noise(rng, n, 2.6, 1, 4)                     # the arm's direction drifts over the wall
    for _ in range(2600):
        x0, y0 = rng.uniform(0, n, 2)
        a = float(sweep[int(y0) % n, int(x0) % n]) * 0.9 + rng.normal(0, .35)
        length = rng.uniform(10, 24) * p
        width = rng.uniform(4, 8) * p
        RM.stamp(field, x0, y0, length / 2, width / 2, rng.uniform(.4, 1.0), a, profile='dome', mode='add')
    field = field - T.blur(field, 10 * p)                    # only the marks' own relief, not their pile-up
    return field / (field.std() + 1e-9)


def plaster(out):
    """rw_lime, rw_lime_dark and rw_lime_dado: 2048 px over 256 in (8 px an inch). c.1900 lime plaster under mineral
    paint, nearly even at 10 m (round 2: the half-metre wash read as water stains, parchment): only broad shifts at
    1-4 cycles (2-6 m) and a faint brush wash, paler than the hall's sandstone frame; the
    float's and trowel's marks 0.03 in deep that catch raking light, four hairline cracks 0.4-1.2 m long, three repairs
    in a smoother, lighter coat with a soft edge, a fine sand grain, roughness 0.80-0.92 with the cloud."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    n = 2048
    p = n / LIME_TILE
    rng = np.random.default_rng(5071)
    x, y = RM.coords(n)
    grain = RM.noise(rng, n, .4, n / 3)
    sand = RM.noise(rng, n, 1.0, 120, n / 3)
    trowel = _trowel_marks(rng, n, p)
    swirl = RM.noise(rng, n, 1.4, 20, 60)
    cloud = RM.noise(rng, n, 3.5, 1, 4)                     # broad: at 1-4 cycles a 6.5 m tile doesn't show its repeat
    wash = RM.noise(rng, n, 1.8, 6, 40)                      # the brush's wash: patchy, half a metre across
    blot = RM.noise(rng, n, 2.0, 6, 40)
    cracks = RM.crack_lines(rng, n, 4, (16 * p, 47 * p), 1.3, .3)
    repair = smoothstep(.3, .7, _soft_patches(rng, n, 3, 22 * p, 6 * p))
    # A repair is a newer, smoother coat: the old marks are gone under it, its own edge stands a hair proud.
    repair_edge = smoothstep(.0, .25, repair) * (1 - smoothstep(.25, .6, repair))
    height = ((.055 * trowel + .008 * swirl) * (1 - .8 * repair) + .0035 * sand + .0015 * grain
              - .02 * cracks + .012 * repair + .01 * repair_edge)
    # The mineral paint's cloud: broad shifts a few metres across, the brush's wash, and the paint pooling a shade
    # darker in the trowel's hollows.
    colour_lum = ((1 + .05 * cloud + .02 * wash + .01 * blot + .015 * grain - .025 * trowel)
                  * (1 + .06 * repair) * (1 - .6 * cracks))
    base = np.array([204., 198., 182.])
    colour = BT.paint(base, colour_lum)
    # The cloud isn't only lighter and darker: where the paint is thin the warmer lime shows, where thick it's greyer.
    colour = RM.tinted(colour, (210, 196, 166), .2 * smoothstep(-.8, 1.8, cloud) + .05 * smoothstep(-.5, 1.8, wash))
    rough = np.clip(.86 + .035 * cloud + .015 * grain - .04 * repair, .80, .92)

    # rw_lime_dark: soot from a century of steam and gas light, deeper in the vault, streaked down from ledges.
    # Soot settles as a cloud, heavier in places, with only faint runs: whole-wall vertical streaks read as curtains.
    soot_streak = smoothstep(.4, 2.6, RM.streaks(rng, n, 1.6, 2, 30, 140, 3.0)) * smoothstep(-.5, 1.5, RM.noise(rng, n, 2.6, 2, 8))
    soot_cloud = smoothstep(-1.8, 2.2, RM.noise(rng, n, 3.6, 1, 3) + .35 * RM.noise(rng, n, 2.0, 5, 30))
    dark = BT.paint(base * .82, colour_lum * (1 + .05 * cloud))
    dark = RM.mix(dark, BT.paint((92, 86, 76), 1 + .1 * grain + .05 * cloud), .2 + .35 * soot_cloud + .15 * soot_streak)
    # Soot settles most in the trowel's hollows and on the upper side of its lips.
    dark = RM.darken(dark, 1 - .08 * np.clip(-trowel, 0, 2))

    # rw_lime_dado: anchored at z 0, the picture's bottom rows are the wall's foot: grime over the lowest 8 in,
    # scuffs from feet, bags and trolleys up to 40 in, hand marks above that.
    z = (n - y) / p                                   # inches up from the floor
    foot = 1 - smoothstep(0, 14, z + 3 * RM.noise(rng, n, 1.6, 8, 120))
    canvas = RM.Canvas(n, 2, int(12 * p))
    for _ in range(140):
        zc = rng.uniform(2, 38) if rng.random() < .8 else rng.uniform(38, 60)
        x0 = rng.uniform(0, n)
        length = rng.uniform(1.5, 9) * p
        a = rng.normal(0, .12)
        canvas.line([(x0, n - zc * p), (x0 + length * math.cos(a), n - zc * p + length * math.sin(a))],
                    rng.uniform(.6, 2.2), rng.uniform(.3, .9))
    scuffs = canvas.result() * (z < 70)
    hand = smoothstep(.2, 1.6, RM.noise(rng, n, 2.2, 6, 60)) * smoothstep(30, 40, z) * (1 - smoothstep(56, 66, z))
    dado = RM.darken(colour, (1 - .08 * foot - .08 * smoothstep(60, 0, z)) * (1 - .3 * scuffs) * (1 - .08 * hand))
    dado = RM.mix(dado, BT.paint((110, 100, 86), 1 + .1 * grain), .35 * foot)

    normal = RM.gl_normals(height, p)
    RM.save_rgb(out / 'lime_color.png', colour)
    RM.save_rgb(out / 'lime_dark_color.png', dark)
    RM.save_rgb(out / 'lime_dado_color.png', dado)
    RM.save_rgb(out / 'lime_normal.png', (normal * .5 + .5) * 255)
    RM.save_grey(out / 'lime_rough.png', rough)
    (out / 'rw_lime.vmat').write_text(_vmat('rw_lime', 'lime_color.png', 'lime_normal.png', 'lime_rough.png',
                                            'mineral lime plaster, 256-inch tile.'), encoding='utf-8')
    (out / 'rw_lime_dark.vmat').write_text(_vmat('rw_lime_dark', 'lime_dark_color.png', 'lime_normal.png', 'lime_rough.png',
                                                 'lime plaster under soot (vault, above the gallery).', rough_exp=.9),
                                           encoding='utf-8')
    (out / 'rw_lime_dado.vmat').write_text(_vmat('rw_lime_dado', 'lime_dado_color.png', 'lime_normal.png', 'lime_rough.png',
                                                 'lime plaster at the wall foot, anchored at z 0.'), encoding='utf-8')
    print('wrote lime plaster: rw_lime, rw_lime_dark, rw_lime_dado', flush=True)


# A c.1900 Backstein wall: red-brown, from orange-red through brown to greyed (round 2: the old set was one new-build
# orange); the headers' vitrified ends dark, nearly black-brown and glassy.
BRICK_REDS = [(134, 72, 54), (118, 64, 50), (150, 86, 64), (104, 56, 46), (142, 92, 72), (126, 76, 60), (112, 70, 58)]
BRICK_BURNT = [(72, 44, 42), (64, 42, 42), (80, 50, 44)]
BRICK_MORTAR = (168, 160, 146)


def brick(out):
    """rw_brick and rw_brick_dark: Reichsformat brick (250 x 120 x 65 mm) in English cross bond, alternate stretcher
    and header courses, 2048 px over a 133.3 in tile (44 courses of 77 mm, 26 headers or 13 stretchers across: 15.4 px
    an inch). Red-browns from orange-red to greyed brown (each brick +-10 % in value and 0.8-1.1 in saturation, a third
    of them weathered greyer), a fifth of the headers vitrified dark clinker ends (glossier), each brick a hair proud or
    sunk (+-0.04 in) with a 0.3 in rounded, chipped arris; lime mortar joints 11 mm, raked back 0.25 in and greyed by
    soot so the bond has relief at 2-3 m and reads at 10 m. Sand grains and iron spots in each face. Soot mostly in the joints, with
    only a faint broad shift across the tile (a wall-wide mottle read as camouflage at engine scale); white efflorescence
    washing out under a few joints, a little green. rw_brick_dark is the
    sooted top courses, under the eaves where rain never washes them."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    n = 2048
    p = n / BRICK_TILE
    rng = np.random.default_rng(6203)
    x, y = RM.coords(n)
    ch = n / BRICK_COURSES
    course = np.minimum((y // ch).astype(int), BRICK_COURSES - 1)
    v = y - course * ch
    hw = n / BRICK_HEADERS                                   # a header's width (and half a stretcher's)
    header_course = course % 2 == 1
    # Stretcher courses alternate their offset by half a stretcher (cross bond); header courses sit a quarter brick in.
    shift = np.where(header_course, .5 * hw, np.where(course % 4 == 0, 0.0, hw))
    width = np.where(header_course, hw, 2 * hw)
    xs = (x + shift) % n
    k = np.floor(xs / width).astype(int)
    u = xs - k * width
    brick_id = course * BRICK_HEADERS + k
    count = BRICK_COURSES * BRICK_HEADERS
    joint = .22 * p                                          # half an 11 mm joint
    d = np.minimum(np.minimum(u, width - u), np.minimum(v, ch - v))
    # Hand-moulded brick isn't machine-straight: its arrises wander a little, so the joints vary in width.
    d = d + .025 * p * RM.noise(rng, n, 2.4, 8, 90)
    on_brick = d > joint
    # Per brick: tone, burnt headers, height, how chipped.
    tone = np.array(BRICK_REDS, float)[rng.integers(0, len(BRICK_REDS), count)]
    grey = tone.mean(1, keepdims=True)
    tone = grey + (tone - grey) * rng.uniform(.8, 1.1, (count, 1))          # saturation, brick by brick
    weathered = rng.random(count) < .33                                      # faces greyed by a century of weather
    tone = np.where(weathered[:, None], tone + (np.array([112., 100., 92.]) - tone) * rng.uniform(.15, .4, (count, 1)), tone)
    tone = tone * rng.uniform(.9, 1.1, (count, 1))                           # value
    burnt = rng.random(count) < .2
    tone_b = np.array(BRICK_BURNT, float)[rng.integers(0, len(BRICK_BURNT), count)] * rng.uniform(.92, 1.08, (count, 1))
    is_burnt = burnt[brick_id] & header_course
    lift = rng.normal(0, .02, count)
    tilt_u, tilt_v = rng.normal(0, .002, (2, count))
    fine = RM.noise(rng, n, .3, n / 3)
    sand = RM.noise(rng, n, 1.0, 60, n / 3)
    mottle = RM.noise(rng, n, 2.4, 8, 120)
    chipn = RM.noise(rng, n, 1.2, 40, 700)
    chip = smoothstep(2.1, 2.5, chipn) * (d < joint + .45 * p) * on_brick
    arris = smoothstep(joint, joint + .3 * p, d)
    face = lift[brick_id] + tilt_u[brick_id] * (u - width / 2) / p + tilt_v[brick_id] * (v - ch / 2) / p
    speck = RM.noise(rng, n, 0.0, n / 2.5)
    iron = smoothstep(2.0, 2.6, speck) * on_brick
    grains = smoothstep(2.0, 2.6, -speck) * on_brick
    height = np.where(on_brick, face + .016 * sand + .006 * fine - .015 * iron - .12 * (1 - arris) ** 2 - .12 * chip,
                      -.25 + .015 * fine)
    height = T.blur(height, .5)
    # Each brick's own clay: sand grains and iron spots in the face, a little cloud of its own, no blotches across the
    # wall (at engine scale a broad mottle read as camouflage).
    lum = (1 + .025 * mottle + .05 * fine + .03 * sand) * (1 - .25 * chip) * (1 - .35 * iron) * (1 + .18 * grains)
    col = np.where(is_burnt[..., None], tone_b[brick_id], tone[brick_id])
    # Firing: each brick a little darker at one end (the stack's flash).
    flash = rng.uniform(-1, 1, count)
    lum = lum * (1 + .06 * flash[brick_id] * (u / width - .5))
    colour = BT.shade(col, lum)
    mortar_lum = 1 + .06 * fine + .05 * mottle
    mortar = BT.paint(BRICK_MORTAR, mortar_lum)
    soot_joint = smoothstep(-.6, 1.6, RM.noise(rng, n, 2.2, 3, 60))
    mortar = RM.darken(mortar, 1 - .35 * soot_joint)
    in_joint = 1 - smoothstep(joint - .6, joint + .6, d)
    colour = RM.mix(colour, mortar, in_joint)
    ao = T.cavity_ao(height, ((.5 * p, .6), (2.0 * p, .3)), 1.0)
    # Weathering: soot blotches, efflorescence washing down from some joints, a little algae.
    soot = smoothstep(-.6, 2.2, RM.noise(rng, n, 3.2, 1, 3))   # broad and faint: the dark goes in the joints
    broad = RM.noise(rng, n, 4.0, 1, 1.5)                   # one gentle shift across the tile: +-4 %
    eff_src = np.zeros((n, n))
    for _ in range(10):                          # broad faint veils washing down under a few courses
        RM.stamp(eff_src, rng.uniform(0, n), rng.uniform(0, n), rng.uniform(5, 14) * p, rng.uniform(.6, 1.4) * p,
                 rng.uniform(.4, .9), soft=2.0 * p)
    eff = np.clip(RM.run_down(eff_src, 22 * p, .6, rng), 0, 1)
    eff = T.blur(eff, 2.0 * p) * (.7 + .3 * in_joint)
    green = RM.blotches(rng, n, 2.6, 2, 30, .06, .8)
    grime = smoothstep(-.8, 2.0, RM.noise(rng, n, 2.6, 1, 6) + .5 * RM.streaks(rng, n, 1.6, 2, 60, 80, 1.6))
    c = RM.darken(colour, (1 - .1 * soot) * (1 + .04 * broad) * (1 - .12 * grime))
    c = RM.mix(c, BT.paint((204, 202, 194), 1 + .05 * fine), .4 * eff)
    c = RM.tinted(c, (84, 96, 56), .2 * green)
    colours = {'rw_brick': T.shaded(c, ao, .55)}
    crust = np.clip(.45 + .3 * RM.noise(rng, n, 2.6, 1, 8) + .25 * in_joint
                    + .25 * smoothstep(-.4, 2.0, RM.streaks(rng, n, 1.6, 2, 60, 90, 1.6)), 0, 1)
    dk = RM.darken(colour, .78)
    dk = RM.mix(dk, BT.paint((44, 38, 34), 1 + .1 * fine), .6 * crust)
    colours['rw_brick_dark'] = T.shaded(dk, ao, .55)
    rough = np.clip(.8 + .05 * sand + .04 * fine + .08 * in_joint - .2 * is_burnt * on_brick, .55, .97)
    normal = RM.gl_normals(height, n / BRICK_TILE)
    RM.save_rgb(out / 'brick_color.png', colours['rw_brick'])
    RM.save_rgb(out / 'brick_dark_color.png', colours['rw_brick_dark'])
    RM.save_rgb(out / 'brick_normal.png', (normal * .5 + .5) * 255)
    RM.save_grey(out / 'brick_rough.png', rough)
    scale = BRICK_UV_TILE / BRICK_TILE
    note = f'Reichsformat brick, cross bond, {BRICK_TILE:.1f} in tile over the models\' 64 in UVs.'
    (out / 'rw_brick.vmat').write_text(_vmat('rw_brick', 'brick_color.png', 'brick_normal.png', 'brick_rough.png', note,
                                             scale=scale), encoding='utf-8')
    (out / 'rw_brick_dark.vmat').write_text(_vmat('rw_brick_dark', 'brick_dark_color.png', 'brick_normal.png',
                                                  'brick_rough.png', 'sooted ' + note, scale=scale, rough_exp=.9),
                                            encoding='utf-8')
    print('wrote brick: rw_brick, rw_brick_dark', flush=True)


# Paints this module owns, for railhead_materials.paints(): paint -> (texture, tile units the models' UVs use).
PAINTS = {'rw_lime': ('lime', LIME_TILE), 'rw_lime_dark': ('lime', LIME_TILE), 'rw_lime_dado': ('lime', LIME_TILE),
          'rw_brick': ('brick', BRICK_UV_TILE), 'rw_brick_dark': ('brick', BRICK_UV_TILE)}


def write(out_root):
    """Draw every finish material under out_root (laid out as Assets: out_root/materials/railhead/finish)."""
    finish = Path(out_root) / RESOURCE
    plaster(finish)
    brick(finish)
    return finish


def stage(destination):
    destination = Path(destination)
    surface = destination / 'materials/railhead'
    surface.mkdir(parents=True, exist_ok=True)
    for name in ('asphalt', 'dressed', 'steel', 'lattice'):
        RM.write_texture(name, surface)
    write(destination)
    files = sorted(str(p.relative_to(destination)).replace('\\', '/') for p in destination.rglob('*') if p.is_file())
    (destination.parent / 'finish-files.json').write_text(json.dumps(files, indent=2), encoding='utf-8')
    print(f'Staged {len(files)} surface files in {destination}')


def ensure_materials(out_root=None):
    """Create the finish files that are MISSING under out_root (default Assets) during a full offline map
    regeneration. Never overwrites: changed materials go through write(<stage>) and the integration step."""
    finish = Path(out_root or ROOT / 'Assets') / RESOURCE
    if any(not (finish / name).is_file() for name in ('rw_lime.vmat', 'lime_color.png', 'lime_normal.png', 'lime_rough.png')):
        plaster(finish)
    if not (finish / 'rw_brick.vmat').is_file():
        brick(finish)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--stage', type=Path, help='write the finish materials (and the surfaces it re-stages) here')
    parser.add_argument('--only', action='store_true', help='with --stage: only the finish materials')
    args = parser.parse_args()
    if args.stage is None:
        parser.error('--stage is required (this script never writes Assets directly)')
    if args.only:
        write(args.stage)
    else:
        stage(args.stage)

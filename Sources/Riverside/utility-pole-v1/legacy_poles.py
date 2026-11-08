"""Redraw the old Riverside utility poles exactly as the map's dressing mesh holds them (writes only under output/ and, for
the kept originals, Assets/models/props/riverside/utility_pole_original/).

The old poles were only ever geometry inside Assets/models/maps/riverside/riverside_dressing.obj: a shaft in four 8-sided
tapered pieces, one or two crossarm boxes and two steel braces per arm (`riverside_parts.pole`, paints rs_pole / rs_steel).
This calls that same function for the nine poles `riverside_map.dressing` places (without the transformer can and the
street-lamp arm, which stay in the dressing) and writes:

  output/riverside/utility-pole-v1/legacy_poles.obj          all nine in plan position, the fingerprint prepare_install.py cuts by
  Assets/models/props/riverside/utility_pole_original/        the same two shapes at a local origin, one model each, drawn the way
      pole_2arm_original.vmdl / pole_1arm_original.vmdl       the new models are (facing plan north), so a ModelRenderer with the
                                                              same position and yaw swaps old for new and back. Nothing uses them.
"""
from pathlib import Path
import hashlib, json, sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).absolute().parents[3]
sys.path.insert(0, str(ROOT / 'Tools'))
import map_kit as K          # noqa: E402
import riverside_parts as P  # noqa: E402
import riverside_map as R    # noqa: E402

OUT = ROOT / 'output/riverside/utility-pole-v1'
DEST = ROOT / 'Assets/models/props/riverside/utility_pole_original'
RES = 'models/props/riverside/utility_pole_original'
# (height, arms, facing) of the two kinds, as riverside_map.dressing calls them
WEST = dict(height=430, arms=2, facing=(1, 0.1))
EAST = dict(height=400, arms=1, facing=(-1, 0))


def draw_old_poles(m):
    P.OLD_POLES_IN_DRESSING = True      # the map no longer draws them (the new models stand there); this asks for the old shapes
    for k, c in enumerate(R.POLES_WEST):
        P.pole(m, c, WEST['height'], facing=WEST['facing'], arms=WEST['arms'], transformer=False, lamp=None, seed=k)
    for k, c in enumerate(R.POLES_EAST):
        P.pole(m, c, EAST['height'], facing=EAST['facing'], arms=EAST['arms'], transformer=False, lamp=None, seed=10 + k)


def count_triangles(path):
    tris = 0
    for line in Path(path).read_text().splitlines():
        if line.startswith('f '):
            tris += len(line.split()) - 3
    return tris


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    m = K.Model()
    draw_old_poles(m)
    R.configure(m)
    legacy = OUT / 'legacy_poles.obj'
    print('legacy poles:', K.write_obj(legacy, m, 'legacy_poles'), 'triangles', legacy)
    info = dict(legacy=legacy.relative_to(ROOT).as_posix(), triangles=count_triangles(legacy), sha256=hashlib.sha256(legacy.read_bytes()).hexdigest())

    # The two shapes alone, at a local origin facing plan north (the new models' convention).
    DEST.mkdir(parents=True, exist_ok=True)
    for name, kind in (('pole_2arm_original', WEST), ('pole_1arm_original', EAST)):
        P.OLD_POLES_IN_DRESSING = True
        one = K.Model()
        P.pole(one, (0.0, 0.0, 0.0), kind['height'], facing=(0, 1), arms=kind['arms'], transformer=False, lamp=None)
        one.hulls = []              # the old collision stays in the dressing; this model only draws
        R.configure(one)
        obj = DEST / f'{name}.obj'
        tris = K.write_obj(obj, one, name)
        K.write_vmdl(DEST / f'{name}.vmdl', RES, name, one)
        info[name] = dict(triangles=tris, vmdl=f'{RES}/{name}.vmdl')
        print(name, tris, 'triangles')
    (OUT / 'legacy-manifest.json').write_text(json.dumps(info, indent=2))
    print(json.dumps(info, indent=2))


if __name__ == '__main__':
    main()

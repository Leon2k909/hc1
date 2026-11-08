"""Remove the terrace mast and lawn overlay from the current dressing imports."""
from pathlib import Path
from collections import Counter

root = Path(__file__).resolve().parents[1] / 'Assets'
resource = 'models/maps/veridant/terrace-paved-garden'
destination = root / resource
destination.mkdir(parents=True, exist_ok=True)
model = (root/'models/maps/veridant/veridant_dress.vmdl').read_text()
imports = {
    'cafe-pergola-teak-v1/base_without_cafe_pergola_0.obj': 72,
    'veridant_dress_hulls_default.obj': 36,
    'veridant_dress_hulls_metal.obj': 28,
}
for source, expected in imports.items():
    path = 'models/maps/veridant/' + source
    vertices, output = [], []
    removed = Counter()
    material = ''
    hull = 'hulls_' in source
    for line in (root/path).read_text().splitlines():
        if line.startswith('v '):
            vertices.append(tuple(map(float, line.split()[1:4])))
        elif line.startswith('usemtl '):
            material = line.split()[1]
        elif line.startswith('f '):
            points = [vertices[int(token.split('/')[0])-1] for token in line.split()[1:]]
            mast = (hull or material in {'vr_stone_dark', 'vr_brass', 'vr_mast'}) and all(
                abs(y-514)<6.1 and abs(x-413)<6.1 and 127.9<z<332.1 for y,z,x in points)
            lawn = material == 'vr_lawn' and any(
                all(y0-.01<=y<=620.01 and x0-.01<=x<=x1+.01 and abs(z-128.15)<.02 for y,z,x in points)
                for y0,x0,x1 in [(320,300,520),(380,640,900)])
            if mast or lawn:
                removed['mast' if mast else 'lawn'] += 1
                continue
        output.append(line)
    if sum(removed.values()) != expected:
        raise RuntimeError(f'{source}: expected {expected} faces, matched {removed}')
    filename = Path(source).name
    (destination/filename).write_text('\n'.join(output)+'\n')
    for line in output[:5]:
        if line.startswith('mtllib '):
            mtl = line.split(maxsplit=1)[1]
            source_mtl = (root/path).with_name(mtl)
            if source_mtl.exists():
                (destination/mtl).write_bytes(source_mtl.read_bytes())
    model = model.replace(path, f'{resource}/{filename}')
    print(source, dict(removed))
(destination/'dressing.vmdl').write_text(model)

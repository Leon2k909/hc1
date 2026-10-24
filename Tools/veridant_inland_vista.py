"""Veridant's fixed photographic inland horizon; no physics or animation.

Stage against the installed backdrop instead of regenerating the shared map.
Retained OBJ vertices, UVs, normals and faces remain byte-for-byte unchanged.
The normal generator calls replace() after the accepted bay impostor pass.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil

import numpy as np
import map_kit as K
from riverdale_parts import UP, unit, v, card

ROOT = Path(__file__).resolve().parents[1]
PAINT = "vr_inland_vista"
PAINTS = (PAINT, "vr_inland_vista_b", "vr_inland_vista_c")
MATERIAL = "materials/veridant/vr_inland_vista.vmat"
TEXTURE = "materials/veridant/vista/inland-v1.png"
CENTRE = np.array([75.0, -100.0])
RADIUS = 14000.0
def mainland_arc():
    """Keep the photographic sectors on land at this radius, including the ends."""
    from veridant_vista_ground import coast_data
    coast = coast_data()
    def inland(angle):
        a = math.radians(angle)
        e,n = CENTRE+RADIUS*np.array([math.cos(a),math.sin(a)])
        return e-np.interp(n,coast[:,1],coast[:,0])-300
    lo,hi = -180.,0.
    for _ in range(40):
        mid=(lo+hi)/2
        if inland(mid)<0: lo=mid
        else: hi=mid
    start=hi
    lo,hi=0.,180.
    for _ in range(40):
        mid=(lo+hi)/2
        if inland(mid)>=0: lo=mid
        else: hi=mid
    return start,lo


START, END = mainland_arc()
SEGMENTS = 48  # per sector; three distinct images instead of one enlarged image
SOURCE = ROOT / 'Sources/Veridant/inland-vista-v1/distance-fix'
IMAGE_META = json.loads((SOURCE / 'texture.json').read_text(encoding='utf-8'))
IMAGE_META['panels'] = [IMAGE_META['panels'][index] for index in (0,2,1)]
BRUSH_META = json.loads((SOURCE / 'scrub-texture.json').read_text(encoding='utf-8'))
HOUSES = {"vr_render", "vr_village", "vr_village_lit", "vr_village_roof", "vr_window_dark"}
BAY = {"vr_bay_headland", "vr_bay_boats"}
GROUND = {"vr_garrigue", "vr_scrub", "vr_scrub_dark", "vr_lawn"}


def terrain_skirt(model):
    from veridant_vista_ground import build
    build(model, radius=RADIUS, brush=BRUSH_META)


def keep(paint, points, props=False):
    if paint in BAY:
        return True
    if paint in PAINTS or paint in ('vr_inland_scrub','vr_inland_brush'):
        return False
    if props and paint in HOUSES:
        return False
    if props:
        return False
    # Leave the close sea wall, its riprap, and the far shore in the bay alone.
    # Only the mainland occupied by the villas is replaced.
    from veridant_backdrop import COAST
    points = np.asarray(points)
    if (points[:,0].min() >= -2100 and points[:,0].max() <= -1730
            and np.abs(points[:,1]).max() <= 2660 and points[:,2].max() <= 10):
        return True  # Keep the original sea wall and its riprap, not the old terrain sheet.
    coast = np.interp(np.asarray(points)[:, 1], [n for _, n in COAST], [e for e, _ in COAST])
    mainland = np.any(np.asarray(points)[:, 0] >= coast - 1200.0)
    return not mainland


def panel_mapping(index):
    panel = IMAGE_META['panels'][index]
    step = (END - START) / len(PAINTS)
    start = START + index * step
    end = START + (index+1) * step
    rect = panel['uv_rect_px']
    pixel_scale = RADIUS * math.radians(end-start) / (rect[2]-rect[0])
    # The irregular physical slope occludes the image's straight lower edge.
    offsets = [0.]
    for previous,current in zip(IMAGE_META['panels'][:-1],IMAGE_META['panels'][1:]):
        old_height = (previous['minimum_foot_row']-previous['top_rows'][-1])*pixel_scale
        new_height = (current['minimum_foot_row']-current['top_rows'][0])*pixel_scale
        offsets.append(offsets[-1]+old_height-new_height)
    bottom = 500-(rect[3]-panel['minimum_foot_row'])*pixel_scale+offsets[index]-max(offsets)
    return start, end, pixel_scale, bottom


def cards(model):
    for sector, paint in enumerate(PAINTS):
        start, end, pixel_scale, bottom = panel_mapping(sector)
        left, top, right, lower = IMAGE_META['panels'][sector]['uv_rect_px']
        width, raster_height = IMAGE_META['size']
        height = (lower-top) * pixel_scale
        def column(u):
            angle = math.radians(start + u*(end-start))
            return v(*(CENTRE + RADIUS*np.array([math.cos(angle), math.sin(angle)])), bottom)
        def uv(u, t):
            return ((left+(right-left)*u)/width, 1-(lower+(top-lower)*t)/raster_height)
        for index in range(SEGMENTS):
            u0, u1 = index/SEGMENTS, (index+1)/SEGMENTS
            p, q = column(u0), column(u1)
            model.polygon(paint, [p,q,q+UP*height,p+UP*height],
                          normal=unit(v(*CENTRE,100)-(p+q)/2),
                          uv=[uv(u0,0),uv(u1,0),uv(u1,1),uv(u0,1)])
        model.material_overrides[paint] = f'materials/veridant/{paint}.vmat'
        model.tile_overrides[paint] = 64.0


def replace(far, props):
    result = []
    for source, is_props in ((far, False), (props, True)):
        target = K.Model()
        target.material_overrides = dict(source.material_overrides)
        target.tile_overrides = dict(source.tile_overrides)
        target.grain_paints = set(source.grain_paints)
        for paint, polygons in source.polygons.items():
            for index, (points, normal) in enumerate(polygons):
                if keep(paint, points, is_props):
                    target.polygon("vr_lawn" if paint in GROUND else paint, points, normal,
                                   uv=source.polygon_uvs.get((paint, index)),
                                   normals=source.polygon_normals.get((paint, index)))
        assert not source.boxes and not source.hulls and not source.props
        result.append(target)
    cards(result[0])
    terrain_skirt(result[0])
    return tuple(result)


def material_text(index=0):
    rect = IMAGE_META['panels'][index]['uv_rect_px']
    width = IMAGE_META['size'][0]
    return ('// Tools/veridant_inland_vista.py\n"Layer0"\n{\n'
            '    shader "shaders/hc1_veridant_horizon_v4.shader"\n'
            '    F_ALPHA_TEST "0"\n'
            f'    TextureVista "{TEXTURE}"\n'
            '    g_flAlphaTestReference "0.55"\n'
            f'    g_flImageU0 "{rect[0]/width:.8f}"\n'
            f'    g_flImageU1 "{rect[2]/width:.8f}"\n'
            f'    g_flCoastSide "{(-1 if index==0 else 1 if index==2 else 0)}"\n'
            f'    g_flSector "{index}"\n'
            f'    g_flPixelScale "{panel_mapping(index)[2]:.8f}"\n'
            f'    g_flAtlasWidth "{IMAGE_META["size"][0]}"\n'
            f'    g_flAtlasHeight "{IMAGE_META["size"][1]}"\n'
            + ''.join(f'    g_vAtlasRect{i} "[{" ".join(map(str,p["uv_rect_px"]))}]"\n'
                      f'    g_flBottom{i} "{panel_mapping(i)[3]:.8f}"\n'
                      for i,p in enumerate(IMAGE_META['panels'])) +
            '    g_flVistaBrightness "1.0"\n}\n')


def write_materials(out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    for index,paint in enumerate(PAINTS):
        (out / (paint + '.vmat')).write_text(material_text(index), encoding='utf-8')
    (out / 'vr_inland_scrub.vmat').write_text(
        '// Tools/veridant_inland_vista.py\n"Layer0"\n{\n'
        '    shader "shaders/hc1_veridant_scrub_v3.shader"\n'
        '    TextureGrass "materials/veridant/vr_lawn_color.jpg"\n'
        '    TextureSoil "materials/veridant/vr_gravel_color.jpg"\n}\n', encoding='utf-8')
    texture = out / 'vista/inland-v1.png'
    texture.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(ROOT / IMAGE_META['source'], texture)
    (out / 'vr_inland_brush.vmat').write_text(
        '// Tools/veridant_inland_vista.py\n"Layer0"\n{\n'
        '    shader "shaders/hc1_veridant_impostor.shader"\n'
        '    F_ALPHA_TEST "1"\n'
        '    TextureVista "materials/veridant/vista/inland-scrub.png"\n'
        '    g_flAlphaTestReference "0.65"\n'
        '    g_flVistaBrightness "0.9"\n}\n',encoding='utf-8')
    shutil.copy2(ROOT / BRUSH_META['source'],out / 'vista/inland-scrub.png')


def filtered_obj(source, destination, props=False):
    lines = source.read_bytes().splitlines(keepends=True)
    vertices = []
    for line in lines:
        if line.startswith(b"v "):
            x, z, n = map(float, line.split()[1:])
            vertices.append((-x, n, z))
    vertices = np.asarray(vertices)
    paint = None
    retained, removed, used = [], [], set()
    for line in lines:
        if line.startswith(b"usemtl "):
            paint = line.split()[1].decode()
        if line.startswith(b"f "):
            ids = [int(part.split(b"/")[0]) - 1 for part in line.split()[1:]]
            if not keep(paint, vertices[ids], props):
                removed.append(line)
                continue
            used.add(paint)
        retained.append(line)
    # ModelDoc's OBJ loader rejects empty material groups after face removal.
    retained = [line for line in retained if not line.startswith(b"usemtl ")
                or line.split()[1].decode() in used]
    retained = [b"usemtl vr_lawn\n" if line.startswith(b"usemtl ") and line.split()[1].decode() in GROUND
                else line for line in retained]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(b"".join(retained))
    counts = [sum(line.startswith(prefix) for line in retained) for prefix in (b"v ", b"vt ", b"vn ")]
    return {"before_triangles": sum(l.startswith(b"f ") for l in lines),
            "removed_triangles": len(removed),
            "retained_triangles": sum(l.startswith(b"f ") for l in retained),
            "retained_sha256": hashlib.sha256(b"".join(retained)).hexdigest(),
            "index_offsets": counts}


def stage(folder, source=None):
    folder = Path(folder).resolve()
    if folder.exists():
        raise FileExistsError(f"Use a fresh stage: {folder}")
    assets = folder / "Assets"
    live = ROOT / "Assets/models/maps/veridant"
    source = Path(source).resolve() if source else live
    target = assets / "models/maps/veridant"
    records, geometry = {}, {}
    for name in ("veridant_backdrop", "veridant_backdrop_props"):
        for suffix in (".obj", ".mtl", ".vmdl"):
            path = live / (name + suffix)
            records[path.relative_to(ROOT).as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        output = target / (name + ".obj")
        report = filtered_obj(source / output.name, output, name.endswith("_props"))
        for suffix in (".mtl", ".vmdl"):
            shutil.copy2(source / (name + suffix), target / (name + suffix))
        if not name.endswith("_props"):
            model = K.Model()
            cards(model)
            terrain_skirt(model)
            leaf = folder / "inland-card.obj"
            K.write_obj(leaf, model, "inland-card")
            offsets = report["index_offsets"]
            with output.open("ab") as writer:
                writer.write(b"\n# Photographic inland horizon\n")
                for line in leaf.read_bytes().splitlines(keepends=True):
                    if line.startswith((b"#", b"o ", b"mtllib ")):
                        continue
                    if line.startswith(b"f "):
                        ids = [[str(int(p) + offsets[i]) for i, p in enumerate(part.decode().split('/'))]
                               for part in line.split()[1:]]
                        line = ("f " + " ".join("/".join(part) for part in ids) + "\n").encode()
                    writer.write(line)
            paints = sorted(model.polygons)
            with output.with_suffix(".mtl").open("a", encoding="utf-8") as writer:
                for paint in paints:
                    writer.write(f"\nnewmtl {paint}\nKd 1 1 1\nd 1\n")
            doc = output.with_suffix(".vmdl")
            text = doc.read_text(encoding="utf-8")
            assert '"Physics' not in text and PAINT not in text
            additions = ''.join(f'\n\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "{model.material_overrides[paint]}" }},'
                                for paint in paints if f'from = "{paint}.vmat"' not in text)
            text = text.replace('remaps =\n\t\t\t\t\t\t[', 'remaps =\n\t\t\t\t\t\t[' + additions, 1)
            assert all(text.count(f'from = "{paint}.vmat"') == 1 for paint in PAINTS)
            doc.write_text(text, encoding="utf-8")
            report["added_triangles"] = model.triangle_count()
        report["after_triangles"] = report["retained_triangles"] + report.get("added_triangles", 0)
        geometry[name] = report
    write_materials(assets / 'materials/veridant')
    for name,version in (('hc1_veridant_horizon','_v4'),('hc1_veridant_scrub','_v3')):
        target_shader = assets / 'shaders' / (name+version+'.shader')
        target_shader.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(SOURCE / (name+'.shader.txt'), target_shader)
    manifest = {"expected_sha256": records, "geometry": geometry,
                "collision": False, "shadows": False,
                "files": [p.relative_to(folder).as_posix() for p in sorted(assets.rglob('*')) if p.is_file()]}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(manifest, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', required=True)
    parser.add_argument('--source', help='Original backdrop backup for a targeted revision')
    args = parser.parse_args()
    stage(args.stage, args.source)

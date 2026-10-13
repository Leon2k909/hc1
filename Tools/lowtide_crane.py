"""Blender-authored Lowtide quay crane, with smooth painted-steel PBR.

rtk proxy python Tools/lowtide_crane.py

The standalone pass replaces only old crane triangles in the dressing meshes.
Map regeneration uses build(), retaining the detailed crane and original portal
collision. Reauthor the editable source with lowtide_crane_blender.py.
"""
import argparse
from collections import Counter
from functools import lru_cache
import gzip
import hashlib
import importlib.util
import io
import json
import re
import uuid

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

import map_kit as K
import terrain_textures as T

PAINT = "lt_crane_red"
PANELS = "lt_crane_red_panels"  # Legacy remap, retained for old source assets.
TILE_UNITS = 40.0
DIRECTORY = K.ASSETS / "materials/lowtide"
SOURCE_DIR = K.ROOT / "Sources/Lowtide/crane"
SOURCE = SOURCE_DIR / "oxide_red_source.png"
MESH = SOURCE_DIR / "lowtide_quay_crane.mesh.json.gz"
REPORT = K.ROOT / "output/lowtide/crane-realism"
FINISHES = {
    "lt_crane_machined": ((.30, .34, .36), .39, .87),
    "lt_crane_oily": ((.105, .12, .13), .44, .70),
    "lt_crane_glass": ((.075, .14, .18), .16, .28),
    "lt_crane_trim": ((.47, .46, .41), .43, .72),
    "lt_crane_grate": ((.17, .19, .20), .65, .75),
}


def write_bytes(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists() or path.read_bytes() != data:
        tmp = path.with_name(path.name + ".writing")
        tmp.write_bytes(data)
        tmp.replace(path)


def metadata(path):
    sidecar = path.with_name(path.name + ".meta")
    if not sidecar.exists():
        key = "hc1/lowtide/crane/" + path.relative_to(K.ASSETS).as_posix()
        K.write_text(sidecar, json.dumps({"guid": str(uuid.uuid5(uuid.NAMESPACE_URL, key))}, indent=2) + "\n")


def save_map(suffix, array):
    path = DIRECTORY / f"{PAINT}_{suffix}.png"
    buffer = io.BytesIO()
    Image.fromarray(array).save(buffer, format="PNG", optimize=True)
    write_bytes(path, buffer.getvalue())
    metadata(path)


def bake():
    sample = Image.open(SOURCE).convert("RGB").resize((2048, 2048), Image.Resampling.LANCZOS)
    rgb = np.asarray(sample, dtype=np.float32) / 255.0
    lum = rgb @ np.array([.2126, .7152, .0722], dtype=np.float32)
    red = (rgb[..., 0] - rgb[..., 1]) / np.maximum(rgb[..., 0], .05)
    exposed = 1 - T.smoothstep(.24, .48, red)
    warm = (rgb[..., 0] - rgb[..., 2]) / np.maximum(rgb[..., 0], .05)
    rust = exposed * T.smoothstep(.12, .40, warm)
    steel = np.clip(exposed-rust, 0, 1)
    fine = gaussian_filter(lum, .65, mode="wrap") - gaussian_filter(lum, 3, mode="wrap")
    fading = gaussian_filter(lum, 25, mode="wrap")
    # The colour mottling must not become a concrete-like heightfield. Relief
    # comes only from the thin paint film, tiny scratches and actual paint loss.
    height = fine*.003 - gaussian_filter(exposed, .8, mode="wrap")*.004
    scale = sample.width/TILE_UNITS
    dx = (np.roll(height,-1,1)-np.roll(height,1,1))*.5*scale
    dy = (np.roll(height,-1,0)-np.roll(height,1,0))*.5*scale
    normal = np.stack((-dx,dy,np.ones_like(lum)),axis=-1)
    normal /= np.linalg.norm(normal,axis=-1,keepdims=True)
    rough = np.clip(.44+(fading-fading.mean())*.5+rust*.36-steel*.11+fine*.1,.30,.90)
    save_map("color", np.asarray(sample))
    save_map("normal", np.rint((normal+1)*127.5).clip(0,255).astype(np.uint8))
    save_map("rough", np.rint(rough*255).astype(np.uint8))
    save_map("metal", np.rint(steel*.92*255).astype(np.uint8))
    REPORT.mkdir(parents=True,exist_ok=True)
    K.write_text(REPORT/"surface.json",json.dumps({
        "albedo_source":str(SOURCE.relative_to(K.ROOT)),
        "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
        "dimensions":[2048,2048], "tile_inches":TILE_UNITS,
        "roughness_range":[float(rough.min()),float(rough.max())],
        "normal_convention":"OpenGL, thin paint film over smooth steel",
        "paint_is_dielectric":True, "real_panels_bolts_and_bevels":True,
    },indent=2)+"\n")


def write_materials():
    path = DIRECTORY/f"{PAINT}.vmat"
    resource = f"materials/lowtide/{PAINT}"
    K.write_text(path,f'''// Tools/lowtide_crane.py: weathered enamel on smooth fabricated steel.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    F_METALNESS_TEXTURE "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "0"
    TextureColor "{resource}_color.png"
    TextureNormal "{resource}_normal.png"
    TextureRoughness "{resource}_rough.png"
    TextureMetalness "{resource}_metal.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"
}}
''')
    metadata(path)
    for paint,(colour,rough,metal) in FINISHES.items():
        path = DIRECTORY/f"{paint}.vmat"
        K.write_text(path,f'''// Tools/lowtide_crane.py: distinct crane mechanical finish.
"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flRoughnessScaleFactor "1"
    g_flMetalness "{metal}"
    TextureColor "materials/default/default_color.tga"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "[{rough} {rough} {rough} 0]"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[{' '.join(str(c) for c in colour)} 1]"
    g_flModelTintAmount "1"
}}
''')
        metadata(path)


def configure(model):
    for paint in (PAINT,*FINISHES):
        if paint in model.polygons:
            model.material_overrides[paint] = f"materials/lowtide/{paint}.vmat"
            model.tile_overrides[paint] = TILE_UNITS if paint==PAINT else 32


@lru_cache(maxsize=1)
def mesh_data():
    with gzip.open(MESH,"rt",encoding="utf8") as f:
        return json.load(f)["faces"]


def build(model,e,n=-1475):
    origin = np.array((e,n,0),dtype=float)
    for paint,points,normals,uv in mesh_data():
        model.polygon(paint,np.asarray(points)+origin,uv=uv,normals=normals)
    # Retain the old 200-inch portal clearance and broad collision exactly.
    for de in (-70,70):
        for dy in (-90,90):
            model.collision_box((e+de-30,n+dy-9,0),(e+de+30,n+dy+9,22),"metal")
            model.collision_box((e+de-8,n+dy-8,22),(e+de+8,n+dy+8,200),"metal")
    model.collision_box((e-82,n-100,200),(e+82,n+100,228),"metal")
    configure(model)


def parse_obj(data):
    vertices = []
    records = []
    for line in data.decode("utf8").splitlines():
        if line.startswith("v "):
            vertices.append(tuple(float(x) for x in line.split()[1:4]))
        if line.startswith("f "):
            refs = [int(t.split("/")[0])-1 for t in line.split()[1:]]
            records.append((line,tuple(sorted(vertices[i] for i in refs))))
    return records


def patch_models():
    # Match the pre-pass crane triangles precisely; bounding-box deletion could
    # remove unrelated props. Existing face references and colliders stay intact.
    legacy = REPORT/"before/Tools/lowtide_map.py"
    if not legacy.exists():
        raise FileNotFoundError("Missing pre-pass map source for targeted mesh replacement")
    spec = importlib.util.spec_from_file_location("lowtide_crane_legacy_map",legacy)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    reports = []
    folder = K.ASSETS/"models/maps/lowtide"
    for side,s in (("east",1),("west",-1)):
        name = f"lowtide_dress_{side}"
        path = folder/f"{name}.obj"
        source = path.read_bytes()
        if b"# Blender-authored detailed quay cranes v2" in source or b"usemtl lt_crane_machined" in source:
            print(f"{name}: detailed cranes already installed")
            continue
        old_obj,new_obj = REPORT/f"legacy-{side}.obj",REPORT/f"detailed-{side}.obj"
        old_model,new_model = K.Model(),K.Model()
        for e in (1650,620):
            old.quay_crane(old_model,s,e)
            if not new_obj.exists():
                build(new_model,s*e)
        old.configure(old_model)
        K.write_obj(old_obj,old_model,name)
        triangles = K.write_obj(new_obj,new_model,name) if not new_obj.exists() else sum(len(face[1])-2 for face in mesh_data())*2
        paints = {face[0] for face in mesh_data()}
        selected = Counter(key for line,key in parse_obj(old_obj.read_bytes()))
        records = dict(parse_obj(source))
        lines = []
        removed = 0
        for line in source.decode("utf8").splitlines():
            key = records.get(line) if line.startswith("f ") else None
            if key is not None and selected[key]>0:
                selected[key]-=1
                removed+=1
            else:
                lines.append(line)
        if any(selected.values()):
            # An older prop-fragment refresher truncates everything after its
            # own faces. Recover only the known all-cranes-absent case recorded
            # by this pass, never a partially changed or unrecognised crane.
            active = None
            crane_faces = 0
            for line in lines:
                if line.startswith("usemtl "):
                    active = line.split()[1]
                elif line.startswith("f ") and active and active.startswith("lt_crane_"):
                    crane_faces += 1
            if removed == 0 and crane_faces == 0 and (REPORT/"replacement.json").exists():
                print(f"{name}: restoring cranes removed by another prop-fragment refresh")
            else:
                raise ValueError(f"{name}: {sum(selected.values())} legacy crane faces missing; refusing partial replacement")
        counts = {p:sum(line.startswith(p+" ") for line in lines) for p in ("v","vt","vn")}
        additions = []
        for line in new_obj.read_text().splitlines():
            if line.startswith(("v ","vt ","vn ","usemtl ")):
                additions.append(line)
            elif line.startswith("f "):
                refs = []
                for ref in line.split()[1:]:
                    values = [int(t) for t in ref.split("/")]
                    refs.append("/".join(str(v+counts[p]) for v,p in zip(values,("v","vt","vn"))))
                additions.append("f "+" ".join(refs))
        # Keep all attribute declarations before draw records for the engine's
        # OBJ importer. Old face indices and material assignments stay intact.
        combined = lines+additions
        attributes = []
        for prefix in ("v ","vt ","vn "):
            attributes.extend(line for line in combined if line.startswith(prefix))
        draw = [line for line in additions if line.startswith(("usemtl ","f "))]
        draw += [line for line in lines if line.startswith(("usemtl ","f "))]
        header = [line for line in lines if not line.startswith(("v ","vt ","vn ","usemtl ","f "))]
        updated = "\n".join(header+["# Blender-authored detailed quay cranes v2"]+attributes+draw)+"\n"
        assert sum(line.startswith("f ") for line in lines)==len(records)-removed
        vmdl = path.with_suffix(".vmdl")
        model_source = vmdl.read_text()
        before_physics = model_source[model_source.index('_class = "PhysicsShapeList"'):]
        extra = []
        for paint in sorted(paints):
            if f'from = "{paint}.vmat"' not in model_source:
                extra.append(f'\t\t\t\t\t\t\t{{ from = "{paint}.vmat" to = "materials/lowtide/{paint}.vmat" }},')
        marker = re.search(r'[^\n]*\{ from = "lt_crane_red\.vmat"[^\n]*\n',model_source)
        if not marker:
            raise ValueError("Crane material remap missing")
        model_source = model_source[:marker.end()]+"\n".join(extra)+"\n"+model_source[marker.end():]
        assert model_source[model_source.index('_class = "PhysicsShapeList"'):]==before_physics
        mtl = path.with_suffix(".mtl")
        mtl_source = mtl.read_text()
        for paint in sorted(paints):
            if f"newmtl {paint}\n" not in mtl_source:
                mtl_source+=f"newmtl {paint}\nKd 1 1 1\nd 1\n"
        write_bytes(path,updated.encode("utf8"))
        K.write_text(mtl,mtl_source)
        K.write_text(vmdl,model_source)
        reports.append({"model":name,"cranes":2,"removed_triangles":removed,"new_triangles":triangles,
                        "other_faces_preserved":len(records)-removed,"physics_preserved":True})
        print(f"{name}: replaced {removed} crane triangles with {triangles}; other props and collision preserved")
    if reports:
        K.write_text(REPORT/"replacement.json",json.dumps(reports,indent=2)+"\n")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--materials-only",action="store_true")
    args = p.parse_args()
    bake()
    write_materials()
    if not args.materials_only:
        patch_models()
    print("Lowtide: Blender crane, real steel sections and mechanisms, restrained enamel PBR")


if __name__=="__main__":
    main()

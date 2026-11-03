"""Stage a face-exact replacement of the eleven original ARM-04 monitors."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import riverdale_hall as H
import riverdale_materials as RM
import riverdale_radiation_monitor as ARM
from riverdale_splice import read_obj, write_obj

OUT = ROOT / "output/riverdale/radiation-monitor-v2"
STAGE = OUT / "stage"
ASSETS = ROOT / "Assets"


def sites():
    result = []
    for sign in (-1, 1):
        face = H.Face((sign * 1000, 0), (-sign, 0))
        for n, z in ((470, 86), (1560, 374)):
            result.append((face, face.s_of(sign * 1000, n), z))
    north = H.Face((0, 2000), (0, -1))
    result += [(north, 905, 86), (north, -560, 374), (north, 560, 374)]
    south = H.Face((0, -200), (0, 1))
    result += [(south, -460, 86), (south, 460, 86)]
    for sign in (-1, 1):
        face = H.Face((sign * 640, 0), (-sign, 0))
        result.append((face, face.s_of(sign * 640, 1320), 150))
    return result


def old_monitor(d, fine, face, s, z):
    face.box(d, s-7, s+7, z, z+10, 0, 5, "rv_hall_equipment")
    face.quad(fine, "rv_screens", s-5.5, s+1.5, z+3.5, z+8, 5.05, H.screen_uv("table"))
    face.quad(fine, "rv_hall_led_green", s+3, s+4.6, z+6.6, z+8.2, 5.05)
    face.quad(fine, "rv_hall_led_amber", s+3, s+4.6, z+3.8, z+5.4, 5.05)
    H.P.cylinder(fine, face.p(s+4, 0, 2.5), 1.4, z+10, z+13, "rv_hall_led_amber", 8, top="rv_hall_led_amber")
    H.sign_on(fine, face, "arm", s, z-3.2, 4.4)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def main():
    STAGE.mkdir(parents=True, exist_ok=True)
    entries, report = [], []
    def entry(relative):
        src, dst = STAGE / relative, ASSETS / relative
        entries.append(dict(Source=str(src), Target=str(dst), ExpectedSHA256=digest(dst), SHA256=digest(src)))
    old, new = (K.Model(), K.Model()), (K.Model(), K.Model())
    for face, s, z in sites():
        old_monitor(*old, face, s, z)
        ARM.monitor(*new, face, s, z)
    RM.load_extras()
    for m in (*old, *new):
        for p in m.polygons:
            if p not in m.tile_overrides:
                m.tile_overrides[p] = RM.TILES.get(p, 64.0)
    for i, name in enumerate(("riverdale_hall_detail", "riverdale_hall_fine")):
        rel = Path("models/maps/riverdale") / (name + ".obj")
        oldpath, newpath = OUT / (name+"-old.obj"), OUT / (name+"-new.obj")
        K.write_obj(oldpath, old[i], name)
        K.write_obj(newpath, new[i], name)
        header, published = read_obj(ASSETS / rel)
        _, removed = read_obj(oldpath)
        _, added = read_obj(newpath)
        before, remove, add = Counter(published), Counter(removed), Counter(added)
        assert not remove-before, f"{name}: {sum((remove-before).values())} legacy faces missing; refusing splice"
        after = before-remove+add
        assert before-after == remove-add and after-before == add-remove
        target = STAGE / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        write_obj(target, header, list(after.elements()))
        entry(rel)
        mtl = rel.with_suffix(".mtl")
        extra = sorted(set(new[i].polygons)-set(old[i].polygons))
        (STAGE / mtl).write_text((ASSETS / mtl).read_text()+"".join(f"\nnewmtl {p}\nKd 1 1 1\nd 1\n" for p in extra))
        entry(mtl)
        vmdl = rel.with_suffix(".vmdl")
        text = (ASSETS / vmdl).read_text()
        lines = text.splitlines(keepends=True)
        last = max(j for j, line in enumerate(lines) if 'from = ' in line and 'to = ' in line)
        lines[last] = lines[last].rstrip().rstrip(',')+',\n'
        lines[last+1:last+1] = [f'\t\t\t\t\t\t\t{{ from = "{p}.vmat" to = "{ARM.FOLDER}/{p}.vmat" }}'+(',\n' if j<len(extra)-1 else '\n') for j,p in enumerate(extra)]
        (STAGE / vmdl).write_text(''.join(lines))
        entry(vmdl)
        report.append(dict(Model=name, Removed=len(removed), Added=len(added), UnrelatedFacesPreserved=True, CollisionUnchanged=True))

    folder = Path(ARM.FOLDER)
    (STAGE / folder).mkdir(parents=True, exist_ok=True)
    pictures = ARM.artwork()
    configs = {ARM.SHELL: ((168,174,162), .64, 0), ARM.SEAL: ((24,29,28), .72, 0),
               ARM.STEEL: ((131,140,138), .37, 1), ARM.PANEL: (None, .58, 0),
               ARM.LCD: (None, .28, 0), ARM.SIGN: (None, .56, 0),
               ARM.AMBER: ((155,66,13), .29, 0), ARM.GREEN: ((49,114,56), .29, 0)}
    rng = np.random.default_rng(1414)
    for name, (color, rough, metal) in configs.items():
        if color:
            noise = rng.normal(0, .9, (256,256))
            pictures[name] = Image.fromarray(np.uint8(np.clip(np.array(color)[None,None,:]+noise[...,None],0,255)))
        pictures[name].save(STAGE / folder / (name+"_color.png"))
        Image.new("L", (64,64), round(rough*255)).save(STAGE / folder / (name+"_rough.png"))
        for suffix in ("color", "rough"):
            entry(folder / (name+"_"+suffix+".png"))
        emission = .8 if name == ARM.LCD else (.12 if name == ARM.AMBER else (2.2 if name == ARM.GREEN else 0))
        emit = f'\n    F_SELF_ILLUM "1"\n    g_flSelfIllumBrightness "{emission}"\n    g_flSelfIllumAlbedoFactor "1"\n    g_vSelfIllumTint "[1 1 1 1]"\n    TextureSelfIllumMask "[1 1 1 0]"\n' if emission else ''
        vmat = f'''"Layer0"
{{
    shader "shaders/complex.shader"
    F_SPECULAR "1"
    g_flMetalness "{metal}"
    g_flRoughnessScaleFactor "1"
    TextureColor "{ARM.FOLDER}/{name}_color.png"
    TextureNormal "materials/default/default_normal.tga"
    TextureRoughness "{ARM.FOLDER}/{name}_rough.png"
    TextureAmbientOcclusion "materials/default/default_ao.tga"
    g_vColorTint "[1 1 1 1]"
    g_flModelTintAmount "1"{emit}
}}
'''
        (STAGE / folder / (name+".vmat")).write_text(vmat)
        entry(folder / (name+".vmat"))
    # Front-sheet preview is also useful for checking artwork before engine import.
    pictures[ARM.PANEL].save(OUT / "panel-artwork.png")
    pictures[ARM.LCD].save(OUT / "lcd-artwork.png")
    manifest = dict(Entries=entries, Geometry=report, MonitorCount=len(sites()), SceneFileChanged=False)
    (OUT / "stage.json").write_text(json.dumps(manifest, indent=2))
    print(json.dumps({k:v for k,v in manifest.items() if k!='Entries'}, indent=2))


if __name__ == "__main__":
    main()

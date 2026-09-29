"""Where the eye sits behind each magnified MWII optic when aimed, and the eyepiece glass its magnified picture fills.

Every M4 optic was placed with the same OpticAimOffset x (-4), so a magnified one's eyepiece ended up wherever that put
its model: the 2x Magnifier and Holo's glass 2.1" from the eye, the 6x scopes' 1.3-1.6" (their eyepieces filled the
screen), the 3x Flip Magnifier's 5.3". The picture-in-picture was a fixed 0.3 of the screen's height wherever the glass
was, so it sat inside a ring of unmagnified glass or spilled over the housing.

For each magnified optic in gunsmith/m4a1/mw2022 this writes:
  - OpticEyepiece and OpticEyepieceDiameter: the centre of the eyepiece's rear glass in the optic model's space and its
    diameter (the model's "lens" bodygroup disc, in its *_reticle material). OpticZoom fits the picture to that glass.
  - OpticAimOffset x: puts the eye EYE_RELIEF[kind] behind that glass on the M4 (and so on every ported gun, whose
    OpticAimCorrection copies the M4's optic position). y and z, which line the sight up, are left alone.

Eye relief is the distance from the eyepiece's rear glass to the eye, from real optics of each kind (the longest of the
common ones, which reads best on screen):
  - magnifiers 2.8": Aimpoint's 3XMag-1 is 70 mm (EOTech's G33 2.2");
  - fixed 3x scopes 2.6": Vortex's Spitfire HD Gen II 3x (Trijicon's ACOGs 1.5-2.4");
  - digital scopes 2.56": 65 mm, Pulsar's Thermion 2 60 mm models (the 50 mm ones 50 mm);
  - 6x scopes 4": Vortex's Razor HD Gen II 1-6x24 (the Gen III 1-10x24 3.5").

Run from anywhere: python Tools/optic_eyepieces.py [--check]
"""
import json
import re
import sys
from pathlib import Path

ASSETS = Path(__file__).resolve().parent.parent / "Assets"
PARTS = ASSETS / "gunsmith/m4a1/mw2022"

# How far in front of the eye the M4's aimed pose holds an optic's origin before its OpticAimOffset: the Kastov 762's
# optic slot at its ADS pose (4.634, port_kastov) plus its verified OpticAimCorrection x (4.084), which maps it onto the M4.
# Every ported gun's correction is derived to copy it (checked on the 762, M16A4, P90 and Uzi: 2.15 to a 2x's tag_lense).
M4_OPTIC_DEPTH = 8.718

MAGNIFIER, PRISM, DIGITAL, SIX = 2.8, 2.6, 2.56, 4.0
EYE_RELIEF = {
    "att_vm_2x_west01": MAGNIFIER,
    "att_vm_2x_west02": MAGNIFIER,
    "att_vm_hybrid_west02": MAGNIFIER,
    "att_vm_hybrid_west02_thermal": MAGNIFIER,
    "att_vm_4x_east01_tall": PRISM,
    "att_vm_4x_west01_tall": PRISM,
    "att_vm_4x_west02_tall": PRISM,
    "att_vm_hybrid_west01": PRISM,
    "att_vm_hybrid_west03": PRISM,
    "att_vm_thermal_east01": DIGITAL,
    "att_vm_thermal_east01_hybrid": DIGITAL,
    "att_vm_thermal_west01": DIGITAL,
    "att_vm_scope_mike14": SIX,
    "att_vm_scope_vz": SIX,
}


def obj_triangles(path):
    """ Vertices in model space (ModelDoc reads the OBJ's (x, y, z) as model (Y, Z, X)) and each material's vertex ids. """
    vertices, used, material = [], {}, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("v "):
            x, y, z = map(float, line.split()[1:4])
            vertices.append((z, x, y))
        elif line.startswith("usemtl"):
            material = line.split()[1]
        elif line.startswith("f "):
            used.setdefault(material, set()).update(int(p.split("/")[0]) - 1 for p in line.split()[1:])
    return vertices, used


def eyepiece(part):
    """ The rear glass's centre (its rear face) and diameter, in the optic model's space. """
    prefab = json.loads((ASSETS / part["MainPrefab"]["prefab"]).read_text(encoding="utf-8"))
    model = next(c["Model"] for c in prefab["RootObject"]["Components"] if c.get("__type") == "Sandbox.ModelRenderer")
    vmdl = (ASSETS / model).read_text(encoding="utf-8")
    remap = dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"', vmdl))
    obj = ASSETS / re.search(r'filename = "([^"]+\.obj)"', vmdl).group(1)
    vertices, used = obj_triangles(obj)
    glass = [m for m, target in remap.items() if target.endswith("_reticle.vmat")]
    assert len(glass) == 1, (model, glass)
    points = [vertices[i] for i in used[glass[0]]]
    xs, ys, zs = zip(*points)
    centre = (min(xs), (min(ys) + max(ys)) / 2, (min(zs) + max(zs)) / 2)
    return centre, min(max(ys) - min(ys), max(zs) - min(zs))


def number(v):
    text = f"{v:.3f}".rstrip("0").rstrip(".")
    return "0" if text in ("-0", "") else text


def main():
    check = "--check" in sys.argv
    stale = 0
    for name, relief in EYE_RELIEF.items():
        path = PARTS / f"{name}.gnsmth"
        text = path.read_text(encoding="utf-8")
        part = json.loads(text)
        centre, diameter = eyepiece(part)
        aim = [float(v) for v in part["OpticAimOffset"].split(",")]
        aim[0] = relief - M4_OPTIC_DEPTH - centre[0]
        values = {
            "OpticAimOffset": f'"{",".join(f"{v:.6f}" for v in aim)}"',
            "OpticEyepiece": f'"{",".join(number(v) for v in centre)}"',
            "OpticEyepieceDiameter": number(diameter),
        }
        new = text
        for key, value in values.items():
            line = re.compile(rf'("{key}": )("[^"\n]*"|[^,\n}}]+)')
            if line.search(new):
                new = line.sub(lambda m: m.group(1) + value, new, count=1)
            else:
                # After the last property, keeping the file's own indentation.
                new = re.sub(r'(\n(\s*)"[^"\n]+": [^\n]*?)(\n\})\s*$', lambda m: f'{m.group(1)},\n{m.group(2)}"{key}": {value}{m.group(3)}\n', new, count=1)
        json.loads(new)
        print(f"{part['Name']:38s} eye {relief:.2f} behind glass x {centre[0]:7.3f}, {diameter:.3f} across -> aim x {aim[0]:.3f}")
        if new != text:
            stale += 1
            if not check:
                path.write_text(new, encoding="utf-8", newline="")
    print(f"{stale} part file(s) {'out of date' if check else 'written'}")
    return 1 if check and stale else 0


if __name__ == "__main__":
    sys.exit(main())

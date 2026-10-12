"""Align the separate reflex sights on MW22 hybrid optics, including their MP5 mounts.

python Tools/hybrid_optic_sights.py [--check]

Keep the scope's existing eye relief and every weapon's aim correction. The alternate
pose moves the weapon by the difference between the two glass centres; its reflex
sight is unmagnified. No mesh or primary optic alignment is changed.
"""
import argparse
import json
import re
from pathlib import Path

from optic_eyepieces import obj_triangles

ASSETS = Path(__file__).resolve().parent.parent / "Assets"
REFLEX_MATERIALS = {
    "att_vm_hybrid_west01": "attachment_vm_hybrid_west_lens_reflex_ads.vmat",
    "att_vm_hybrid_west03": "attachment_vm_minireddot02_lens_ads.vmat",
    "att_vm_thermal_east01_hybrid": "attachment_vm_minireddot02_lens_ads.vmat",
}


def sight_geometry(part):
    prefab = json.loads((ASSETS / part["MainPrefab"]["prefab"]).read_text(encoding="utf-8"))
    model = next(c["Model"] for c in prefab["RootObject"]["Components"] if c.get("__type") == "Sandbox.ModelRenderer")
    vmdl = (ASSETS / model).read_text(encoding="utf-8")
    remap = dict(re.findall(r'from = "([^"]+)\.vmat" to = "([^"]+)"', vmdl))
    obj = ASSETS / re.search(r'filename = "([^"]+\.obj)"', vmdl).group(1)
    vertices, used = obj_triangles(obj)

    def centre(material):
        axes = tuple(zip(*(vertices[i] for i in used[material])))
        return tuple((min(axis) + max(axis)) * 0.5 for axis in axes)

    kind = Path(model).stem
    reflex_name = REFLEX_MATERIALS[kind]
    primary = next(m for m, target in remap.items() if target.endswith("_reticle.vmat"))
    secondary = next(m for m, target in remap.items() if target.endswith("/" + reflex_name))
    scope, reflex = centre(primary), centre(secondary)
    reflex_axes = tuple(zip(*(vertices[i] for i in used[secondary])))
    radius = min(max(axis) - min(axis) for axis in reflex_axes[1:]) * 0.45
    # Depth stays as authored for the scope: a reflex sight has no restricted eye relief.
    return (0.0, scope[1] - reflex[1], scope[2] - reflex[2]), reflex, radius


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    stale = 0
    count = 0
    for path in sorted((ASSETS / "gunsmith").rglob("*.gnsmth")):
        if path.stem not in REFLEX_MATERIALS:
            continue
        text = path.read_text(encoding="utf-8")
        part = json.loads(text)
        if part.get("Category") != "Optic" or not part.get("OverrideAimOffset"):
            continue
        offset, reflex, radius = sight_geometry(part)
        values = {
            "HasAlternateSight": True,
            "AlternateSightAimOffset": ",".join(f"{v:.6f}" for v in offset),
            "AlternateSightAimAngles": "0,0,0",
            "AlternateSightMagnification": 1,
            "AlternateSightEyepiece": ",".join(f"{v:.6f}" for v in reflex),
            "AlternateSightRadius": round(radius, 6),
        }
        new = text
        for key, value in values.items():
            encoded = json.dumps(value)
            line = re.compile(rf'("{key}": )("[^"\n]*"|[^,\n}}]+)')
            if line.search(new):
                new = line.sub(lambda m: m.group(1) + encoded, new, count=1)
            else:
                new = re.sub(r'(\n(\s*)"[^"\n]+": [^\n]*?)(\n\})\s*$',
                             lambda m: f'{m.group(1)},\n{m.group(2)}"{key}": {encoded}{m.group(3)}\n', new, count=1)
        actual = json.loads(new)
        assert all(actual[key] == value for key, value in values.items()), path
        count += 1
        print(f"{path.relative_to(ASSETS)}: scope -> 1x reflex {values['AlternateSightAimOffset']}")
        if new != text:
            stale += 1
            if not args.check:
                path.write_text(new, encoding="utf-8", newline="")
    assert count == 5, f"Expected three MW22 optics plus their two MP5 variants, got {count}"
    print(f"{count} hybrid sights; {stale} {'out of date' if args.check else 'written'}")
    return 1 if args.check and stale else 0


if __name__ == "__main__":
    raise SystemExit(main())

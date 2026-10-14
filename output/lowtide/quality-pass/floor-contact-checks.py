"""Validate the static floor bake, runtime texture binding and preserved scope."""
import hashlib
import json
import re
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
before = json.loads((OUT/"floor-contact-before/manifest.json").read_text())
bake = json.loads((OUT/"floor-contact-stage/bake.json").read_text())
for rel, digest in {**before["geometry_and_scene"], **bake["inputs"]}.items():
    assert sha(ROOT/rel) == digest, f"Geometry changed: {rel}"
mask_path = ROOT/"Assets/materials/lowtide/interior/floor_contact.png"
assert mask_path.read_bytes() == (OUT/"floor-contact-stage/floor_contact.png").read_bytes()
mask = np.asarray(Image.open(mask_path).convert("RGB"), float)/255
assert mask.shape == (768, 768, 3)

def sample(e, n):
    u = (abs(e)-240)/760*.5 + (.5 if e < 0 else 0)
    v = 1-(n+400)/1550
    return mask[min(767, int(v*768)), min(767, int(u*768)), :2]

# Known physical contacts, including asymmetrical prop locations. These detect
# flipped axes/cells and a stale bake independently of the generator internals.
for sign in (1, -1):
    for e, n in ((500,130), (740,130), (500,630), (740,880)):
        assert max(sample(sign*e,n)) < .28, (sign,e,n,sample(sign*e,n))
    # The forklift chassis is raised above the floor; check its broad channel,
    # rather than expecting the immediate contact of a solid column base.
    assert sample(sign*640,560)[1] < .28
    assert min(sample(sign*620,0)) > .97, "Open floor should remain unoccluded"

material = ROOT/"Assets/materials/lowtide/interior/lt_concrete.vmat"
refs = sorted(set(x.decode() for x in re.findall(rb"materials/[a-zA-Z0-9_./-]+[.]vtex", material.with_suffix(".vmat_c").read_bytes())))
assert any("/floor_contact_png_" in r for r in refs), "Compiled material omitted the new texture input"
assert all((ROOT/"Assets"/(r+"_c")).exists() for r in refs)
engine = json.loads((OUT/"floor-contact-engine-checks.json").read_text())
assert engine["textureBound"] and not engine["materialError"] and not engine["remainingQaScenes"]
compiled = np.asarray(Image.open(OUT/"floor-contact-compiled.png").convert("RGB"),float)/255
assert compiled.shape == mask.shape
assert abs(compiled-mask).mean() < .006, "Compiled mask orientation or channel values changed"

captures = {}
for name in ("live-floor-contact-column-bound", "live-floor-contact-hall-bound", "live-floor-contact-cargo-final", "live-floor-contact-west-final"):
    diagnostic = (OUT/(name+"-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$",diagnostic,re.M)
    assert len(models)==15 and all(e=="False" and n=="0" for _,e,n in models)
    assert diagnostic.count("downwardClear=True")==18
    assert "Lights: points=24; spots=0" in diagnostic
    captures[name] = {"valid_renderers":15, "clear_emitters":18, "model_and_material_errors":0}

differences = {}
for label, old, new in (("column","live-floor-contact-column-disabled","live-floor-contact-column-bound"), ("cargo","live-floor-contact-cargo-disabled","live-floor-contact-cargo-final")):
    a = np.asarray(Image.open(OUT/(old+".png")),float)
    b = np.asarray(Image.open(OUT/(new+".png")),float)
    diff = b-a
    assert abs(diff).max() > 10 and diff.mean() < 0, "Enabled bake should darken contact regions"
    assert abs(diff).mean() < 5, "A local contact bake should not regrade the whole view"
    differences[label] = {"mean_pixel_change":float(diff.mean()), "mean_absolute_change":float(abs(diff).mean()), "maximum_absolute_change":float(abs(diff).max())}
report = {"unchanged_geometry_and_scene_files":len(before["geometry_and_scene"]), "added_triangles":0,
          "added_lights":0, "mask_resolution":[768,768], "ray_count":384*768*2*96,
          "compiled_texture_references":refs, "texture_bound_in_engine":True,
          "compiled_mask_mean_error":float(abs(compiled-mask).mean()), "captures":captures,
          "before_after_pixel_changes":differences, "remaining_qa_scenes":[],
          "performance":"One conditional floor texture sample; no controlled benchmark"}
(OUT/"floor-contact-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))

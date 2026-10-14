"""Verify applied material resources, unchanged geometry and final engine views."""
import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT / "Tools"))
import lowtide_banks as B

folder = Path(__file__).parent
assets = ROOT / "Assets"
stage = folder / "stone-surfaces-stage/Assets"
before = json.loads((folder / "stone-surfaces-before/manifest.json").read_text())
for relative,expected in before["geometry_and_scene"].items():
    assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest()==expected,relative
report = {"unchanged_geometry_and_scene_files":len(before["geometry_and_scene"]), "added_triangles":0,
          "materials":{}, "maps":{}, "captures":{}}
for relative,source in B.stone_material_sources().items():
    path = assets / relative
    assert path.read_text()==source==(stage / relative).read_text(),relative
    references = sorted(set(x.decode() for x in re.findall(rb"materials/[a-zA-Z0-9_./-]+[.]vtex",path.with_suffix(".vmat_c").read_bytes())))
    surface = "granite" if "granite" in relative else "clay"
    for suffix in ("color","normal"):
        assert any(f"/stone_{surface}_{suffix}_png_" in ref for ref in references), references
    # Compiled materials may retain the common constant RMA input even when
    # roughness is computed in the pixel shader. Validate every dependency.
    assert all((assets / (ref+"_c")).is_file() for ref in references)
    report["materials"][relative] = {"compiled_texture_references":references,"all_resolved":True}
for name,metres,depth in B.STONE_SOURCES:
    for suffix in ("color","normal"):
        relative = f"{B.STONE_RESOURCE}/stone_{name}_{suffix}.png"
        assert (assets / relative).read_bytes()==(stage / relative).read_bytes()
        im = Image.open(assets / relative)
        assert im.size==(2048,2048) and im.mode=="RGB"
        normal_stats = {}
        if suffix=="normal":
            normal = np.asarray(im,dtype=float)/127.5-1
            assert np.isfinite(normal).all() and normal[:,:,2].min() > 0
            assert np.allclose(np.linalg.norm(normal,axis=2),1,atol=.012)
            # Rare deep clay pores have steeper slopes than the granite. Check
            # valid normals and the overall relief, rather than clipping those.
            assert np.median(normal[:,:,2]) >= .99
            normal_stats = {"minimum_normal_z":float(normal[:,:,2].min()),
                            "first_percentile_normal_z":float(np.quantile(normal[:,:,2],.01))}
        report["maps"][relative] = {"size":list(im.size),"physical_tile_metres":metres,**normal_stats}
relative = "shaders/hc1_lowtide_stone.shader"
assert (assets / relative).read_bytes()==(stage / relative).read_bytes()
assert (assets / (relative+"_c")).is_file()
assert all(row["success"] for row in json.loads((folder / "stone-surface-compile-results.json").read_text()))
assert all(row["success"] for row in json.loads((folder / "stone-surface-final-compile.json").read_text()))
for name in ("live-stone-surfaces-final-low","live-stone-surfaces-final-player","live-canal-stone-surfaces-final"):
    text = (folder / (name+"-diagnostics.txt")).read_text()
    models = re.findall(r"^(.+): modelError=(\w+); materialErrors=(\d+)$",text,re.M)
    assert len(models)==15 and all(e=="False" and n=="0" for _,e,n in models)
    assert text.count("downwardClear=True")==18
    assert "Lights: points=24; spots=0" in text
    assert (folder / (name+".png")).is_file()
    report["captures"][name] = {"renderers":15,"model_errors":0,"material_errors":0,"clear_emitters":18}
assert json.loads((folder / "window-cleanup-check.json").read_text())["remainingQaScenes"]==[]
report["remaining_qa_scenes"] = []
report["projection"] = "World-space triplanar color and shallow normal slopes; no spherical UV sampling"
report["performance"] = "Six surface texture samples; no controlled benchmark performed"
(folder / "stone-surface-checks.json").write_text(json.dumps(report,indent=2)+"\n")
print(json.dumps(report,indent=2))

"""Stage only the two owned visual meshes; verify their pre-edit generators."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "Tools"))
import map_kit as K
import lowtide_map as L
import lowtide_banks as B
import lowtide_marine as M
import lowtide_finish as F

folder = Path(__file__).parent
stage = folder / "banks-stage"
stage.mkdir(exist_ok=True)
manifest = {}
for module, name in ((M, "lowtide_marine"), (F, "lowtide_finish")):
    path = folder / "banks-before/Tools" / (module.__name__ + ".py")
    spec = importlib.util.spec_from_file_location(module.__name__ + "_before_banks", path)
    old = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(old)
    before = old.build(L)
    check = stage / "original-generator"
    check.mkdir(exist_ok=True)
    K.write_obj(check / (name + ".obj"), before, name)
    original = L.OUT_DIR / (name + ".obj")
    assert original.read_bytes() == (check / original.name).read_bytes(), f"{name} has geometry outside its current generator; merge instead"
    model = module.build(L)
    assert not model.boxes and not model.hulls and not model.props
    count = K.write_model(stage, L.RESOURCE_DIR, name, model)
    manifest[name] = {"triangles": count, "previous_triangles": before.triangle_count(),
                      "sha256": hashlib.sha256(original.read_bytes()).hexdigest()}
    print(name, manifest[name])
(stage / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n")
B.bake_wet_silt()
materials = B.stone_material_sources()
for name in ("lt_mud", "lt_mud_wet"):
    relative = f"materials/lowtide/{name}.vmat"
    source = (K.ASSETS / relative).read_text()
    anchor = '    TextureRoughness "materials/lowtide/finish/silt_rough.png"\n'
    assert anchor in source and "TextureWetColor" not in source
    materials[relative] = source.replace(anchor, anchor +
        f'    TextureWetColor "{B.WET_RESOURCE}_color.png"\n    TextureWetNormal "{B.WET_RESOURCE}_normal.png"\n')
(stage / "materials.json").write_text(json.dumps(materials, indent=2)+"\n")
for path in ("shaders/hc1_lowtide_stone.shader", "materials/lowtide/marine/lt_tidal_brick.vmat"):
    B.metadata(K.ASSETS / path)

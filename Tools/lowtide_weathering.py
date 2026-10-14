"""Stage scoped exterior biofilm materials for native editor integration.

The generated albedo is copied unchanged. The shader masks it in world space,
so it follows exposed canal walls and warehouse plinths without altering UVs,
geometry, indoor surfaces or collision.
"""
import hashlib
import json
import shutil
import uuid
from pathlib import Path

import map_kit as K

TEXTURE = "materials/lowtide/masonry/canal_biofilm_color.png"
MATERIALS = {
    "materials/lowtide/lt_brick.vmat": .8,
    "materials/lowtide/lt_brick_soot.vmat": .8,
    "materials/lowtide/lt_brick_glazed.vmat": .8,
    "materials/lowtide/lt_brick_slime.vmat": .8,
    "materials/lowtide/finish/lt_quay_stone.vmat": 1.0,
    "materials/lowtide/masonry/lt_granite_trim.vmat": .9,
}


def material_inputs(strength, tidal_clay=False):
    return (f'    TextureCanalBiofilm "{TEXTURE}"\n'
            f'    g_flCanalBiofilm "{strength:g}"\n'
            + ('    g_flTidalClay "1"\n' if tidal_clay else ''))


def stage():
    folder = K.ROOT / "output/lowtide/quality-pass"
    target = folder / "weathering-stage/Assets"
    before = folder / "weathering-before"
    manifest = {}
    paths = [Path("shaders/hc1_brick.shader"), *map(Path, MATERIALS)]
    for relative in paths:
        source = K.ASSETS / relative
        backup = before / "Assets" / relative
        if backup.exists() and backup.read_bytes() != source.read_bytes():
            raise RuntimeError(f"Baseline changed: {relative}; inspect before staging again")
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, backup)
        manifest["Assets/" + relative.as_posix()] = hashlib.sha256(source.read_bytes()).hexdigest()
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        text = source.read_text()
        if relative.as_posix() in MATERIALS:
            assert "TextureCanalBiofilm" not in text
            text = text.replace('\n}', '\n' + material_inputs(MATERIALS[relative.as_posix()],
                relative.stem in ("lt_brick_glazed", "lt_brick_slime")) + '}')
        destination.write_text(text)
    protected = [K.ASSETS / "scenes/maps/Lowtide/lowtide.scene"]
    protected += sorted((K.ASSETS / "models/maps/lowtide").glob("*.obj"))
    protected += sorted((K.ASSETS / "models/maps/lowtide").glob("*.vmdl"))
    manifest.update({p.relative_to(K.ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in protected})
    (before / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    texture = target / TEXTURE
    texture.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(K.ROOT / "Sources/Lowtide/visual-target/canal-biofilm-source.png", texture)
    # Stage metadata using the final resource name, not the staging folder.
    sidecar = K.ASSETS / (TEXTURE + ".meta")
    if sidecar.exists():
        shutil.copy2(sidecar, Path(str(texture) + ".meta"))
    else:
        Path(str(texture) + ".meta").write_text(json.dumps({
            "guid": str(uuid.uuid5(uuid.NAMESPACE_URL, TEXTURE))}, indent=2) + "\n")
    print(f"Staged six material bindings and unchanged generated albedo; protected {len(protected)} scene/geometry files")


if __name__ == "__main__":
    stage()

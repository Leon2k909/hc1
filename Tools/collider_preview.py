"""Fast geometry-only preview, independent of Blender and the editor."""
import json
import re
from pathlib import Path
import numpy as np
from PIL import Image
import collider_map as C
import railhead_preview as P

ROOT = Path(__file__).resolve().parents[1]

def colour(paint):
    material = (ROOT / "output/collider/stage/materials/collider" / (paint+".vmat") if paint.startswith("co_")
                else ROOT / "Assets/materials/ares" / (paint+".vmat"))
    text = material.read_text()
    value = re.search(r'TextureColor\s+"([^"]+)"',text).group(1)
    tint = re.search(r'g_vColorTint\s+"\[([^\]]+)\]"',text)
    tint = np.array([float(v) for v in tint.group(1).split()][:3]) if tint else np.ones(3)
    if value.startswith("["):
        return np.array([float(v) for v in value.strip("[]").split()][:3]) * tint
    if value == "materials/default/default_color.tga": return tint
    p = ROOT / "Assets" / value
    if paint.startswith("co_"): p = C.STAGE / value
    return np.array(Image.open(p).convert("RGB").resize((16,16)),float).mean(axis=(0,1))/255*tint

def main():
    P.paint_colour=colour
    P.is_glass=lambda paint: "glass" in paint
    P.GLOWING.update(("co_beam","co_white","co_red","co_amber","ar_screens"))
    models=C.build()
    opaque=P.triangles(models.values())
    glass=P.triangles(models.values(),glass=True)
    config=json.loads((ROOT/"Sources/Collider/editor/capture-config.json").read_text())
    out=ROOT/"output/collider/geometry-preview"
    out.mkdir(parents=True,exist_ok=True)
    for view in config["views"]:
        P.perspective(opaque,glass,view["eye"],view["target"],(1280,720),view["fov"]).save(out/(view["name"]+".png"))
        print("wrote",view["name"],flush=True)

if __name__=="__main__": main()

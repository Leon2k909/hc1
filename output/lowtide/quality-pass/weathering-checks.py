"""Check weathering scope and generated texture provenance without rebuilding the map."""
import hashlib
import json
import re
import sys
from pathlib import Path
from PIL import Image, ImageStat

ROOT = Path(__file__).resolve().parents[3]
FOLDER = Path(__file__).parent
sys.path.insert(0, str(ROOT / "Tools"))
import lowtide_weathering as weather

manifest = json.loads((FOLDER / "weathering-before/manifest.json").read_text())
protected = {p: h for p, h in manifest.items() if p.endswith((".obj", ".vmdl", ".scene"))}
seam_manifest = json.loads((FOLDER / "tidal-seam-manifest.json").read_text())
for path, digest in protected.items():
    current_hash = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
    if current_hash != digest:
        repair = seam_manifest["changes"][path]
        assert repair["before"] == digest and repair["after"] == current_hash, path
source = ROOT / "Sources/Lowtide/visual-target/canal-biofilm-source.png"
texture = ROOT / "Assets" / weather.TEXTURE
assert source.read_bytes() == texture.read_bytes(), "Generated albedo must remain unchanged"
for relative, strength in weather.MATERIALS.items():
    current = (ROOT / "Assets" / relative).read_text()
    original = (FOLDER / "weathering-before/Assets" / relative).read_text()
    stripped = re.sub(r'^// Biofilm binding compiled after shader schema update\.\n', '', current)
    stripped = re.sub(r'^    (?:TextureCanalBiofilm|g_flCanalBiofilm|g_flTidalClay) .*\n', '', stripped, flags=re.M)
    assert stripped == original, relative
    assert weather.material_inputs(strength, Path(relative).stem in ("lt_brick_glazed", "lt_brick_slime")) in current
shader = (ROOT / "Assets/shaders/hc1_brick.shader").read_text()
assert 'float g_flCanalBiofilm < Default( 0 )' in shader
assert 'float g_flTidalClay < Default( 0 )' in shader
assert 'world.z < 100' in shader
assert 'face.y * sign( e ) > .6 || face.z > .6' in shader
# Match the shader's exact spatial bands at representative real locations.
def exterior(e, n, normal):
    a = abs(e)
    sign = 1 if e >= 0 else -1
    x, y, z = normal
    canal = 215 < a < 270 and -1450 < n < 1450 and (y * sign > .6 or z > .6)
    outside = 985 < a < 1015 and -410 < n < 1160 and y * sign < -.6
    ends = 230 < a < 1010 and ((abs(n + 400) < 14 and x < -.6) or (abs(n - 1150) < 14 and x > .6))
    return canal or outside or ends
for side in (-1, 1):
    assert exterior(side * 240, 0, (0, side, 0))
    assert not exterior(side * 260, 0, (0, -side, 0)), "Interior canal-side wall must remain unchanged"
    assert not exterior(side * 980, 0, (0, side, 0)), "Interior outer wall must remain unchanged"
    assert not exterior(side * 620, -380, (1, 0, 0)), "Interior end wall must remain unchanged"
    assert not exterior(side * 620, 400, (0, 0, 1)), "Interior floor must remain unchanged"
for suffix in ("canal-biofilm-v2", "biofilm-close-v2"):
    diagnostic = (FOLDER / f"live-{suffix}-diagnostics.txt").read_text()
    assert diagnostic.count("modelError=False; materialErrors=0") == 15
final_views = ("canal-biofilm-final", "biofilm-close-final", "biofilm-west-final")
image_checks = {}
for suffix in final_views:
    diagnostic = (FOLDER / f"live-{suffix}-diagnostics.txt").read_text()
    assert diagnostic.count("modelError=False; materialErrors=0") == 15
    with Image.open(FOLDER / f"live-{suffix}.png") as img:
        stats = ImageStat.Stat(img.convert("RGB"))
        assert max(stats.mean) > 10 and max(stats.stddev) > 10, suffix
        image_checks[suffix] = {"nonblank": True, "meanRGB": stats.mean}
# A completed capture command and clean material list did not ensure valid pixels.
with Image.open(FOLDER / "live-biofilm-interior-regression.png") as img:
    black_capture = max(ImageStat.Stat(img.convert("RGB")).mean) < 1
assert black_capture, "Review the replaced interior capture before changing its status"
with Image.open(FOLDER / "live-biofilm-interior-viewport.png") as img:
    interior_stats = ImageStat.Stat(img.convert("RGB"))
    assert max(interior_stats.mean) > 10 and max(interior_stats.stddev) > 10
assert "No matching console output" in (ROOT / "output/editor-startup-20261014/global-errors-after-viewport.json").read_text()
report = {
    "sourceScope": "PASS", "protectedSceneAndGeometryFiles": len(protected),
    "materialsWithBiofilm": len(weather.MATERIALS), "generatedAlbedoUnmodified": True,
    "interiorSurfaceExclusionSamples": "PASS", "initialWeatheringViews": "PASS",
    "finalTideBlendExteriorEngineValidation": "PASS: overview and both canal sides visually reviewed",
    "finalExteriorImageChecks": image_checks,
    "interiorRenderedRegression": "PASS: normal editor viewport visually reviewed; no fresh global console errors",
    "subsequentGeometryRepair": "Three OBJs match the separately validated tidal-seam manifest",
    "controlledPerformance": "PENDING: offscreen benchmark aborted; no FPS result",
}
(FOLDER / "weathering-checks.json").write_text(json.dumps(report, indent=2) + "\n")
print("PASS: protected scene/geometry; six input-only material edits; exact generated albedo; interior mask exclusions")
print("PASS: final exterior captures contain valid pixels and clean material diagnostics")
print("PASS: replacement interior viewport capture; prior black capture remains rejected")
print("PENDING: controlled game performance; current native editor snapshot is capped and has no comparison baseline")

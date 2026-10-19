"""Build linear reflection panoramas from native camera captures.

Stages EXRs and sky materials outside Assets. Import through the editor, then
copy its compiled cubes with apply-reflections.cs.txt. This avoids runtime GGX
filtering, which faults on the current workstation's Vulkan driver.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import struct
import zlib

import numpy as np
from PIL import Image

from sewage_reflections import write_exr

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "Sources/CerroBlanco/lighting/config.json"


def sky_functions():
    """Reuse the verified EXR reader and exact inverse of the engine ACES curve."""
    source = ast.parse((ROOT / "Tools/belltower_sky.py").read_text())
    names = {"read_exr", "undisplay", "srgb_linear", "aces", "display"}
    constants = {"ACES_IN", "ACES_OUT", "DESIGN_EXPOSURE"}
    selected = [node for node in source.body
                if isinstance(node, ast.FunctionDef) and node.name in names
                or isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id in constants for t in node.targets)]
    namespace = {"np": np, "struct": struct, "zlib": zlib, "Path": Path}
    exec(compile(ast.Module(body=selected, type_ignores=[]), "verified_sky_io", "exec"), namespace)
    return namespace


SKY = sky_functions()


def calibration(config):
    capture = ROOT / "output/cerroblanco/reflections" / config["revision"] / "8"
    meta = json.loads((capture / "faces.json").read_text())
    validate_capture(meta)
    face = next(e for e in meta["Faces"] if e["Face"] == 4)
    image = np.asarray(Image.open(capture / face["File"]).convert("RGB"))
    observed = SKY["undisplay"](image, exposure=1)
    sky = SKY["read_exr"](ROOT / "Assets/materials/cerroblanco/sky/cerroblanco_sky.exr")
    vector = lambda name: np.array([float(v.strip()) for v in face[name].split(",")])
    u = (np.arange(512) + .5) / 256 - 1
    v = 1 - (np.arange(512) + .5) / 256
    direction = vector("Forward") + u[None, :, None] * vector("Right") + v[:, None, None] * vector("Up")
    direction /= np.linalg.norm(direction, axis=-1, keepdims=True)
    # The courtyard's upward face is unobstructed sky. Match its known EXR
    # radiance instead of assuming that RenderToBitmap applied its exposure.
    x = np.mod(-np.arctan2(direction[..., 1], direction[..., 0]) / (2*np.pi), 1) * sky.shape[1]
    y = (.5 - np.arcsin(direction[..., 2]) / np.pi) * sky.shape[0]
    expected = sky[np.clip(y.astype(int), 0, sky.shape[0]-1), x.astype(int) % sky.shape[1]]
    center = np.s_[64:-64, 64:-64]
    channels = np.median((expected / np.maximum(observed, 1e-6))[center].reshape(-1, 3), axis=0)
    scale = float(np.median(channels))
    spread = float(np.max(np.abs(channels / scale - 1)))
    if spread > .12 or not .05 < scale < 8:
        raise ValueError(f"Sky calibration disagrees across channels: {channels}")
    report = {"radiance_scale": scale, "channel_scales": channels.tolist(), "max_channel_deviation": spread}
    (capture.parent / "calibration.json").write_text(json.dumps(report, indent=2))
    return scale


def reconstruct(capture, entries, scale):
    assert len(entries) == 1, "Expected one verified camera capture per face"
    encoded = np.asarray(Image.open(capture / entries[0]["File"]).convert("RGB"), np.float32) / 255
    assert encoded.shape == (512, 512, 3)
    return SKY["undisplay"](encoded * 255, exposure=1) * scale, {
        "clipped_fraction": float((encoded.max(axis=-1) >= .995).mean()),
        "unique_colors": len(np.unique(encoded.reshape(-1, 3), axis=0))}


def validate_capture(metadata):
    assert "ACES" in metadata["Encoding"] and metadata.get("CaptureSize") == "512,512"
    assert metadata.get("ScreenSpaceOcclusion") is False, "Exclude view-dependent screen-space occlusion from the cube"
    assert len(metadata["Faces"]) == 6
    assert {e["Face"] for e in metadata["Faces"]} == set(range(6))
    for face in metadata["Faces"]:
        assert face.get("FieldOfView") == 90 and face.get("CaptureSize") == "512,512", "Recapture all faces with the fixed projection"
        assert face.get("Position") == metadata["Position"], "Cube faces must share the probe origin"


def panorama(index, config, scale):
    revision = config["revision"]
    capture = ROOT / "output/cerroblanco/reflections" / revision / str(index)
    metadata = json.loads((capture / "faces.json").read_text())
    assert metadata["Name"] == config["reflection_names"][index]
    validate_capture(metadata)
    h, w = 1024, 2048
    lat = (.5 - (np.arange(h, dtype=np.float32) + .5) / h) * np.pi
    lon = -(np.arange(w, dtype=np.float32) + .5) / w * 2 * np.pi
    directions = np.stack(np.broadcast_arrays(np.cos(lat[:, None]) * np.cos(lon),
                                              np.cos(lat[:, None]) * np.sin(lon),
                                              np.sin(lat[:, None])), axis=-1)
    best = np.full((h, w), -1, np.float32)
    result = np.zeros((h, w, 3), np.float32)
    diagnostics = []
    for face in range(6):
        entries = [entry for entry in metadata["Faces"] if entry["Face"] == face]
        image, check = reconstruct(capture, entries, scale)
        diagnostics.append({"face": face, **check})
        meta = entries[0]
        vector = lambda name: np.array([float(v.strip()) for v in meta[name].split(",")], np.float32)
        forward, right, up = map(vector, ["Forward", "Right", "Up"])
        denominator = directions @ forward
        selected = denominator > best
        safe = np.maximum(denominator, 1e-5)
        size = image.shape[0]
        u = np.clip(((directions @ right) / safe + 1) * size / 2 - .5, 0, size - 1)
        v = np.clip((1 - (directions @ up) / safe) * size / 2 - .5, 0, size - 1)
        x, y = u.astype(np.int32), v.astype(np.int32)
        x1, y1 = np.minimum(x + 1, size - 1), np.minimum(y + 1, size - 1)
        a, b = (u - x)[..., None], (v - y)[..., None]
        color = (image[y, x] * (1 - a) + image[y, x1] * a) * (1 - b) + (image[y1, x] * (1 - a) + image[y1, x1] * a) * b
        result[selected], best[selected] = color[selected], denominator[selected]
    assert np.isfinite(result).all() and best.min() > .5
    relative = Path("materials/cerroblanco/reflections") / revision
    output = ROOT / "output/cerroblanco/stage" / relative
    output.mkdir(parents=True, exist_ok=True)
    write_exr(output / f"reflection_{index}.exr", result)
    # Display-only preview; the asset retains linear values from the camera.
    preview = result / (1 + result)
    preview = np.where(preview <= .0031308, preview * 12.92, 1.055 * preview ** (1 / 2.4) - .055)
    Image.fromarray(np.clip(preview * 255, 0, 255).astype(np.uint8)).save(capture / "panorama.png")
    path = (relative / f"reflection_{index}.exr").as_posix()
    (output / f"reflection_{index}.vmat").write_text(
        '"Layer0"\n{\n shader "shaders/sky.shader"\n F_TEXTURE_FORMAT2 "6"\n'
        ' g_flBrightnessExposureBias "0"\n g_flRenderOnlyExposureBias "0"\n'
        f' SkyTexture "{path}"\n}}\n', encoding="utf-8")
    report = {"index": index, "name": metadata["Name"], "radiance_max": float(result.max()),
              "size": [w, h], "faces": diagnostics}
    (capture / "conversion.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("index", nargs="?", type=int)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    indices = range(len(config["reflection_names"])) if args.index is None else [args.index]
    scale = calibration(config)
    reports = [panorama(index, config, scale) for index in indices]
    relative = Path("materials/cerroblanco/reflections") / config["revision"]
    stage = ROOT / "output/cerroblanco/stage"
    files = [{"path": p.relative_to(stage).as_posix(), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
             for p in sorted((stage / relative).iterdir()) if p.suffix in {".exr", ".vmat"}]
    (ROOT / "output/cerroblanco/reflection-manifest.json").write_text(
        json.dumps({"revision": config["revision"], "capture_encoding": "ACES inverse with sky calibration",
                    "radiance_scale": scale, "captures": reports, "files": files}, indent=2))
    print(json.dumps(reports, indent=2))


if __name__ == "__main__":
    main()

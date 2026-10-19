"""Fetch Belltower's CC0 scan sources; material creation and scene edits run inside s&box.

The manifest records the original API response, authors, licenses and checksums.
Run from the project with: rtk python Tools/belltower_quality_sources.py
"""
from pathlib import Path
import hashlib
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Assets/materials/belltower/scans"
PROVENANCE = ROOT / "Sources/Belltower/scans"
SOURCES = {
    "qwantani_afternoon_puresky": ("hdri",),
    "kloppenheim_05_puresky": ("hdri",),
    "medieval_blocks_03": ("Diffuse", "nor_gl", "Rough", "AO", "Displacement"),
    "stone_wall_03": ("Diffuse", "nor_gl", "Rough", "AO", "Displacement"),
    "medieval_blocks_05": ("Diffuse", "nor_gl", "Rough", "AO"),
    "white_plaster_rough_01": ("Diffuse", "nor_gl", "Rough", "AO"),
    "painted_plaster_wall": ("Diffuse", "nor_gl", "Rough", "AO"),
    "clay_roof_tiles": ("Diffuse", "nor_gl", "Rough", "AO", "Displacement"),
}


def request(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={
        "User-Agent": "BelltowerVisualPass/1.0 (local CC0 game-asset import)"
    }), timeout=60)


def fetch_json(url, path):
    if not path.exists():
        with request(url) as response:
            data = response.read()
        path.write_bytes(data)
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    with path.open("rb") as file:
        return hashlib.file_digest(file, "md5").hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    PROVENANCE.mkdir(parents=True, exist_ok=True)
    manifest = {"license": "CC0-1.0", "license_url": "https://polyhaven.com/license", "assets": []}
    for ident, channels in SOURCES.items():
        info = fetch_json(f"https://api.polyhaven.com/info/{ident}", PROVENANCE / f"{ident}-info.json")
        files = fetch_json(f"https://api.polyhaven.com/files/{ident}", PROVENANCE / f"{ident}-files.json")
        record = {"id": ident, "source": f"https://polyhaven.com/a/{ident}", "authors": info.get("authors"),
                  "dimensions_mm": info.get("dimensions"), "files": {}}
        for channel in channels:
            # Keep the HDR dynamic range and OpenGL normals; s&box's complex shader expects +Y normal maps.
            formats = files[channel]["4k"]
            extension = "exr" if channel == "hdri" else ("png" if "png" in formats else "jpg")
            remote = formats[extension]
            name = f"{ident}_{channel.lower()}_4k.{extension}"
            path = OUT / name
            if not path.exists() or digest(path) != remote["md5"]:
                partial = path.with_suffix(path.suffix + ".part")
                with request(remote["url"]) as response, partial.open("wb") as file:
                    while chunk := response.read(1024 * 1024):
                        file.write(chunk)
                if digest(partial) != remote["md5"]:
                    raise RuntimeError(f"Checksum mismatch: {name}")
                partial.replace(path)
            record["files"][channel] = {"path": path.relative_to(ROOT / "Assets").as_posix(), "md5": remote["md5"],
                                         "source": remote["url"], "bytes": path.stat().st_size}
            print(f"Ready {name}: {path.stat().st_size / 1048576:.1f} MiB", flush=True)
        manifest["assets"].append(record)
        (PROVENANCE / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

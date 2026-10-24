"""Stage sixteen woodland silhouettes on eight sectors, preserving every vertex.

Only original texture coordinates and their face indices change. This never
writes Assets or the saved scene; native import and review are separate steps.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "output/belltower/quality/forest-shapes-v1"
CACHE = ROOT / "output/belltower/quality/parcel-v4-forest/crowns.npy"
RESOURCE = "models/maps/belltower/forest/shapes-v1"
MATERIAL_DIR = "materials/belltower/forest/shapes-v1"
SECTORS = tuple((x, y) for x in range(-4, 0) for y in (-1, 0))
KIND_ROWS = {0: 0, 1: 1, 8: 2, 5: 3}  # OAK, HOLM, BEECH, WILLOW in vista_paint.


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def slot_indices(crowns: np.ndarray) -> np.ndarray:
    seed = np.floor(crowns[:, 11] * 65536).astype(np.uint64)
    with np.errstate(over="ignore"):
        value = (seed ^ (seed >> np.uint64(16))) * np.uint64(0x9E3779B185EBCA87)
        value ^= value >> np.uint64(29)
    rows = np.array([KIND_ROWS[int(kind)] for kind in crowns[:, 6]], dtype=np.int32)
    return rows * 4 + (value & np.uint64(3)).astype(np.int32)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    accepted = json.loads((ROOT / "output/belltower/quality/parcel-v4-forest/manifest.json").read_text(encoding="utf-8"))
    assert sha(ROOT / "Tools/belltower_quality_forest.py") == accepted["generator_sha256"]
    assert sha(ROOT / "Sources/Belltower/landscape/forest.json") == accepted["source_group_sha256"]
    atlas = ROOT / "Sources/Belltower/generated/forest-trees-v2.png"
    atlas_record = ROOT / "Sources/Belltower/generated/forest-trees-v2.json"
    source = json.loads(atlas_record.read_text(encoding="utf-8"))
    assert source["selected_sha256"] == sha(atlas) and len(source["regions"]) == 16
    assert source["source_pixels_and_alpha_unchanged"]
    rectangles = [r["uv_rect_top_down"] for r in source["regions"]]
    uv_lines = []
    for left, top, right, bottom in rectangles:
        assert 0 <= left < right <= 1 and 0 <= top < bottom <= 1
        for flip in (False, True):
            points = [(left, 1-bottom), (right, 1-bottom), (right, 1-top), (left, 1-top)]
            if flip:
                points = [(left+right-u, v) for u, v in points]
            uv_lines += [f"vt {u:.9f} {v:.9f}" for u, v in points]

    files, overrides, sectors, inputs = [], [], [], [Path(__file__), CACHE, atlas, atlas_record]

    def stage(relative: str, content: str | bytes) -> Path:
        path = OUT / "Assets" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
        live = ROOT / "Assets" / relative
        assert not live.exists() or sha(live) == sha(path), f"Use a new revision for {relative}"
        files.append({"path": relative, "source": path.relative_to(ROOT).as_posix(), "sha256": sha(path)})
        return path

    template_path = ROOT / "Assets/materials/belltower/forest/trials/forest_coverage_v1.vmat"
    template = template_path.read_text(encoding="utf-8")
    assert template.count('g_flCanopyMipCompensation "1"') == 1
    control = template.replace('g_flCanopyMipCompensation "1"', 'g_flCanopyMipCompensation "0"')
    stage(f"{MATERIAL_DIR}/forest_control.vmat", control)
    assert control.count('TexturePlants "materials/belltower/forest/forest-trees-v1.png"') == 1
    candidate = control.replace('TexturePlants "materials/belltower/forest/forest-trees-v1.png"', f'TexturePlants "{MATERIAL_DIR}/forest-trees-v2.png"')
    stage(f"{MATERIAL_DIR}/forest_trees.vmat", candidate)
    stage(f"{MATERIAL_DIR}/forest-trees-v2.png", atlas.read_bytes())
    inputs += [template_path, ROOT / "Assets/shaders/belltower_forest_coverage_trial.shader",
               ROOT / "Assets/shaders/belltower_forest.shader", ROOT / "Sources/Belltower/landscape/forest.json",
               ROOT / "Assets/scenes/maps/Belltower/belltower.scene", ROOT / "Tools/belltower_quality_forest.py",
               ROOT / "Tools/belltower_vista_paint.py", ROOT / "output/belltower/quality/parcel-v4-forest/manifest.json",
               ROOT / "Sources/Belltower/generated/forest-trees-v1.png"]
    crowns = np.load(CACHE)
    assert crowns.shape == (320000, 12) and np.isfinite(crowns).all()
    sector_ids = np.floor(crowns[:, :2] / 12000).astype(np.int32)
    all_counts = np.zeros(16, dtype=np.int64)
    for x, y in SECTORS:
        selected = crowns[np.all(sector_ids == (x, y), axis=1)]
        assert len(selected)
        name = f"belltower_forest_{x+8:02}_{y+8:02}"
        old_resource = f"{accepted['resource']}/{name}"
        old_obj = ROOT / "Assets" / (old_resource + ".obj")
        old_vmdl = ROOT / "Assets" / (old_resource + ".vmdl")
        old_mtl = ROOT / "Assets" / (old_resource + ".mtl")
        inputs += [old_obj, old_vmdl, old_mtl]
        lines = old_obj.read_text(encoding="utf-8").splitlines()
        vertex_lines = [line for line in lines if line.startswith("v ")]
        normal_lines = [line for line in lines if line.startswith("vn ")]
        faces = [line for line in lines if line.startswith("f ")]
        vertices = np.fromstring(" ".join(line[2:] for line in vertex_lines), sep=" ").reshape(-1, 4, 3)
        assert len(vertices) == len(selected) and len(faces) == len(selected)*2
        assert len([line for line in lines if line.startswith("vt ")]) == 32
        assert normal_lines == ["vn 0 1 0"]
        # Independently bind cache row order to the actual accepted OBJ quads.
        height = selected[:, 4] + selected[:, 5]
        assert np.allclose(-(vertices[:, 0, 0]+vertices[:, 1, 0])/2, selected[:, 0], atol=.0011, rtol=0)
        assert np.allclose((vertices[:, 0, 2]+vertices[:, 1, 2])/2, selected[:, 1], atol=.0011, rtol=0)
        assert np.allclose(vertices[:, 0, 1], selected[:, 2]-height*.025, atol=.0011, rtol=0)
        assert np.allclose(vertices[:, 2, 1]-vertices[:, 0, 1], height, atol=.0011, rtol=0)
        slots = slot_indices(selected)
        counts = np.bincount(slots, minlength=16)
        all_counts += counts
        new_faces = []
        for index, slot in enumerate(slots):
            flip = int(selected[index, 11] % 2 < 1)
            first_uv = (int(slot)*2+flip)*4+1
            first_vertex = index*4+1
            for offset, expected in enumerate(((0, 1, 2), (0, 2, 3))):
                tokens = [token.split("/") for token in faces[index*2+offset].split()[1:]]
                assert [int(t[0]) for t in tokens] == [first_vertex+k for k in expected]
                assert [t[2] for t in tokens] == ["1", "1", "1"]
                new_faces.append("f " + " ".join(f"{t[0]}/{first_uv+k}/{t[2]}" for t, k in zip(tokens, expected)))
        body, inserted = [], False
        for line in lines:
            if line.startswith("vt "):
                if not inserted:
                    body.extend(uv_lines)
                    inserted = True
            elif not line.startswith("f "):
                body.append(line)
        text = "\n".join(body+new_faces)+"\n"
        assert [line for line in text.splitlines() if line.startswith(("v ", "vn "))] == [line for line in lines if line.startswith(("v ", "vn "))]
        stage(f"{RESOURCE}/{name}.obj", text)
        stage(f"{RESOURCE}/{name}.mtl", old_mtl.read_bytes())
        vmdl = old_vmdl.read_text(encoding="utf-8")
        assert vmdl.count(old_resource+".obj") == 1
        assert vmdl.count('to = "materials/belltower/forest/forest_trees.vmat"') == 1 and "Physics" not in vmdl
        vmdl = vmdl.replace(old_resource+".obj", f"{RESOURCE}/{name}.obj")
        vmdl = vmdl.replace('to = "materials/belltower/forest/forest_trees.vmat"', f'to = "{MATERIAL_DIR}/forest_trees.vmat"')
        stage(f"{RESOURCE}/{name}.vmdl", vmdl)
        overrides.append({"original": old_resource+".vmdl", "candidate": f"{RESOURCE}/{name}.vmdl"})
        sectors.append({"sector": [x, y], "cards": len(selected), "triangles": len(faces),
                        "vertex_and_normal_lines_exact": True, "variant_counts": counts.tolist()})
    # This west-facing strip contains oak and holm oak, not every species in the
    # full 320,000-card forest. Preserve that ecology rather than inserting new kinds.
    active_rows = sorted(set(np.flatnonzero(all_counts)//4))
    for row in active_rows:
        assert np.all(all_counts[row*4:row*4+4] > 0)
    inputs = list(dict.fromkeys(inputs))
    manifest = {"revision": "forest-shapes-v1", "state": "staged; native import and appearance pending",
                "files": files, "model_overrides": overrides, "sectors": sectors,
                "source_sha256": {p.relative_to(ROOT).as_posix(): sha(p) for p in inputs},
                "cards": int(all_counts.sum()), "triangles": int(all_counts.sum()*2), "changed_sectors": len(SECTORS),
                "variant_counts": all_counts.tolist(), "available_silhouettes": 16,
                "silhouettes_used_in_bounded_trial": int(np.count_nonzero(all_counts)), "source_pixels_and_alpha_unchanged": True,
                "all_vertex_positions_normals_and_vertex_topology_preserved": True,
                "new_colliders": 0, "additional_draw_materials_per_sector": 0,
                "control_material": f"{MATERIAL_DIR}/forest_control.vmat", "candidate_material": f"{MATERIAL_DIR}/forest_trees.vmat",
                "shared_mip_compensation": 0, "canopy_brightness": 1, "accepted_assets_written": False, "native_verified": False,
                "scope": "Eight-sector silhouette/UV study. All accepted card positions, sizes, species and counts are retained. The atlas supplies sixteen distinct silhouettes; this oak/holm-oak strip uses eight of them. Both comparison materials hold the previously tested coverage strength at zero. Native mip behavior, appearance, boundary continuity and performance remain unverified."}
    (OUT / "manifest.json").write_text(json.dumps(manifest, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({"staged_files": len(files), "cards": manifest["cards"], "variant_counts": all_counts.tolist(),
                      "vertices_preserved": True, "accepted_assets_written": False, "native_verified": False}))


if __name__ == "__main__":
    main()

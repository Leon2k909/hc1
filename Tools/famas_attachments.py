"""Decompile the locally installed FAMAS attachment models used by the weapon pipeline."""
from pathlib import Path
import subprocess
import numpy as np
from kastov_smd import Smd, write_smd, matrix, euler_to_mat

TOOLS = Path(r"D:/tmp/hc1-mw22-tools")
SOURCE = TOOLS / "extracted/2528829149/models/viper/mw/attachments/falpha"
OUTPUT = TOOLS / "decompiled/falpha"


def main():
    for model in sorted(SOURCE.glob("*.mdl")):
        folder = OUTPUT / model.stem
        if not (folder / (model.stem + ".qc")).is_file():
            folder.mkdir(parents=True, exist_ok=True)
            result = subprocess.run([str(TOOLS / "CrowbarCommandLineDecomp.exe"), "-p", str(model), "-o", str(folder)],
                                    capture_output=True, text=True, timeout=120)
            if result.returncode or not (folder / (model.stem + ".qc")).is_file():
                raise RuntimeError(f"Decompile failed: {model}\n{result.stdout[-2000:]}\n{result.stderr[-1000:]}")
        print(model.stem + ": " + ", ".join(p.name for p in sorted(folder.glob("*.smd"))))
    # The low rail's charging assembly uses differently named bones. Bind it to the original charging handle
    # while retaining its authored rest positions, so the existing FAMAS reloads drive the replacement too.
    reference = Smd(OUTPUT / "v_falpha/attachment_vm_ar_falpha_receiver.smd")
    rail = Smd(OUTPUT / "attachment_vm_ar_falpha_railcust/attachment_vm_ar_falpha_railcust.smd")
    ref_world = reference.world(reference.dense_frames()[0])
    source_world = rail.world(rail.dense_frames()[0])
    mount = ref_world[reference.index("tag_rail_attach")] @ np.linalg.inv(source_world[rail.index("tag_rail_attach")])
    triangles = []
    for material, vertices in rail.triangles:
        converted = []
        for position, normal, uv, links in vertices:
            weights = [(reference.index("j_charging_handle" if rail.name(bone).startswith("j_charging_")
                                         else "tag_rail_attach"), weight) for bone, weight in links]
            converted.append((mount[:3,:3] @ position + mount[:3,3], mount[:3,:3] @ normal, uv, weights))
        triangles.append((material, converted))
    derived = OUTPUT / "derived"
    derived.mkdir(exist_ok=True)
    frame = reference.dense_frames()[0]
    locals_ = [matrix(frame[i][0], euler_to_mat(*frame[i][1])) for i in range(len(reference.nodes))]
    write_smd(derived / "low_rail.smd", reference.nodes, [locals_], triangles)


if __name__ == "__main__":
    main()

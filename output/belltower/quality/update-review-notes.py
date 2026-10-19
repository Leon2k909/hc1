"""Apply only Belltower's verified review notes to the current shared document."""
from pathlib import Path
import os

path = Path("CLAUDE.md")
original = path.read_bytes()
text = original.decode("utf-8")
newline = "\r\n" if "\r\n" in text else "\n"
text = text.replace("\r\n", "\n")
edits = [
    ("Garden props v1 (2026-10-15) is imported and natively compiled; native review found a trim overlap to fix.",
     "Garden props v2 (2026-10-15) is imported, natively compiled and reviewed as an incremental quality pass."),
    ("the two town meshes are fully staged in `models/garden-v2/`", "the two town meshes are installed from `models/garden-v2/`"),
    ("""    all three v1 sheds and accepts v2. Two offline construction views are in `garden-v2-studio/`. Native import and
    review await the next coordinated editor window. `garden-v1-checkpoint.json` records the rejected overlap;
    no garden acceptance manifest has been
    written yet. Do not restore the older facade models over these changes. `garden-import-request.json` selects""",
     """    all three v1 sheds and accepts v2. Two offline construction views are in `garden-v2-studio/`; seven matching
    native views are in `garden-v2-saved/`. `Sources/Belltower/gardens/manifest.json` and
    `garden-v2-saved/verification.json` record the accepted sources, native compiles and unchanged scene/collision.
    The shed edge artifacts are resolved. Firewood still needs less faceted profiles and convincing bark/cut faces;
    the wheelbarrow chassis partly enters its basin and needs lowering. These remain open quality issues.
    `garden-v1-checkpoint.json` records the rejected overlap. Do not restore the older facade models over these
    changes. `garden-import-request.json` selects"""),
    ("""    viewport camera. A hidden tab can have no `Scene.Camera` while another map is playing. It records the actual
    camera exposure and preserves the selected document and game state while restoring its camera transform.""",
     """    viewport camera. A hidden tab can have no `Scene.Camera` while another map is playing. It records the requested
    camera exposure settings and preserves the selected document and game state while restoring its camera transform."""),
    ("""    component and camera settings. `look-v1-plan.json` records the pending ACES/AgX and lower-exposure comparisons
    against the pale street captures. These settings have not been applied to the saved scene or reviewed natively.""",
     """    component and camera settings. Eleven native images in `look-v1-*` were reviewed: AgX visibly improves the pale
    surfaces, but exposure bounds and compensation produced nearly identical pixels despite changed camera metadata.
    `look-v1-review.json` records matched cameras, pixel differences, exact component restoration and the unchanged
    saved scene. Effective rendered exposure remains unverified; do not treat metadata as proof. Local engine IL
    shows editor rendering can copy post-processing from `Scene.Camera` again, and native tone-map parameters cross
    into the renderer; the cause is not confirmed. Inspect both cameras/native settings and use a deliberately
    separated fixed-exposure comparison in the next coordinated window. No look changes have been saved."""),
]
for before, after in edits:
    assert text.count(before) == 1, "Review note anchor changed; read the shared file again"
    text = text.replace(before, after)
staged = path.with_name("CLAUDE.belltower-review-incoming")
staged.write_bytes(text.replace("\n", newline).encode("utf-8"))
assert path.read_bytes() == original, "Concurrent edit detected; preserve the new shared file"
os.replace(staged, path)
print("Updated five Belltower review notes; preserved all other current content.")

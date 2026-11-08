# Veridant courtyard drains — rejected; removed entirely, 2026-11-06

The user rejected the drain placement itself and requested continuous courtyard
paving. All four drains, their render import and generation calls are removed.
The original flat strips were already removed from the active ground base; the
replacement cover import is now removed too. Paving and collision remain intact.
Do not reinstall these drains or regenerate their historical patch. The following
notes and captures are retained only as superseded review history.

Four flat grating strips are replaced with slim bevelled metal perimeter frames,
removable cover panel joints, individual cross bars, lower centre ties and small
fasteners. Uses the existing Spillway trench-grate steel/frame/dark/bolt material
set, adapted to Veridant's narrow covers. A dark backing masks the existing floor
through the slots; no ground excavation is claimed.

All vertices stay within the original 5.9-inch overall widths and original lengths.
Maximum rise is 0.245 inches (about 6.2 mm). Original floor collision and the full
ModelDoc physics suffix are unchanged. Exactly 24 original triangles are removed;
22,094 new triangles are imported. The original vertex/UV/normal tables and every
unrelated face are retained. Two empty old material-group declarations were removed
because the OBJ importer rejected the empty groups after the drain faces were removed.

The source is Tools/veridant_courtyard_drains.py. A narrow veridant_parts.drain
hook retains the four covered placements; veridant_map.configure preserves their
explicit existing-material overrides. All other geometry, scene settings, lighting
and the earlier accepted upgrades are unchanged.

build.py stages; prepare_import.py imports through native editor with parent/base
guards; verify.py checks finite/unit data, nondegenerate triangles, original
footprint/rise limits, preserved tables/faces and exact physics suffix. Native
compilation succeeded after the empty-group correction. The temporary failed
capture with a missing floor is not used as review evidence.

Actual displayed editor viewport frames with the same existing camera/settings:
output/veridant/courtyard-drains-v1/before.png and after.png. No temporary camera,
isolated scene, RenderToBitmap or exposure/lighting changes. Stage and rollback
snapshots remain in that output directory; historical stages must not overwrite
newer work without an explicit baseline refresh.

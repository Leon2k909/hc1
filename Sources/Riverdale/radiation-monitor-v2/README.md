# Riverdale ARM-04 monitor

`Tools/riverdale_radiation_monitor.py` contains the geometry and dedicated instrument artwork.
`riverdale_hall.radiation_monitor` calls it for all eleven existing placements. These are static
decorative instruments; the 0.12 µSv/h display is artwork, and the buttons have no interaction.

The housing retains the original 14 × 10 inch footprint and approximately five inch projection.
Changes include a chamfered painted enclosure, lid gasket, front plate, captive screws, recessed
LCD with a dose readout, two collared pilot lights, two buttons, serial plate, cable glands,
Fresnel beacon and a separately mounted enamel identification plate. The materials use the
engine's complex shader, with restrained self illumination and dedicated panel textures.

`build.py` stages an exact face subtraction/addition against the published hall OBJ files. It
refuses any missing legacy face and checks that all unrelated faces remain identical. It does
not rebuild the map or alter scene JSON or collision. The original eleven monitors account for
110 detail triangles and 330 fine triangles. Their replacements use 36,894 detail triangles and
242 fine triangles in total (about 3,376 triangles per instrument, including all fixings).

The running editor retained a stale fine mesh during the first compile. A temporary fresh
import filename evicted it, after which the model was rebound and force-compiled against the
canonical `riverdale_hall_fine.obj`. Both original model resource paths and source paths remain
in use, so later hall edits continue to reach the same assets.

The one-time migration and its backups are in `output/riverdale/radiation-monitor-v2`.
`stage.json` records hashes before and after import. Install scripts run inside the native editor
from its session exchange directory and use atomic file replacement because source files may
be memory-mapped. `compile.cs.txt` registers and force-compiles the eight materials and two
hall models. `capture-before.cs.txt` and `capture-after.cs.txt` clone the map's visual roots into
an isolated editor scene and destroy it afterward, retaining the user's scene and play state.

Do not rerun the legacy migration on an already migrated mesh: it deliberately refuses it.
For further edits, capture the installed monitor geometry as the baseline and splice only the
new monitor geometry. Do not publish a full hall regeneration over unrelated asset work.

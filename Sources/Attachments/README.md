# HC1 attachment art

Four original game-art models: Rifle Suppressor, Compact Suppressor, Vertical Grip,
and Angled Grip. They appear in the M4A1 and SCAR-H gunsmith under Barrel and
Underbarrel. Existing attachments and loadout cookies are preserved.

## Files

- `hc1_attachments.blend`: editable source, four named collections at their mounting
  origins, with the generated atlas packed into the file. Hide the other collections
  when editing a part. No lights or preview staging are included in the source file.
- `../../Assets/attachments/hc1/`: exported OBJ meshes, MTL files, ModelDoc VMDLs,
  four material definitions and the original generated color atlas.
- `../../Assets/gunsmith/hc1/`: prefab and gunsmith resource for each part.
- `qa/attachment-lineup.png`: Blender render of the actual modeled geometry.
- `texture-prompt.txt`: exact prompt used with the built-in imagegen tool.

The original imagegen output is 1254 x 1254 pixels. Its quadrants contain anodized
aluminum, polymer, steel and ceramic coating. UVs stay within their material quadrant
with a 2% atlas gutter (about 25 pixels). Each material shares this color map and has
its own metalness and roughness values. Normal and AO inputs use engine defaults;
clamps, lips, ribs, collars, end caps and fasteners are modeled geometry.

These are cosmetic game meshes, with no functional internals or manufacturing data.
They use the game's existing attachment effects; this pack introduces no new recoil,
damage, ammunition or unlock-balance rules.

## Rebuild

From the project root, with Blender 5.x on PATH:

```powershell
rtk proxy blender --background --threads 6 --python Sources/Attachments/build_attachments.py
rtk proxy python Sources/Attachments/install_gunsmith_parts.py
rtk proxy python Sources/Attachments/validate_attachments.py
```

Add `-- --skip-render` to the Blender command to export without rendering the lineup.
The installation script is idempotent and only adds missing selection points to the
M4A1/SCAR-H view and world prefabs. It recreates this pack's resource definitions.

The Blender source uses +X forward, +Z up, in Source game units. The OBJ writer
explicitly counters ModelDoc's OBJ axis conversion; compiled VMDL bounds are verified
against the Blender mesh bounds. Do not apply a second axis rotation in ModelDoc.

## Placement and validation

`GunsmithSocketAttachment` follows the animated renderer's muzzle socket; static
world models without a socket use the existing WeaponModel muzzle object. Its
offset positions grips on the rail. Model-specific socket rotation corrections keep
SCAR-H attachments upright. Floating gunsmith buttons remain selection anchors.

Validation checks finite vertices, unit normals, nonzero triangle areas, padded UVs,
triangle counts and prefab/material/model resource paths. The final triangle counts
are recorded in `qa/validation.json`.

The editor's `hc1_attachment_audit` command checks loaded models.
`hc1_attachment_preview m4a1 false false` renders a temporary cloned weapon with the
rifle suppressor and vertical grip. Arguments are weapon (`m4a1`/`scarh`), world-model
flag, and compact-set flag (compact suppressor + angled grip). The temporary scene
is destroyed after rendering and does not change the open scene or player cookies.
Use `hc1_attachment_refresh` after adding the component to an already-running editor
if it imported the prefabs before the C# type was available.

`hc1_attachment_fit_matrix` renders both weapons in view and world configurations,
using rifle suppressor/vertical grip for view models and compact suppressor/angled
grip for world models. It also exercises equip, unequip and re-equip, including
initialization while a world-model root is disabled. Close image previews before
rerunning: Windows may prevent overwriting an image while a viewer holds it open.

The September 22, 2026 verification passed mesh/resource validation, loaded all four
compiled models and their materials, and completed all four engine preview cases.
The Code and Editor build completed with zero errors (existing warnings remain).
See `qa/validation.json`, `qa/build.log`, and `qa/engine-validation.log` for evidence.
The final visually inspected engine captures are:

- `qa/m4a1-view-rifle-verified.png`
- `qa/m4a1-world-compact-verified.png`
- `qa/scarh-view-rifle-verified.png`
- `qa/scarh-world-compact-verified.png`

These checks use isolated engine scenes; a full multiplayer gameplay playtest has
not been performed. Files ending in `-fit.png` are earlier calibration captures.

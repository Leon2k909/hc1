from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent
p=HERE/'build.py';s=p.read_text();a=s.index('def stage_base():');b=s.index("if __name__",a)
s=s[:a]+'''def main():
    MODEL.mkdir(parents=True,exist_ok=True)
    lods=[K.write_obj(MODEL/f'lantern_lod{i}.obj',build(i),f'lantern_lod{i}') for i in range(3)]
    (MODEL/'wall_lantern.vmdl').write_text(modeldoc())
    print(json.dumps({'lods':lods,'accepted_resource_staged':True,'original_asset_preserved':True}))

'''+s[b:];p.write_text(s)
p=HERE/'README.md';s=p.read_text().replace('— review candidate','— installed; original retained').replace('Not installed in the saved map.','Approved by the user and installed at all 24 matching wall-lantern positions (12 west, 12 east).').replace('`build.py` checks finite, nondegenerate source faces and removes exactly those 960 old triangles','The original review builder checked finite, nondegenerate source faces and removed exactly those 960 old triangles').replace('Await user approval under `CLAUDE.md` before installation.','''The user approved replacement and explicitly requested retention of the original asset because its shape was useful.
All 24 matching fixtures are now separate saved scene objects. Exactly 23,040 baked triangles were replaced
in twelve source meshes; seven affected current/historic map VMDLs and the retained original compiled.
The saved scene, physics, existing object IDs and editor/play state passed native verification.
`installed.json` records the source and state checks. Saved after evidence is `after-installed.png`.

## Retained original — keep this asset

`models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl` is the complete original
960-triangle lantern and bracket, at the same scale/reach as the review. Its local origin is the wall anchor;
local plan +E faces away from the wall. Mesh, materials, compiled model and procedural source are retained.
The resource compiles and loads successfully. No existing asset files were deleted, including review evidence.
`build_original.py` can stage the original again; `belltower_map._legacy_wall_lantern` retains its authoring code.
`build.py` now stages only the accepted new resource. Custom nonstandard scale/reach calls retain legacy behavior.
Regeneration uses `Tools/belltower_wall_lanterns.py` with stable IDs and mirrored headings.''');p.write_text(s)
p=ROOT/'docs/notes/belltower-wall-lantern-v2-review-20261104.md';s=p.read_text().replace('— pending review','— installed; original retained').replace('NOT installed. The saved map keeps the existing lantern pending the user\'s visual approval.','''The user approved the new lantern and explicitly asked to KEEP the original asset because its shape was useful.
Installed all 24 matching fixtures (12 west, 12 east) through the editor, replacing 23,040 old baked triangles
across twelve mesh sources. Seven affected map VMDLs compiled. Scene save, preserved physics/object IDs,
mirrored generator placements, editor state and matched saved after screenshots were verified.

KEEP `models/maps/belltower/wall-lantern-original/wall_lantern_original.vmdl`: this is the full original
960-triangle bracket and lantern as a reusable standalone resource, not just a screenshot or temporary backup.
Its OBJ/MTL, compiled resource and procedural source remain available; native compilation/loading passed.
No old asset files were deleted. `Sources/Belltower/wall-lantern-v2/installed.json` records the checks.
The new accepted build remains under `wall-lantern-v2`; `Tools/belltower_wall_lanterns.py` emits stable scene IDs.
`belltower_map._legacy_wall_lantern` preserves the old procedural authoring and custom scale/reach behavior.''');p.write_text(s)
p=ROOT/'CLAUDE.md';s=p.read_text().replace('Belltower wall lantern v2 (doorway model review, 2026-11-04)','Belltower wall lantern v2 (24 installed; original asset retained, 2026-11-04)');p.write_text(s)
print('Documented installation and explicit original-asset retention.')

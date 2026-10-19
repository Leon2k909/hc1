"""Update the Belltower notes atomically, preserving other chats' file contents."""
from pathlib import Path

root=Path(__file__).resolve().parents[3]
path=root/'CLAUDE.md'
original=path.read_bytes()
text=original.decode('utf-8')
newline='\r\n' if '\r\n' in text else '\n'
marker='  - The landscape pass replaces rectangular field rows with larger, warped Voronoi parcels, reduces crop-colour'
assert text.count(marker)==1
note='''  - Distant woodland v8 (2026-10-15) adds 320,000 town-facing tree cards in 88 sector meshes, 640,000 triangles.
    These are visual only, with no collision or shadow casting. The original generated RGBA tree atlas is preserved
    in `Sources/Belltower/generated/forest-trees-v1.png` with its prompt/provenance. `belltower_forest.shader` uses
    diffuse lighting and the landscape B/C/D palette and slope normals, averaged over a 128-unit crown footprint.
    Generated leaf detail modulates that colour; distance fade is 30,000-52,000 units. Single cards avoid the bright
    crossed-card seams. The v8 pass was reviewed against same-session baseline captures at the valley, west ridge
    and terrace, then saved natively. It improves the nearby canopy; the far valley still needs refinement.
    `Sources/Belltower/landscape/forest.json` is the accepted native group, and `forest-manifest.json` records its
    source/asset hashes. `belltower_map.py` includes that cache when regenerating; staging trials are excluded.
    `belltower_quality_forest.py` stages placement, models and materials. Import with `import-forest.cs.txt`, compile
    the material and verify with `verify-forest.cs.txt`. `apply-forest.cs.txt` is only for the first reviewed save;
    it refuses an existing group. Future replacements must update the existing group rather than adding another.
    `forest-v8-saved/` contains fresh saved-scene captures and the scene comparison; `audit-forest-sources.py --saved`
    verifies all 267 inputs, all 88 current compiled models, 640,000 triangles and the matching regeneration cache.
    The native save also refreshed per-process resource IDs/two prefab child mappings and wrote the new false
    ZombiesOnly default; town geometry/collision, transforms and other scene values were preserved. The v9 indirect
    light and v7 reflection assets are unchanged. Editor performance was sampled with play stopped; gameplay
    performance remains unverified and the overall AAA quality goal remains open.
'''.replace('\n',newline)
assert 'Distant woodland v8 (2026-10-15)' not in text
updated=text.replace(marker,note+marker,1)
old=('    `output/belltower/quality/landscape-v2-preview/` contains native comparisons; the distant canopy and near terrace'+newline+
     '    retaining walls still read as painted terrain and need further work for the overall quality goal.')
new=('    `output/belltower/quality/landscape-v2-preview/` contains comparisons before the woodland addition. Distant'+newline+
     '    fields and the near retaining walls still need refinement for the overall quality goal.')
assert updated.count(old)==1
updated=updated.replace(old,new,1)
temporary=path.with_name('CLAUDE.forest-v8.tmp')
temporary.write_bytes(updated.encode('utf-8'))
assert path.read_bytes()==original, 'CLAUDE.md changed during preparation; retry from its current content.'
temporary.replace(path)
print('Recorded accepted forest v8 and remaining visual/performance work.')

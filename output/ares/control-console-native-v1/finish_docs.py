from pathlib import Path
r=Path(__file__).absolute().parents[3]
text='''# Riverside T2 sliding-window frame — installed 2026-11-05

User approved the new frame. Installed `models/props/riverside/sliding_window_v1/window.vmdl` at engine `995,820,76`. Deleted exactly 14 original aluminium frame/sill faces from the lowland mesh and retired obsolete private preview resources. Original lit pane positions, artwork UVs, emission and physics remain unchanged.

Rounded mounting extrusion, offset sashes, seals, latch, tracks/weep slots and formed drip sill use existing Riverside finishes. LODs: 2,586 / 1,970 / 866 triangles; thresholds 0/25/70. No added collision, lights or textures.

`Tools/riverside_sliding_window.py` places the approved prop. Narrow optional hooks in `riverside_parts.py` and `riverside_map.py` suppress only T2's central south-side frame/sill, retaining its pane. No full map regeneration was performed.

`build.py` reproduces approved frame assets. `verify.py` checks hashes, attributes, winding, bounds, references and placement. Installation receipts in `output/riverside/sliding-window-v1/` record exact cut scope, unchanged unrelated lines and physics. Native compilation succeeded; isolated captures checked all three LODs and player floor, preserving editor/play state. No frame-time benchmark claimed.

`install.cs.txt` is a historical one-time installer. `capture_installed.cs.txt` records installed captures. Its obsolete manifest read should use build-manifest.json if replayed.
'''
(r/'Sources/Riverside/sliding-window-v1/README.md').write_text(text,encoding='utf-8')
(r/'docs/notes/riverside-sliding-window-v1-20261104.md').write_text(text,encoding='utf-8')
p=r/'CLAUDE.md';s=p.read_text(encoding='utf-8');s=s.replace('Riverside close-range T2 sliding-window frame (review candidate, 2026-11-04)','Riverside close-range T2 sliding-window frame (installed, 2026-11-05)');p.write_text(s,encoding='utf-8')

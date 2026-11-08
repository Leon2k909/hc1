# Veridant breakable railing glass

Installed 147 independently breakable railing panes using the existing
`Facepunch.BreakableGlass` component. Exact original render faces and UVs are
retained in local pane models with thin convex glass collision. Removed only
588 `vr_glass_clear` triangles from the two active aggregate render imports;
steel rails, shoes, materials and player clips are retained.

The scene was installed and saved through the native editor. Buildings and
dressing compiled successfully. All 147 panes passed glass-tagged collision
rays and the component's local break/restore state checks; all shatter prefab,
sound and intact model references were valid. This was an editor verification,
not a live gunfire or second-client multiplayer test. The actual editor
viewport was inspected without temporary cameras or changed render settings.

`Tools/veridant_breakable_rails.py` stages the exact mesh extraction and keeps
rail glass out of regenerated static exports. `Sources/Veridant/breakable-rails-v1/group.json`
preserves the installed placements in the map generator. Update that group
and regenerate pane models if the railing layout changes.

Native install/check scripts are alongside the group. Receipts and backups:
`output/veridant/breakable-rails-v1/`. Do not run the earlier install-assets
script after installation: its pre-install source hash guards will reject it.

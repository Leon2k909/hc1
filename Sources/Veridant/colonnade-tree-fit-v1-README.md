# Colonnade tree fit — 2026-11-06

Final verification after editor reopening: correct saved light position loaded,
tree centred/rooted, actual viewport capture sbox.2026.11.06.18.03.41.png copied
to after.png. The pending-capture note below is superseded. The reopened editor
had different viewport dimensions; this final image is a standalone verification.

Centered the olive on the accepted stone planter: base plan (-233,12.5,20.5),
1.5 inches below soil to conceal its cut bottom. Moved the uplight lens to
(-244,-1,22.1), clear of the trunk, with its point light at world (-1,244,46.1).
Matched and translated exactly 526 tree triangles and eight lens triangles;
unrelated source records, UVs and physics unchanged. Guarded native import
persisted the model. Actual live viewport after.png is under
output/veridant/colonnade-tree-fit-v1/ and shows centered rooted tree/clear lens.

The editor closed during final saving. Point-light relocation was verified live
but not saved by the interrupted call, so only its exact GUID's Position field
was persisted to the closed scene file with a guarded script. Final live capture
after that last light-position persistence remains pending editor reopening.

Original cube assembly remains models/props/shared/colonnade_planter_original_v1/planter_original.vmdl.
Bronze alternative recovered from preserved staging and compiled separately at
models/props/shared/colonnade_bronze_alternative_v1/planter.vmdl. Neither is placed
in Veridant. Existing source Reef Hall planter also remains untouched. Stone
model stays active; tree/uplight generator values match persisted changes.

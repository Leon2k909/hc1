## Boxyard southwest pallet stack — review (2026-11-04)

- User rejected this candidate: preferred the original wood texture. Keep the original active; no installation pending.

- Reuses the approved Spillway detailed pallet mesh/wood atlas, scaled to Boxyard's existing47.24×31.5×17.01-inch
  stack envelope, with three full pallets and alternate180-degree rotation. No new textures or external assets.
- Candidate only: public model/generator/scene unchanged. Replaces410 old faces with2,892; preserves12,468 other
  prop faces exactly, including approved pipe stacks. Other single pallet under the northwest crate unchanged.
  Original physics suffix/hulls and stack collision unchanged; the candidate adds no collider.
- Source, checks, snapshots and actual matched native renders: `Sources/Boxyard/pallet-stack-v1/`, local `review/`.
  All3 preview models compiled. Native context views load saved Boxyard visuals with only a props-model swap.
  Temporary scenes destroyed; clean Riverside document and stopped play state preserved. No performance claim.
- Persistent `--connect` script requests repeatedly timed out while editor remained responsive; direct
  `sbox-cli --call run_csharp` with the same source as `code` succeeded. `direct.py SCRIPT` implements this route.
- Acceptance should narrow-splice the selected stack and add a single generator hook/material remap, retaining
  the original wood collision. Source details and original licensing: `Sources/Spillway/cargo-props-v2/README.md`.

# Sewage gate shed lock reuse — 2026-11-04

User narrowed the gate improvement to its lock and requested reuse of the shed asset. Both tunnel gates now use the existing `Tools/belltower_padlock.py` hardware: rounded bronze case, smooth steel shackle, recessed cylinder/keyway, slotted hasp, hinge knuckles, staple and fixings. Reused the shed materials. Gate body textures were not replaced.

Integration: `Tools/sewage_tunnel_gates.py`. Guarded exact splice/build and native installation/capture scripts: `Sources/sewage/gate-shed-lock-v1/`. Baseline, plan, verification and matched native screenshots: `output/sewage/gate-shed-lock-v1/`. Native review before model: `models/maps/sewage/gate-shed-lock-v1/before.vmdl`. Active model remains `models/maps/sewage/sewage_shell.vmdl`.

Only central hardware changed: 1,368 old triangles replaced with 7,860 reused detailed hardware triangles across two gates; 13,156 unrelated triangles retained exactly. Model physics suffix and collider OBJ unchanged. No scene file or user editor/play/dirty state changes. Native compilation succeeded and close-up/full-gate screenshots were visually checked. Awaiting user review; preserved prior gate version for comparison.

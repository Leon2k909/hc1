# Sewage maintenance tunnel gates v1 (2026-11-04)

New model for both closed maintenance tunnel ends: paired arched steel grille leaves with reinforced lower panels, mirrored braces, bolted frames, barrel hinges, a slide bolt/hasp, padlock and recessed backing. One original grille had been placed behind the concrete end wall; both new gates face into their respective tunnels.

Checked existing Belltower, Veridant, Ares and Riverside gate/door models before building. No matching staged Sewage replacement was found. Installed in `models/maps/sewage/sewage_shell.vmdl` for visual review, keeping the original closed-end collision and entire ModelDoc physics suffix. All 4,180 unrelated shell triangles retain exact position, UV and normal data. No scene file, lighting, navigation or runtime logic change. Both stair variants retained.

Source and reproducible guarded integration: `Tools/sewage_tunnel_gates.py`, `Tools/sewage_map.py`, `Sources/sewage/tunnel-gates-v1/`. Baseline snapshots, model checks and matched green/red tunnel captures: `output/sewage/tunnel-gates-v1/`.

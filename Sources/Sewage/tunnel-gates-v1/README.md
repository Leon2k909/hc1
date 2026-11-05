# Sewage maintenance tunnel gates v1

A new model for the two previously crude/hidden tunnel-end grilles, created after checking the existing Belltower timber town gates, Veridant forecourt gates, Ares pressure doors and the rejected Riverside chain-link gate. Those are different gate types and do not fit these arches. No matching staged Sewage grille upgrade was found.

The replacement has paired arched steel leaves, an anchored head/jamb frame, open vertical bars, mirrored diagonal braces, reinforced kick panels, three segmented barrel hinges per leaf, a slide bolt/hasp, padlock and recessed opaque backing. Both ends use the same local construction with correct mirrored winding and hardware, placed on the tunnel-facing side of the existing end collision.

`Tools/sewage_tunnel_gates.py` builds the mesh. `Tools/sewage_map.py` calls it from `arc_tunnel` while retaining the original closed-end collision box. No animation, opening behaviour, runtime component, lighting or navmesh change is added.

Installed in the public `sewage_shell` model for visual review. The guarded splice removes exactly 864 old end-wall/bar triangles and adds 10,344 triangles across both gates. All 4,180 other shell triangles, their UVs/normals, the ModelDoc physics suffix and original hull file are retained. No whole-map rebuild or scene serialization was needed. Both old/new stair models remain available at the user's request.

Stage/snapshots/checks/renders: `output/sewage/tunnel-gates-v1/`. Native imports and captures use the local adapter `native.py`; scripts are copied into the live session exchange directory before `run_csharp`. Captures use disposable visual scenes, matching cameras and lighting, and restore/destroy them without changing the user's scene/play state.

`build.py` checks exact face preservation, finite/nondegenerate geometry, winding against shading normals and byte-identical physics suffixes. `check_installed.py` verifies installed hashes, the exact face splice, collision hull hash and retained stair variants, and prepares a capture of the actual public model. `import-revision.cs.txt` permits a known previous preview hash when iterating, while rejecting external preview edits.

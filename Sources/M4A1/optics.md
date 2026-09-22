# Additional M4 optics

The Optic slot adds **Reflex Sight**, **Patrol Red Dot** and **Scout 3x**, alongside the original Holo Sight and RMR. They are available at level 0 and apply to the M4A1 only.

- Reflex uses the existing SWB sight source, repaired normals, corrected material remaps and a neutral black housing finish.
- Patrol is a new enclosed optic with a rail clamp, raised mount, recessed lens, adjustment turrets and knurled brightness dial. It uses baked color, normal, roughness, metalness and AO maps matching the Recon attachments.
- Scout uses the existing textured hunter scope, reduced from 113,458 to 27,387 triangles, with a clear aperture, black interior baffles and a restrained illuminated crosshair. Magnification changes the player's ADS field of view by an actual 3x projection ratio relative to ordinary ADS, with matching aim sensitivity reduction. This uses full-view zoom rather than an additional render camera.

The original SWB SMD files cannot be imported by the current ModelDoc compiler. The installer converts their geometry, UVs and normals to OBJ without changing the shared SWB models/materials. Intermediate meshes live outside Assets. The game references indexed meshes grouped into material batches: Reflex has 6,805 triangles, Patrol has 22,856 housing triangles plus its separate lens, and Scout has 27,387 triangles.

Standalone optics follow the weapon's animated muzzle transform using calibrated rail offsets. The first-person and world models have different carry-handle bodygroup indices; model-specific overrides clear the correct one. Unequipping restores factory sights. The original Holo/RMR retain their existing world appearance because their geometry is embedded only in the viewmodel. Per-optic ADS offsets do not mutate the original weapon defaults. Camo colors the housing while preserving the lens, reticle and black interior baffles; Apply Camo to Optics is respected.

## Build order

```powershell
rtk python Sources/M4A1/install_optics.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/optimize_scout.py
rtk python Sources/M4A1/index_optic_meshes.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/build_optics.py
rtk proxy 'C:/Program Files/Blender Foundation/Blender 5.1/blender.exe' --background --threads 4 --python Sources/M4A1/bake_finishes.py -- --optics
rtk python Sources/M4A1/index_patrol_mesh.py
rtk python Sources/M4A1/validate_assets.py
```

These scripts reuse the existing `recon_anodized_color.png` as a baking input. `m4a1_optics.blend` contains editable Patrol geometry; `m4a1_optics_pbr.blend` retains its baked UV layout. The lens shader uses clear alpha blending, collimation and procedural dot/crosshair reticles, with optional Gunsmith reticle textures. It does not depend on a framebuffer-copy pass. The housing shader preserves donor normal/roughness detail while mapping the factory finish to black; selecting a camo texture bypasses that factory color conversion. Both shaders are authored directly under `Assets/shaders`.

The native test fixture is retained under `qa/optics/` outside normal Editor compilation. Copy it temporarily into Editor, then run `m4_optics_verify` for the eleven-case suite, or `m4_optics_qa reflex false false true` for one case (optic name: reflex/tube/scout; world model; camo; ADS pose; paint optics, default true). It checks model/material validity, clear lenses, housing camo toggle, ADS lens alignment within 0.015 units of the aim ray, factory restoration, hip-fire/default aim offsets and projection magnification. The fixture restores the active loadout cookies after each isolated test. See the validation log and screenshots in the same directory.

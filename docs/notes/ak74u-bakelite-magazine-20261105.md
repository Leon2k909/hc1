# AKS-74U standard magazine: classic Bakelite option

- Gunsmith > Build > Magazine > **30 Round Bakelite Mag** selects the factory magazine geometry with a reddish-brown resin finish. **Standard** restores black.
- `Assets/gunsmith/kastov74u/magazines/standard_bakelite.gnsmth` uses magazine bodygroup 0 and replaces only `ks74u_mag.vmat` with `ks74u_mag_bakelite.vmat`.
- `Assets/shaders/ks74u_bakelite.shader` authors the resin appearance procedurally over the original UVs, retaining the original normal map, molded detail and wear. UV regions and source metalness protect steel hardware. No generated comparison image is consumed by the game.
- `GunsmithPart.MaterialReplacements` resolves the selected part's factory material before the shared camo pass, on both view and world models. Removing the part restores the source material. Attachment thumbnails apply the same remaps.
- `IsCosmeticVariant` makes this choice available from level 1 and excludes it from the progression ladder. Capacity, reload timing, mass and all computed stats equal the standard magazine.
- Native editor validation passed: material compiled; variant was offered and unlocked; build-code application/reset passed on both view and world prefabs; all `GunsmithStats` properties matched the standard build. Evidence: `output/ak74u-bakelite/validation.json`.
- Native matching studio renders: `output/ak74u-bakelite/black-preview.png` and `bakelite-preview.png`. The option was also selected and photographed in the running gunsmith. The user subsequently changed to Belltower; the scene and play state were left alone.

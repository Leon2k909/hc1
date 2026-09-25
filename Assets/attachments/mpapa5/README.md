# MP5A5 attachment meshes

## Gunsmith integration

All 11 models are registered as level-0 MP5 Gunsmith parts under `Assets/gunsmith/mpapa5`: 4 barrels, 3 magazines, 1 rail grip, and 3 stocks. The MP5 viewmodel and world-model prefabs expose Barrel, Magazine, Underbarrel, and Stock slots. Magazines and stocks follow their corresponding weapon bones during animations.

The short, integral suppressor and monolithic suppressor barrels and the rail grip are fitted by `Tools/fit_mp5_barrels.py`. They sit on the MP5's own bore, and the MP5 keeps its own receiver, sights and bolt, cut from the stock mesh into `native_receiver/`. The script rewrites their `.vmdl` files without bodygroups, and their prefabs and gunsmith parts. See the script for details.

The public [Black MP5 skin](https://steamcommunity.com/sharedfiles/filedetails/?id=2811134327) supplies material overrides. Its geometry comes from [Modern Warfare 2019 SWEPS – Submachine Guns](https://steamcommunity.com/sharedfiles/filedetails/?id=2802430252).

This folder contains the 11 distinct MP5-specific accessory models:

- Barrels: standard, short, integral suppressor, and monolithic integral suppressor
- Magazines: standard, 45-round, and 10mm 30-round
- Underbarrel: rail grip
- Stocks: standard, classic full stock, and collapsible

Crowbar bodygroup meshes retain the front-sight and grip variants, including the glowing sight materials. The receiver and complete weapon model are excluded. The meshes use the original SMD UVs and normals; VTF color, normal, and emissive maps were exported to PNG and converted to S&box materials in the materials folder.

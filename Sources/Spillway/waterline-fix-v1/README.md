# Spillway terrain waterline repair — 2026-11-03

The visual mountain terrain began at radius3600 with an open inner edge generally at z80, above the
river at z-245. Low views could see sky through the open underside, making the forest and terrain float.

The installed repair adds a rounded sloping bank from that exact rim down to z-560. Its inner radius
varies3180+55*sin(7a)+30*sin(13a+.8), keeping the bank outside the playable enclosure. The upper edge
retains the existing positions and smooth normals, including the accepted waterfall basin carve.
There are576 rim samples and6 strips:6,912 added visual triangles. The original104,832 terrain faces
are preserved exactly. Existing materials are reused. The scene, river, trees, other chunks, ModelDocs,
collision hulls, lighting and reflection settings are unchanged.

`build.py` stages the narrow OBJ addition and the generator update, guards all public Spillway model
sources and the scene, and checks that every new boundary edge is either shared with the original
terrain or submerged below the river. `install.cs.txt` publishes the two files through the native editor.
The public `spillway_mountains.vmdl` compiled successfully with a full native compile. `verify.py` checks
the installed file hashes and all protected inputs. `Tools/spillway_landscape.py:close_shoreline` retains
the closure during future terrain generation.

Evidence and backups: `output/spillway/waterline-fix-v1/`. The native captures `waterline`, `downstream`
and `bank` each have matched `-before.png` / `-after.png` files, using the saved scene with the same
camera and lighting. The after captures load the installed public model. Both passes had zero error
models and preserved the user's active scene and play state. Temporary capture scenes were destroyed.
No scene switching, gameplay edits or playtest were required for this render-only repair.

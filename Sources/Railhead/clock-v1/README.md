# Railhead station clock preview

The suspended central-platform clock at plan `(0, 1110, 240)` is rebuilt as a
double-sided physical assembly. The rolled housing, recessed dial, individual
minute indices, separate hour/minute hands, shallow glass cover, fasteners and
hanger fittings retain the existing clock's design and 14:03 time.

Approved and installed on 2026-11-03. The public central dressing model now imports
the trimmed base and approved clock mesh; the scene is unchanged. An exact geometry-signature match removes only
the old clock's 124 triangles from the private preview model. That model keeps
all original vertex, normal and UV records and the complete original physics
section. The new decorative clock has 16,572 triangles and no collision shapes.

Run commands from the canonical checkout, with the existing editor stopped:

```powershell
rtk python Sources/Railhead/clock-v1/build.py
rtk python Sources/Railhead/clock-v1/review.py
rtk python Sources/Railhead/clock-v1/verify.py
```

`review.py` imports through native `run_csharp`, compiles assets, then opens
Railhead for an offline play check. The review camera copies the player's post
effects and uses matching position, lighting and exposure for both variants.
Each view receives 180 normal streaming frames; texture residency is not forced.
The runner restores the prior scene and stopped state. A scene change from
another editor user aborts capture and leaves their new session untouched.

If an asset compile request times out, inspect compiled-file timestamps and run
`native.py script model-check.cs.txt` before deciding whether further compilation
is needed. `review.py --capture-only` does not repeat imports or compilation.

Comparison images and validation receipts live in `output/railhead/clock-v1`.
`installed.json` records the installed public model's play-mode check with a player
present and no error models. `runtime-installed/` contains the final screenshots.
The generator helper `Tools/railhead_station_clock.py` matches the approved mesh;
`railhead_map.py` retains the old housing collision on regeneration.

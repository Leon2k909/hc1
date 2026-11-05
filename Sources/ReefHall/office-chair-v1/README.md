# Reef Hall upper-office swivel chair — review candidate

One chair behind the desk at plan (1960, 780), yaw 180°, in the control room's upper office. Chair centre (1960, 806, 208), facing south. The preview removes exactly the original chair's 36 triangles: seat, back and pedestal. The desk and screens, other faces and vertex/UV/normal records stay untouched. The full ModelDoc physics section and saved scene are unchanged.

The 9,844-triangle replacement has rounded crowned cushions, a curved lumbar back, moulded rear shell, connected supports and fasteners, adjustable armrests, tilt lever, telescoping gas lift, five swept feet and twin-wheel swivel casters. It reuses the map's original `rh_pad_dark.vmat` upholstery with its existing tile size. Three private materials supply polymer, steel and rubber. No added lights or emissive materials.

Run from `C:\sbox-projects\hc1\forked-shooter-main`:

```powershell
rtk python Sources/ReefHall/office-chair-v1/build.py
rtk python Sources/ReefHall/office-chair-v1/setup.py
rtk python Sources/ReefHall/office-chair-v1/review.py
rtk python Sources/ReefHall/office-chair-v1/verify.py
```

Build writes to an output staging folder; native editor import touches only the private preview files. The actual offline map is played with a player, both versions use the same camera/lighting/exposure and normal streaming, then the prior editor scene and play state are restored. No full map regeneration. No performance benchmark. Installation awaits user approval.

Artifacts: `output/reefhall/office-chair-v1/chair-comparison.png`, `validation.json`, `play-state-restored.json` and the original full-resolution screenshots under `runtime-review/`.

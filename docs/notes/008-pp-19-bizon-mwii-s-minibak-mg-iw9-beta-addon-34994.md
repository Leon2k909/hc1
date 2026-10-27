## PP-19 Bizon (MWII's "Minibak", mg_iw9_beta, addon 3499492742)
- The real 9x18 Makarov Bizon (category SMG) under its real name: the 64-round helical mag, 680 rpm, auto and semi,
  57-N-181S ball at 320 m/s from its 230 mm barrel, modelled as S&B's 95 gr FMJ (G1 0.122), sights 51 mm over the bore,
  zero 100 m (`kastov_prefabs.gameplay_bizon`). Damage, falloff, recoil pattern and move speed are the Vityaz's (the
  MP5's), even though 9x18 is a bit weaker than 9x19. The recoil scale (0.43,2.6) is the Vityaz's scaled by free recoil.
- Its materials and sounds are from `Tools/bizon_assets.py`: its own shots (levelled -4 dB to match the Vityaz's) and
  reload foley at the viewmodel QC's event frames. The stocks and grips (`PARTS_BIZON`, `Assets/gunsmith/bizon/`) are
  the AK-platform parts, with the 74u's materials; the factory stock is the 74u's, so their recoil scales are the 74u's.
- It has no Underbarrel slot (the helical mag sits where a grip would go), so `make_parts_eligible` skips the
  categories a gun has no slot for. The CoD-only barrels are left out.
- Optic `OpticAimCorrection` `2.554,0,-1.353` is derived, NOT checked in-game: the 762's verified correction minus how
  far the Bizon's optic slot sits from the 762's in camera space at the ADS pose
  (inv(cam_ads) · sling_ads · inv(sling_bind) · inv(world frame) · slot). That formula gives the 74u's, Vityaz's and
  RPK's values exactly. The iron sights were checked in a render (post centred in the notch), not in-game, and the
  left hand on the helical mag has no `GripFit`.


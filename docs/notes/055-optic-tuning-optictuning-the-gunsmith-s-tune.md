## Optic tuning (`OpticTuning`, the gunsmith's TUNE)
- The user asked for an optic tuning system like Modern Warfare II's (2022) (2026-10-08). In MWII, a fitted
  attachment's TUNE opens two sliders that trade one trait for another, saved with the build. Here each slider is
  something a shooter really sets on a sight, not a made-up stat:
  - EYE POSITION (MWII's): the optic slides along its rail, one Picatinny slot (0.394") at a time, NEAR to FAR.
    Nearer the eye, its window or eyepiece fills more of the view. Further, more of the world shows round it.
  - ZERO: the elevation turret, the range where the bullet's path comes back through the line of sight. It replaces
    `Shootable.ZeroRange` in `ApplyBallistics` (`Equipment.GetSightZero`), so it only moves the shots where bullets drop
    (Battle Royale's `BulletDrop`). The choices are 25-600 m (`OpticTuning.Zeros`) plus the gun's own, up to the 12
    mrad of elevation a red dot's or holographic sight's turret gives (`MaxElevation`). A gun with no ballistics
    figures has no ZERO card.
  - MWII's optics also had a weight slider, trading aiming speed for steadiness, and its variable scopes a zoom one.
    The optics here have fixed magnifications, and a part's real weight already counts (`GunsmithPart.Mass`), so
    neither is modelled.
- Only the 27 MWII optics on the M4's mounts (`gunsmith/m4a1/mw2022/`, `OpticTuning.IsTunable`) take it: their mount
  (`GunsmithMw22Attachment.RefreshMount`) slides the optic along the bore by `GunsmithAttachmentPoint.OpticRailShift`,
  which leaves the sight line, and so every `ManualOffset` aim, where it was. The old `gunsmith/m4a1/optics/`, the
  MP5's, the M700's and the SCAR-H's optics aren't tunable.
- How far each gun's optic can move (`OpticTuning.Travel`, back towards the eye and forward, in slots): the M4A1,
  M16A4 and AUG 2 and 2, the MCX 2 and 3, the P90 and MP7A1 0 and 2, the Uzi's claw mount 0 and 1, the AK family,
  Vepr-12, FAL and FAMAS 1 and 1. Read off where each rail ends round the optic's slot, not checked on every gun
  in-game. A gun not in the table gets 1 and 1.
- A magnified optic's eye relief follows the slide: `OpticZoom` measures the eye from the rated relief, less the
  rail shift (the learned neutral eye sits wherever the optic is), so off its rated relief the lens picture shrinks and
  shades (`ScopeEyeBox`), as a real scope's does. The tune view says so, and shows the relief against the rated one.
- The tune view (`GunsmithAttachmentBrowser`): TUNE on the fitted optic's row (in the slot list and the Optic slot's
  parts) opens it in place of the parts list. EYE POSITION shows the rail position, how big the sight looks against
  its usual place and the eye relief; ZERO shows where the bullet passes the point of aim at 50-300 m
  (`OpticTuning.HeightAt`, from the gun's prefab's load). RESET puts both back. Back and Escape step out of it to the
  parts list first (`Back`). The stage gun's optic slides as the slider moves.
- Saved per class, weapon and optic in cookies (`hc1.gunsmith.class<n>.<weapon>.optic.<optic>.eye|zero`,
  `GunsmithLoadoutManager.Get/SetOpticEyePosition`, `Get/SetOpticZero`), so each optic keeps its own tune. Build codes
  carry the fitted optic's (`SharedWeaponBuild.OpticEye`, `OpticZero`), and Theater's first-person gun gets the
  recorded build's through `_fitting`. A gun picked up off the floor shoots at its factory zero.
- Compiled offline and hotloaded into the editor (2026-10-08). None of it has been seen in the gunsmith or in a match:
  the view, the slide on each gun (that the optic stays on its rail), the relief's shading through a scope, and a
  zero in Battle Royale.


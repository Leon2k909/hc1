## Flashbang (`FlashbangGrenade`, `FlashbangEffect`, `hc1_flashbang.shader`)
- The user asked for a real flashbang ("1:1 to real life"), keeping the after-effects they liked (the glare, muffled
  hearing and ringing), plus moving slower and being unsteady.
  - The first version (2026-09-28) kept the white faint: 0.3 at most, gone in half a second. On 2026-09-29 the user
    found it "just a really small white thing". They asked for a proper flash of white, disorientation, and the blur the
    original flashbang had close up.
  - The original whited the whole screen out for 2.4 s (1.2 s of it solid), under a strength-10 bloom that smeared the
    view. It had 4 s of glare and muffle, for anyone within 750 units (19 m) with it within ~70 degrees of their view,
    however far off.
- `FlashbangGrenade.Measure` works out what reaches the player being viewed, sense by sense (`FlashExposure`; 1 is 6 ft
  away looking straight at it). The figures are NIJ's measurements of a MK141 (2003: at 6, 9 and 12 ft, ~90 million
  candela, 178 dB less 9 dB per doubling of the distance, and 0.162 bar falling with the distance to the power 1.46):
  - Vision: the light in the eyes, direct (inverse square, less the further off the view's centre, none past 100
    degrees) plus what the walls, floor and ceiling throw back (`Bounced`, 18 rays), so indoors, looking away still
    dazzles. The strength is the light's logarithm (`SightDecades` 2), gone at 100 times less than at 6 ft: about 18 m
    looking straight at it in the open. The eyes still get ~2,400 lux-seconds there, a full-power camera flash (guide
    number 60) from 2 m. Until 2026-09-29 it was gone at 40 times less (11.5 m).
  - Hearing: 178 dB at 6 ft down to 160 dB, where the ringing starts (about 7 m in the open), 12 dB less round a wall.
  - Balance: the blast's overpressure down to 0.035 bar (about 5 m in the open), halved round a wall.
  - Nothing past 750 units. Glass passes the light, not the bang or the blast. Traces skip people, bodies, triggers,
    player clips and grenades.
- `FlashbangEffect` (on the scene's camera, local only) plays it out. A flash that reaches a sense harder than what's
  left of the last one starts that sense over. At strength 1: white 4 s (1.4 s of it solid), sight 5 s (the M84's
  "approximately five seconds"), blur and glare 6 s, deaf 2 s then muffled until 8 s, ringing 10 s, and dazed 5 s.
  Closer, up to 1.3 times as long.
  - The white (`FlashbangOverlay`, a ScreenPanel at ZIndex 200, over the HUD) is flash blindness.
    - It's solid from strength 0.6 up (`FullWhite`): 4.6 m looking straight at it in the open, nearer looking away,
      further indoors, where the walls' light counts too.
    - It holds for up to 1.5 s (1.4 s at 6 ft), then thins out over 0.4 + 2.2 x strength seconds.
    - Less light gives a fainter white, (strength / 0.6)^0.8, that goes sooner.
  - The blur: the afterimage's CommandList grabs the frame with its mips. The shader takes 17 taps over a disc: the
    engine's 16-tap Poisson disc plus the middle, each tap read from the mip level about a third of the radius across.
    - The radius is up to 2% of the screen's height (`MaxBlur`). There's none below strength 0.2, and all of it from 1.
    - At strength 1 it clears from 2.15 s to 6 s, so the sharpness comes back last.
    - The blast's daze blurs it up to half that on its own, so a flashbang going off close behind you blurs the view too.
  - The afterimage: the same CommandList, at `AfterPostProcess` (order 10000), keeps the frame the flash lit and screens
    it onto the view, fading over the sight's time. If the flash was on screen, its fireball's spot burns in bright,
    then stays as a dim, purplish blot for as long again.
  - The glare: a Bloom (threshold 0, Strength up to 4) and a ChromaticAberration on the camera's child "Flashbang",
    which win over the camera's own; the mode is the camera's own bloom's (Additive). The engine adds about Strength / 2
    times the blurred view (6 mips at Strength / 12), so the view is up to three times brighter. It comes up under the
    white and shows as the white thins.
  - Hearing: temporary deafness (`Deafness`, `Code/GameLoop/Audio/Deafness.cs`), and the ringing
    (`sounds/player/ear_ringing.sound`, see Ordnance and handling sounds).
    - `DeafnessProcessor` on the Game mixer (as the acoustic reflex is): world sound up to 36 dB quieter and
      low-passed down to 250 Hz at full deafness, easing back on a log scale as the level falls. Voice chat, music, UI
      and radio aren't touched. The ringing plays on the master mixer, so it isn't muffled with the rest.
    - It replaced the stock "weird.4" DSP on the master mixer (2026-10-16, the user: flash and stun grenades "should
      do temporary deafness"), which was an effect preset rather than a hearing loss, and muffled the ringing and UI.
    - The Flashbang is the only tactical that deafens: the M84 is the stun grenade, and the Decoy (in the
      `M84_Stun_Grenade` folder) only plays gunfire. Blasts (HE, C4) don't deafen yet.
    - Compiled with dotnet, not yet heard in-game.
  - Balance: the blast upsets the inner ear. It comes on over 0.15 s rather than jerking the view.
    - Every gait is up to 30% slower (`MoveSpeedScale`, in `PlayerPawn.GetWishSpeed`).
    - The aim wanders up to 2.5 degrees (`SwayDegrees`, `CameraController.ApplyFlashSway`). The owner moves their own
      pawn, and on their machine they're the one being viewed, so only they need that.
    - The view rolls to and fro up to 4 degrees (`RollDegrees`, `CameraController.ApplyFlashRoll`). Only the camera
      rolls, about where it looks, so the aim doesn't move.
- A trace keeps at most 8 tags to leave out (`WithoutTag` / `WithoutTags`) and silently drops any more, so
  `FlashbangGrenade.Solid` leaves out 7, with room for glass.
- Offscreen renders (`RenderToBitmap`) skip post-processing and the UI, so the glare and the white can't be seen there.
  The afterimage's CommandList does run, so the blur should show.
- A shader can't be compile-checked offline: the install's `resourcecompiler.exe` fails on s&box shaders ("without
  buffer"). The blur was checked by copying the shader into `Assets/shaders` under another name and running
  `recompile_asset` on it. The new names (`FlashBlur`, `g_vBlurTaps`) were in its `.shader_c`. Then the copy was deleted.
- Bots aren't flashed. The prefab's `EffectLifeTime` key is left over and ignored.
- Checked offscreen on 2026-09-28: the exposure with real traces in a test scene (the ranges above, walls and glass),
  and the afterimage and the spot in renders. The glare and the white were set from the engine's bloom maths and a
  preview, not seen. The 2026-09-29 white, blur and roll compiled and hotloaded into a running game, but haven't been
  seen yet. None of it has been checked in-game yet.


# Sprays and personal loading screens — 2026-11-05

Implemented through code only; no editor connection, scene/prefab changes or new artwork.

## Use

- **Profile → Sprays:** choose one of six shipped badge designs. Assign the initially unbound **Spray** action under
  Settings → Controls. Aim at a nearby solid wall or floor and press it. One active mark per player, a ten-second
  cooldown, a two-minute lifetime, a 64-mark scene limit and existing round cleanup bound the objects.
- **Profile → Loading Screens:** choose Game default or one of eight existing map artworks. **Your image** accepts
  a direct HTTPS PNG/JPG/JPEG/WebP link and saves it locally. This is URL-based personal-image support, not a disk
  file picker or multiplayer image upload. Restore default returns to the engine/game's own loading media.

The starter sprays reuse existing original medal/prestige artwork. Their catalogue is fixed; personal loading
URLs cannot be used as sprays. Add curated designs in `Code/Cosmetics/CosmeticCatalog.cs`.

## Integration

`CosmeticSystem` is an automatic runtime GameObjectSystem: no editor wiring. It handles the Spray action behind
existing menu/input guards and applies personal loading art through `LoadingScreen.Media` in BeforeLoad/OnLoad,
while the loading screen is visible, and before `GameUtils.LoadMap` begins a map transition. Loading choices and
personal URLs remain local. The initial engine/package-download phase can happen before game code/preferences
are available and may retain engine artwork. Image-host availability and engine image decoding affect custom URLs.

`Client.RequestSpray` runs on the host. It checks caller ownership, request rate, preset ID, life/movement state,
cooldown and a finite normalized direction aligned with the holder's replicated view. The host derives the eye
position from stance and traces 96 units itself; clients never supply a hit point. Misses, starts in solid, sky,
water, characters and rigidbody surfaces are rejected. The accepted host-owned network object carries its preset
ID and transform, so observers/late joiners can draw it. Decal definitions/textures are local, bounded to the six
catalogue entries; the render component is marked nonnetworked. Sprays have no collider or gameplay damage.

Selection panels use the existing orange/charcoal menu styles and controller button navigation. Custom URL text
entry needs a keyboard/text-input method. No CoD/CS names, logos or images were added.

## Validation and limits

- `rtk dotnet run --project Tools/CosmeticsChecks/CosmeticsChecks.csproj --disable-build-servers -- C:/sbox-projects/hc1/forked-shooter-main`
  passed 62 checks linked to production catalogue, preferences and host request code, with deterministic engine seams.
  Covers image validation, saved/default restoration, caller/state rejection, host trace reach, cooldown/replacement,
  floor orientation, scene cap, asset existence and the unbound action.
- `Code/razedtest.csproj` built offline: 0 errors, 108 warnings.
- Production cosmetics SCSS compiled with Sass. Browser layout previews at 1440×900 and 800×900 were inspected;
  the narrow preview had no horizontal overflow or broken images. These are layout previews, not game screenshots.
  Evidence: `output/playwright/cosmetics/`. The task's browser and temporary local HTTP server were stopped.
- Actual decal projection/orientation, multiplayer replication/late join and loading transitions still need an
  in-game check. No claim is made that the entire engine bootstrap loading screen is replaced.

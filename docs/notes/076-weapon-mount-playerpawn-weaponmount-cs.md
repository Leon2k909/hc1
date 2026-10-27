## Weapon mount (`PlayerPawn.WeaponMount.cs`)
- Aim at a ledge, a sill, a wall's top or a crate and the crosshair shows MOUNT (`CrosshairHud`); the mount key rests
  the gun there, with less recoil and sway, until you move, jump, crouch, go prone, sprint or press it again.
- The user (2026-10-19): "the mount system definitely doesnt work properly it hardly ever shows the mount option". The
  probe looked for a top at one point 43 ahead of the eye. Standing against cover, a wall's or sill's top runs from
  about 16 to 38 ahead, so it found the floor behind it, or nothing.
- Now `FindMountTop` (static, so it can be checked in a scene of its own) traces down every 3 from 12 to 40 ahead and
  takes the nearest flat top between `minTop` and `maxTop` (the old heights: 23-64 over your floor, within 28 under
  the eye):
  - A top under `minTop` is floor: a top less than `MountMinRise` (14) over the last floor is a stair or a slope going
    up, so no mount.
  - Starting inside something (a wall over sill height) or finding something above `maxTop` ends the search.
  - A sloped trace hit (a bevelled edge) carries on to the flat of the top. The muzzle line must be clear to 16 past it.
- `output/weapon-mount/mount-probe-checks.cs.txt` builds cover in an isolated scene and compares the new probe with the
  old one, standing and crouched. On 2026-10-19 all 20 cases passed: the new one mounts on a 12-thick waist wall, an
  8-deep sill with the wall above, a 2-deep rail, a crate and a deep wall (the old one only the last two), and neither
  mounts on stairs, a 30-degree ramp, a tall wall, a low box or a wall 50 ahead.
- The prompt still only shows while aiming (`CanUseWeaponMount` needs the `aiming` tag). Not yet tried in a match.
- 2026-10-25, the user: MOUNT "shows at the wrong times and doesnt actually work", and the bind "might be on the noclip
  one" (their screenshot: MOUNT at the hip in an empty alley).
  - `CrosshairHud`'s BuildHash didn't hash the mount state, so the prompt stayed as it was at the last rebuild (aiming
    in or out): MOUNT left up at the hip, and MOUNTED never shown, so a mount looked like it did nothing. It hashes
    `MountState()` and `MainHUD.IsHudEnabled` now.
  - The ticks that skip `UpdateWeaponMount` (dead, mantling, pipe climbing) clear the mount (`ClearWeaponMount`).
  - A press probes for itself instead of waiting for the 0.09 s probe, and mounting plays the support's footstep at
    0.35, heard only by the shooter (`PlayMountSound`).
  - Mount was MOUSE5 and the editor-only Noclip MOUSE4: the hint shows both side buttons as the same mouse glyph, and
    the back one toggled noclip, which also blocks mounting. Mount is MOUSE4 now and Noclip is N (`Input.config`).
  - Built with dotnet and compiled in the editor (0 errors), not yet tried in a match.


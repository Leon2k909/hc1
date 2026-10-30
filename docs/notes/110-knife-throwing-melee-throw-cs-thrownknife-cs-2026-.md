## Knife throwing (`Melee.Throw.cs`, `ThrownKnife.cs`, 2026-10-14)
- With either the Trenchknife or M9 Bayonet equipped, primary attack swings and secondary attack throws the held knife.
  Both prefabs already list Attack1 and Attack2; the melee component routes secondary input to the throw without asset changes.
- The host releases it after a 0.18 s wind-up, using the player's replicated eyes and inherited movement velocity.
  Defaults: 1600 u/s forward, 80 u/s upward, 100 damage. Holstering, dying, freezing, climbing or mantling before release cancels it.
- `ThrownKnife` sweeps a 2-unit radius through hitboxes with scene gravity. The first impact deals melee damage once
  and turns it into a normal `DroppedEquipment` pickup. The throw consumes the carried knife and switches weapons;
  E or walking over the landed knife recovers it. A flight times out after 8 s; pickups use the existing round cleanup and lifetime.
- A disabled Equipment component on the projectile retains the resource and thrower after the carried weapon is removed,
  preserving its kill-feed icon, knife reward and Gun Game attribution. Only the host creates the projectile and deals damage;
  the throw RPC accepts only the host or the owning player.
- Validation: offline build and the editor's code compiler passed with zero errors. Live host checks on Railhead passed
  for both knives: frozen-player rejection, holster cancellation, duplicate rejection, visible flight, one 100-damage hit,
  weapon switching, recovery and a normal melee swing after recovery. Screenshots and results are in `output/knife-throw/`.
  A runtime Attack2 injection through WeaponInputAction also passed with only the knife enabled: empty hands after release,
  impact and recovery. The native Bridge's frame input helper did not reach fixed-step weapon input, so that check used
  Input.SetAction plus the actual fixed-step handler. A separate remote-client session remains untested.
- Releasing the last held knife calls PlayerPawn.Holster directly; PlayerInventory.HolsterCurrent reaches a null Deploy call.


# Door placement audit — 2026-11-05

The user approved retaining Veridant's new reception doors and requested a search
for other places on this or other maps that need doors. This pass assessed
candidates; it installed no further doors. Existing reception doors remain saved.

Reviewed 24 scene files for door components and named door objects; authored
geometry often contains doors inside larger map models, so zero components does
not establish that a map is missing doors. Read the relevant Veridant, Reef Hall,
Cerro Blanco, Railhead, Lowtide, Riverdale, Riverside, Orion, Spillway and Boxyard
generator sections, and checked Ares/Collider's existing automatic components.
Rendered seven candidate views in isolated editor scenes. The active editor
session, runtime scene and play state were preserved; all isolated scenes were
destroyed. Inventory, camera settings and images: output/door-audit-20261105/.

## Best candidates, in order

1. **Veridant café shopfront** — two empty 64 x 96 openings under the colonnade,
   centred at plan n=-100 and +80, e=-268. Adjacent glass already has dark frames.
   The approved glazed door design is a strong match, resized to these openings.
2. **Veridant operations upper lobby** — empty 100 x 100 balcony opening, centred
   at plan e=510, n=-428, base z=128. Matching double glass doors would finish the
   exterior envelope. Check swing clearance against the balcony and reception desk.
3. **Veridant lounge courtyard entrance** — empty 100 x 96 opening, centred at
   plan e=-208, n=-250. Wider paired doors using the same design would fit the
   existing stone, timber fins and exterior light. Keep the busy route clear.
4. **Reef Hall upper control office** — glass partition has unfilled entrance gaps,
   80 inches wide on the south partition and 70 on its east side. The captured
   south gap spans plan e=2000..2080 at n=720, floor z=208. Use a glazed office
   leaf with dark trim and restrained hardware to match the partition.
5. **Cerro Blanco café upper terrace room** — the framed exterior opening at
   plan e=550..650, n=340, base z=180 is 100 x 120. A glazed pair would fit the
   gallery architecture. Source explicitly leaves doors open because of bots;
   resolve bot traversal before installing closable leaves.

Spillway control-room landing entrances are a lower-priority candidate for glazed
industrial doors; source and a straight-on capture confirm the front opening at
plan e=-345..-205, n=800, base236/head402. Its industrial style needs different
hardware from the resort doors. Treat the existing large hall portals as intended
route openings rather than filling all of them.

## Existing doors and gameplay constraint

Railhead goods-shed doors are modelled slid aside, and Lowtide ground-storey bay
doors are folded back. Boxyard container doors are already modelled open/closed.
Riverside's T2 and office have approved door models. Ares has three proximity
sliding assemblies and Collider has one. These are not missing-door candidates.

LightweightCombatBot.WaitForDoor and BotSystem.Doors work with TerrorTown.MapMover,
not Facepunch.Door. Facepunch.AutomaticSlidingDoor explicitly scans players, bots
and zombies and handles navmesh exclusions. The newly approved reception's manual
Facepunch.Door leaves passed player-use and collision checks, but bot passage has
not been validated. Do not expand manual closed leaves across bot routes without
adding verified bot support, or using suitable automatic operation. This audit
made no gameplay C# changes.

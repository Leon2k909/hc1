# Reef Hall south office doors — 2026-11-05

Installed and saved a glazed pair and fixed glass transom in the empty south
office partition gap,plan e=2000..2080,n=720,floor208,head380. Existing jambs
take two inches per side,so usable width is76. Leaves reuse the approved Veridant
leaf at scale(1,37.15/29.15,.96),hinges(720,-2002.65,208)/(720,-2077.35,208),yaw0/180.
Fixed transom origin(720,-2000,208) fills the space above the normal-height leaves.
Its 132-triangle model reuses rh_gunmetal/rh_glass and compiled natively.

Roots Office south glazed door left/right carry moving BoxCollider and
Facepunch.Door,90 degrees,.55 seconds. Office south fixed glass transom has a
static collider. Saved-object and generator checks passed; reefhall_map.py retains
reefhall_office_doors.scene_objects(ids) at scene root for the Door pivot logic.
Tools/reefhall_office_doors.py builds the scoped transom and defines all3 objects.

Actual direct editor-window captures are in output/reefhall/office-doors-v1/,
before-window.png and after-window.png. Both were inspected for the same Reef Hall
view,camera(590,-2040,268),angles(0,0,0),FOV80. No lighting/display changes,
offscreen rendering or computer use. Immediate scene backup is alongside them.
An earlier capture showed another scene and was not used as review evidence.
Reef Hall's prior camera was restored,then Veridant was reactivated; play stopped.
Runtime movement/collision and bot traversal remain unverified.

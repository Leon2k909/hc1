# Cerro Blanco ground-floor café courtyard doors — 2026-11-06

Installed and saved matching glazed leaves in the café courtyard entrance beside
the terrace stairs,90 x 124 opening,plan e=480..498,n=245..335. Existing jambs
leave85 clear inches; top rail lowers the clear head to121.5. Reuses reception
leaf at scale(1,41.65/29.15,1.22),hinges(248.15,-489,0)/(331.85,-489,0),yaw+90/-90.
Roots Cafe courtyard glazed door left/right carry moving BoxCollider and
Facepunch.Door,90 degrees,.55 seconds. No stair or furniture edits.

Saved-object and generator checks passed; courtyard/terrace GUIDs remain distinct.
Tools/cerroblanco_doors.py scene_objects(ids,courtyard=True) retains the pair.
Native play validation explicitly started Cerro Blanco. Both leaves reached Open,
rotated90 degrees,and returned Closed. Traces at x270/310,y=-515..-465,z45
cleared the open leaves and hit the respective closed leaf. Bot traversal and
multiplayer were not checked.

Direct screenshot_game/PrintWindow captures in
output/cerroblanco/cafe-courtyard-doors-v1/before-window.png and after-window.png
were inspected for the same scene/view,camera(290,-261,60),angles(3,-90,0),FOV80.
No offscreen rendering,computer use,lighting or display setting changes.
Immediate scene backup accompanies the captures. Restored Cerro Blanco's prior
camera and Veridant's active tab,with play stopped.

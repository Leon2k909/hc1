# Veridant café west doors — 2026-11-05

Installed and saved matching glazed double doors in the café's south west-side
entrance,60 x 96,plan e=-720..-704,n=-110..-50. Reuses reception leaf at
scale(1,1,.96). Saved roots Cafe west glazed door left/right have hinges
(-109.35,712,0)/(-50.65,712,0),yaw+90/-90. Moving BoxCollider and Facepunch.Door,
90 degrees,.55 seconds. Saved JSON and generator checks passed, including
distinct café/lounge GUIDs. Generator lounge_west_scene_objects(ids,cafe=True).

Actual displayed editor-window evidence was captured through native
bridge_call screenshot_game/WindowCaptureHandler (PrintWindow, no rerender).
output/veridant/cafe-west-doors-v1/ includes the full before-window.png and
matched before-viewport.png/after-viewport.png. The latter are direct window
crops at x436,y110,w1084,h438. Same camera(-80,940,60),angles(3,-90,0),FOV80,
unchanged lighting and display settings. Gizmos remain as displayed.
No computer-use or temporary/offscreen rendering was used.

Play validation was not run. Restored the previous active Veridant camera
(325,-160,65),angles(16.8,29.7,0); scene remained stopped. Immediate scene backup
is alongside the screenshots.

# Veridant lounge west doors — 2026-11-05

Installed and natively saved two matching glazed leaves at the missing west
lounge entrance,60 x 96,plan e=-720..-704,n=-420..-360. Reuses reception leaf,
scale(1,1,.96); roots Lounge west glazed door left/right have hinges
(-419.35,712,0)/(-360.65,712,0),yaw+90/-90. Moving BoxCollider and Facepunch.Door,
90 degrees,.55 seconds. Saved JSON and generator placement checks passed.
Regeneration retains lounge_west_scene_objects in veridant_reception_doors.py.

Evidence uses the native bridge screenshot_game/WindowCaptureHandler, which
captures the real editor window with PrintWindow. These are not rerenders.
output/veridant/lounge-west-doors-v1/before-window.png and after-window.png use
the same camera(-390,940,60),angles(3,-90,0),FOV80 and unchanged display settings.
The full window identifies the project and active Veridant scene. An immediate
pre-edit scene backup is in the same folder. No computer-use tools were used.

Play verification was not run. After saving/capturing, the editor stalled during
recompilation of veridant_dress.vmdl, then recovered. Restored Riverside as the
active scene,stopped, and Veridant's previous camera(-690,470,60),angles(4.97,0,0).

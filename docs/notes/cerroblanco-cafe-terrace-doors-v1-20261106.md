# Cerro Blanco café terrace doors — 2026-11-06

Installed and saved a glazed pair in the café upper room's terrace entrance,
plan e=550..650,n=322..340,base180,head300. Existing black frame reduces the
clear width to95 and head to297.5. Reuses the approved reception leaf at
scale(1,46.65/29.15,1.18),hinges(331,-553.15,180)/(331,-646.85,180),yaw0/180.
Saved roots Cafe terrace glazed door left/right use moving BoxCollider and
Facepunch.Door,90 degrees,.55 seconds. Saved-object and generator checks passed.
Tools/cerroblanco_doors.py supplies scene_objects; cerroblanco_map includes them.

Matched direct editor-window captures are output/cerroblanco/cafe-terrace-doors-v1/
before-window.png and after-window.png. Both were visually verified as the same
Cerro Blanco scene/view,camera(568,-600,240),angles(3,180,0),FOV80. Native bridge
screenshot_game/PrintWindow captured the displayed window. No RenderToBitmap,
temporary scene/camera,exposure or lighting changes,or computer use.

ScreenshotService.RequestCapture was also tried via reflection (type is internal).
The first frame showed another scene and was rejected; a second requested frame
did not write while the editor was backgrounded. Neither is review evidence.
Runtime movement/collision remain unverified: a play request started Veridant
after the active tab changed; it was immediately stopped and no tests were run
against the wrong scene. Restored Cerro Blanco's previous camera and stopped
Veridant as the active tab. Immediate scene backup accompanies the captures.

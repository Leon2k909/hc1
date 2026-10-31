"""Fill in match_view.cs.txt for one shot and write it to a temporary script: python match_shot.py <out path> <eye x> <eye y> <target x> <target y> <target z> <old|new|both>"""
import os
import sys

out, ex, ey, tx, ty, tz, mode = sys.argv[1:8]
here = os.path.dirname(os.path.abspath(__file__))
text = open(os.path.join(here, "match_view.cs.txt"), encoding="utf-8").read()
for key, value in (("EYE_X", ex), ("EYE_Y", ey), ("TARGET_X", tx), ("TARGET_Y", ty), ("TARGET_Z", tz)):
    text = text.replace(key, f"{float(value)}f")
text = text.replace('"MODE"', f'"{mode}"')
open(out, "w", encoding="utf-8", newline="\n").write(text)

"""Adapt the verified guarded native installation workflow for the approved canopy."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];HERE=Path(__file__).absolute().parent
old=ROOT/'Sources/Riverside/still-here-board-v1'
for name in ('prepare_install.py','install.py','check_installed.py','finish_install.py'):
 s=(old/name).read_text().replace('still-here-board-v1','tower-roof-v1').replace('still_here_board_v1','tower_roof_v1')
 for a,b in [('legacy_board','legacy_roof'),('dressing_without_board','dressing_without_roof'),('board.vmdl','roof.vmdl'),('Park Graffiti Boards','Guard Tower Roofs'),('STILL HERE Board','Guard Tower Roof'),('896,752,144','4676,3156,468'),('411.535923789485,390.99995599854793,261.25','1600,530,628'),('0,30.000727780827372,0','0,-163.3007557660064,0'),('len(cut)==14','len(cut)==4'),('removed_triangles=14','removed_triangles=4'),('RemovedOldTriangles=14','RemovedOldTriangles=4'),('Boards=1','Roofs=1'),('OnlyOriginalBoardRemoved','OnlyOriginalRoofRemoved'),('hitch','roof'),('Hitch','Roof')]:s=s.replace(a,b)
 (HERE/name).write_text(s)

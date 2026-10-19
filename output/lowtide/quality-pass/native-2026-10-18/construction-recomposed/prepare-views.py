from pathlib import Path
import json, math
folder=Path(__file__).resolve().parent/'native-review'
views=[
('east-window',(-260,-120,130),(-315,-240,111)),
('west-window',(-260,120,130),(-315,240,111)),
('window-interior',(-320,-340,120),(-315,-240,115)),
('east-door',(-1220,-1335,110),(-1050,-1400,85)),
('west-door',(-1220,1335,110),(-1050,1400,85)),
('warehouse-head',(-455,-165,965),(-378,-228,944)),
('shed-hopper',(-650,-275,260),(-694,-314,232)),
('pipe-outlet',(230,-1060,30),(207,-1008,12)),
('street-facade',(-250,-1200,64),(300,-1000,220)),
('canal-wide',(-1200,0,110),(0,0,250))]
requests=[]
for name,p,t in views:
    dx,dy,dz=[b-a for a,b in zip(p,t)]
    pitch=math.degrees(math.atan2(-dz,math.hypot(dx,dy)))
    yaw=math.degrees(math.atan2(dy,dx))
    requests.append(dict(name=name,position=','.join(map(str,p)),angles=f'{pitch:.6f},{yaw:.6f},0'))
(folder/'views.json').write_text(json.dumps(requests,indent=2)+'\n')
print(f'Prepared {len(requests)} paired native camera views')

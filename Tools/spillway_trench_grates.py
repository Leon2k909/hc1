"""Flush trench covers: angle frames, removable steel bar panels and captive bolts."""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P
X=P.v(1,0,0);Y=P.v(0,1,0);Z=P.UP
MATS={f'tg_{n}':f'materials/spillway/trench-grates-v1/{n}.vmat' for n in ('steel','frame','dark','bolt')}
PLACEMENTS=((330,-460,150,55),(-50,-930,190,60),(980,-470,90,140),(-1130,50,140,60),(1730,-960,140,65))

def grate(m,c,width,height):
 c=np.asarray(c,float)
 def box(p,size,mat='tg_steel',bevel=.035):P.bevel_box(m,c+np.asarray(p),(X,Y,Z),size,mat,bevel)
 # A dark backing masks the existing surface through the slots, without carving the map's floor.
 P.quad(m,'tg_dark',c+Z*.06,X,Y,width-1.2,height-1.2)
 # Perimeter angle frame stays inside the former decal footprint and below one inch above the floor.
 for x in (-width/2+.65,width/2-.65):box((x,0,.43),(1.3,height,.70),'tg_frame',.09)
 for y in (-height/2+.65,height/2-.65):box((0,y,.43),(width-2.6,1.3,.70),'tg_frame',.09)
 count=max(1,math.ceil(width/62));panelwidth=(width-3.4)/count
 for j in range(count):
  mid=-width/2+1.7+panelwidth*(j+.5);left=mid-panelwidth/2+.16;right=mid+panelwidth/2-.16
  # Separate welded edge strips leave a narrow visible joint between panels.
  for x in (left+.28,right-.28):box((x,0,.44),(.56,height-3.2,.54),'tg_steel',.045)
  for y in (-height/2+2.0,height/2-2.0):box((mid,y,.44),(panelwidth-.65,.8,.54),'tg_steel',.045)
  bars=max(3,int((right-left-1.4)/2.35));spacing=(right-left-1.5)/bars
  for k in range(bars):
   x=left+.75+spacing*(k+.5)
   box((x,0,.44),(.35,height-4.6,.54),'tg_steel',.035)
  # Welded cross ties, deliberately lower than the load-bearing bars.
  ties=max(2,int((height-7)/10))
  for k in range(ties):
   y=-height/2+4+(height-8)*(k+.5)/ties
   box((mid,y,.34),(panelwidth-1.7,.23,.28),'tg_frame',.025)
  for x in (left+.8,right-.8):
   for y in (-height/2+2.0,height/2-2.0):
    at=c+P.v(x,y,.78)
    P.cylinder(m,at,.37,at[2],at[2]+.09,'tg_bolt',6,top='tg_bolt')
    P.torus(m,at,Z,.43,.045,'tg_bolt',16,5)
  # Recessed lifting eyes at opposite ends of each panel.
  for y in (-height/2+5,height/2-5):
   P.torus(m,c+P.v(mid,y,.62),Z,.62,.10,'tg_bolt',20,6)
 for mat,path in MATS.items():m.material_overrides[mat]=path;m.tile_overrides[mat]=18
 return m

"""Draw a new plan-coordinate locator diagram; no editing of screenshots."""
from pathlib import Path
import json,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[3];OUT=ROOT/'output/asset-improvement-20261030/column-base/location-review';OUT.mkdir(parents=True,exist_ok=True)
W,H=1400,1120;im=Image.new('RGB',(W,H),'#101923');d=ImageDraw.Draw(im)
scale=.27;ox=700;oy=90+2080*scale
def pt(x,y):return ox+x*scale,oy-y*scale
def rect(x,y,w,h,color,edge='#91a5b2',width=2):
    a=pt(x,y+h);b=pt(x+w,y);d.rectangle((*a,*b),fill=color,outline=edge,width=width)
def font(n,bold=False):return ImageFont.truetype('C:/Windows/Fonts/'+('arialbd.ttf' if bold else 'arial.ttf'),n)
def text(x,y,value,color='#e6eef4',size=22,bold=False):
    d.multiline_text(pt(x,y),value,font=font(size,bold),fill=color,anchor='mm',align='center',spacing=6)
def line(points,color,width=3):d.line([pt(*p) for p in points],fill=color,width=width)
def arrow(start,end,color,width=3):
    a=pt(*start);b=pt(*end);d.line((a,b),fill=color,width=width)
    vx,vy=b[0]-a[0],b[1]-a[1];length=math.hypot(vx,vy);vx/=length;vy/=length
    d.polygon((b,(b[0]-vx*16-vy*6,b[1]-vy*16+vx*6),(b[0]-vx*16+vy*6,b[1]-vy*16-vx*6)),fill=color)
rect(-1900,674,3800,1226,'#18384b','#49a9d4',3)
text(0,1400,'BLUE ACCELERATOR CHAMBER','#a7e4ff',29,True)
text(0,1180,'Behind the large observation window','#83b8cf',22)
rect(-1400,-900,2800,1550,'#263747')
for x,label in ((-1900,'WEST\nROOMS /\nSPAWN'),(1400,'EAST\nROOMS /\nSPAWN')):
    rect(x,-900,500,1550,'#202d3b');text(x+250,-120,label,size=19)
for x,y,w,h in ((-1400,-900,2800,350),(-1400,-550,400,850),(1000,-550,400,850),(-1400,300,2800,350)):
    rect(x,y,w,h,'#3c5161','#3c5161',1)
line([(-1400,662),(1400,662)],'#67d4ff',7);text(0,558,'OBSERVATION WINDOW','#b1e9ff',20)
text(0,-385,'CENTRAL ATRIUM\nLOWER FLOOR',size=25,bold=True)
text(0,-790,'UPPER WALKWAY ABOVE','#b8cbd7',18)
for x,y,w,h in ((-1000,-210,600,160),(400,40,600,160)):
    rect(x,y,w,h,'#79909f','#c4d7e2',2)
    for i in range(1,13):
        xx=x+w*i/13;line([(xx,y),(xx,y+h)],'#d1dde4',1)
    text(x+w/2,y+h+70,'STAIRS','#cbdbe5',16)
for x,y in ((-960,-500),(-960,300),(960,-500),(960,300)):
    rect(x-44,y-44,88,88,'#ffbd47' if (x,y)==(-960,-500) else '#91a0ab','#131b24',1)
cx,cy=pt(-960,-500);r=105*scale;d.ellipse((cx-r,cy-r,cx+r,cy+r),outline='#ffbd47',width=5)
text(-1170,-1130,'THIS COLUMN BASE\nGround floor, under the walkway','#ffbd47',24,True)
arrow((-1170,-980),(-960,-610),'#ffbd47',4)
cx,cy=pt(-250,-320);d.ellipse((cx-5,cy-5,cx+5,cy+5),fill='#93e0a5')
arrow((-250,-320),(-680,-430),'#93e0a5',3)
text(710,-1140,'Location-view camera','#a9e9b8',18)
arrow((610,-1050),(-250,-320),'#93e0a5',2)
d.text((W/2,37),'COLLIDER — WHERE THIS BASE IS',font=font(32,True),anchor='mm',fill='#e6eef4')
d.text((W/2,H-34),'Top-down schematic • original base is still in the saved map',font=font(21),anchor='mm',fill='#a1b4c3')
im.save(OUT/'locator.png')
(OUT/'locator-data.json').write_text(json.dumps({'basePlan':[-960,-500,0],'mainHall':[-1400,1400,-900,650],
    'atriumEdges':[-1000,1000,-550,300],'observationWindowNorth':662,'columnLocations':[[-960,-500],[-960,300],[960,-500],[960,300]],
    'viewEyePlan':[-250,-320,95],'savedAssetsChanged':False},indent=2)+'\n')
print('Created plan-coordinate locator diagram.')

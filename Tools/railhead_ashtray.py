"""Approved stainless smoking-area columns, exact prototype geometry and UVs."""
import math
import numpy as np
import map_kit as K
import railhead_map as R
import railhead_dress_detail as D
import riverdale_parts as G
def model(e=601.,n=-891.,z0=0.,r=4.,height=40.):
    target_origin=np.array((e,n,z0))
    m=K.Model();X,Y,Z=np.eye(3);O=np.array((601.,-891.,0.))
    def P(x,y,z):return O+np.array((x,y,z))
    def B(c,size,paint='rw_stainless',b=.07,axes=None):G.bevel_box(m,P(*c),axes or (X,Y,Z),size,paint,bevel=b)
    def turn(profile,paint='rw_stainless',c=(0,0,0),axis=Z,sides=64):G.lathe_axis(m,P(*c),axis,[(float(r),float(t)) for r,t in profile],paint,sides=sides)
    def ring(r,ri,z0,z1,paint='rw_stainless'):turn([(ri,z0),(r-.07,z0),(r,z0+.07),(r,z1-.07),(r-.07,z1),(ri,z1),(ri,z0)],paint)
    def at(r,a,z):return P(r*math.cos(a),r*math.sin(a),z)
    def patch(r,a,b,z0,z1,paint='rw_stainless',inside=False,steps=1):
     for i in range(steps):
      t0=a+(b-a)*i/steps;t1=a+(b-a)*(i+1)/steps;d0=np.array((math.cos(t0),math.sin(t0),0));d1=np.array((math.cos(t1),math.sin(t1),0));sign=-1 if inside else 1
      uv=[(r*t0/24,z0/24),(r*t1/24,z0/24),(r*t1/24,z1/24),(r*t0/24,z1/24)] if paint=='rw_stainless' else None
      D._face(m,paint,[at(r,t0,z0),at(r,t1,z0),at(r,t1,z1),at(r,t0,z1)],sign*(d0+d1),normals=[sign*d0,sign*d1,sign*d1,sign*d0],uv=uv)
    # Grounded rolled foot, shoe and four countersunk anchors.
    turn([(0,0),(5.25,0),(5.6,.15),(5.6,.4),(5.35,.6),(4.15,.6),(4,.85),(4,1.4),(0,1.4)])
    for a in (math.pi/4,3*math.pi/4,5*math.pi/4,7*math.pi/4):
     c=(4.8*math.cos(a),4.8*math.sin(a),.57)
     turn([(0,0),(.34,0),(.34,.10),(.22,.16),(0,.16)],'rw_steel_dark',c=c,sides=16)
     B((c[0],c[1],.735),(.35,.055,.018),'rw_black',.008)
    # Main sheet-metal shell. Its front access panel is genuinely separated.
    for k in range(64):
     a=2*math.pi*k/64;b=2*math.pi*(k+1)/64
     for z0,z1 in ((1.4,4.),(4.,26.),(26.,35.)):
      if z0==4 and 40<=k<56:continue
      patch(4,a,b,z0,z1)
    # An inset dark receiver sits behind the panel seams.
    patch(3.83,0,2*math.pi,3.9,26.1,'rw_black',steps=64)
    patch(3.995,5*math.pi/4+.018,7*math.pi/4-.018,4.12,25.88,steps=16)
    for z in (4.13,25.87):
     for k in range(16):
      a=5*math.pi/4+.018+(math.pi/2-.036)*k/16;b=5*math.pi/4+.018+(math.pi/2-.036)*(k+1)/16
      D._face(m,'rw_steel_dark',[at(3.87,a,z),at(3.995,a,z),at(3.995,b,z),at(3.87,b,z)],Z if z>20 else -Z)
    # Small hinges and cylinder lock on the curved access door.
    for z in (8.,22.):
     a=math.radians(227);c=at(4.025,a,z);rad=np.array((math.cos(a),math.sin(a),0));tan=np.array((-math.sin(a),math.cos(a),0))
     G.bevel_box(m,c,(tan,rad,Z),(.55,.22,2.5),'rw_steel_dark',bevel=.08)
     G.lathe_axis(m,c,Z,[(0.,-1.05),(.19,-1.05),(.19,1.05),(0.,1.05)],'rw_stainless',sides=20)
    turn([(0,0),(.43,0),(.48,.08),(.48,.24),(.40,.3),(0,.3)],'rw_steel_dark',c=(0,-3.995,23.2),axis=-Y,sides=32)
    B((0,-4.315,23.2),(.075,.03,.40),'rw_black',.012)
    # Yellow enamel band stays at the old height; its edges have rolled trim.
    patch(4.025,0,2*math.pi,28,30.5,'rw_line_yellow',steps=64)
    G.torus(m,P(0,0,28),Z,4.02,.045,'rw_steel_dark',seg=64,sides=6)
    G.torus(m,P(0,0,30.5),Z,4.02,.045,'rw_steel_dark',seg=64,sides=6)
    ring(4.10,3.48,34.8,35.15)
    # Eight actual side openings divided by cast supports; dark collector below.
    turn([(0,34.4),(3.22,34.4),(3.3,35.0),(3.3,38.7),(0,38.7)],'rw_black')
    for k in range(8):
     a=2*math.pi*k/8-.075;b=a+.15
     patch(4.,a,b,35.15,37.35,steps=3);patch(3.50,a,b,35.15,37.35,inside=True,steps=3)
     for t in (a,b):D._face(m,'rw_stainless',[at(3.5,t,35.15),at(4,t,35.15),at(4,t,37.35),at(3.5,t,37.35)],(-math.sin(t),math.cos(t),0) if t==b else (math.sin(t),-math.cos(t),0))
    ring(4.2,3.62,37.35,39.75)
    # Rolled top lip and a physically perforated removable tray.
    ring(4.2,3.55,39.7,40.)
    def clip_rect(poly,x0,x1,y0,y1):
     for axis,bound,greater in ((0,x0,True),(0,x1,False),(1,y0,True),(1,y1,False)):
      out=[]
      for a,b in zip(poly,poly[1:]+poly[:1]):
       ia=a[axis]>=bound if greater else a[axis]<=bound;ib=b[axis]>=bound if greater else b[axis]<=bound
       if ia:out.append(a)
       if ia!=ib:
        t=(bound-a[axis])/(b[axis]-a[axis]);out.append(a+(b-a)*t)
      poly=out
      if not poly:break
     return poly
    circle=[np.array((3.55*math.cos(2*math.pi*k/96),3.55*math.sin(2*math.pi*k/96))) for k in range(96)]
    holes=0
    for ix in range(-4,5):
     for iy in range(-4,5):
      cx,cy=ix*.9,iy*.9;corners=[np.array((cx+dx,cy+dy)) for dx,dy in ((-.45,-.45),(.45,-.45),(.45,.45),(-.45,.45))]
      poly=clip_rect(circle,cx-.45,cx+.45,cy-.45,cy+.45)
      if len(poly)<3:continue
      if max(np.linalg.norm(q) for q in corners)<=3.54:
       holes+=1
       for k in range(16):
        a,b=2*math.pi*k/16,2*math.pi*(k+1)/16
        da=np.array((math.cos(a),math.sin(a)));db=np.array((math.cos(b),math.sin(b)))
        oa=np.array((cx,cy))+da*.45/max(abs(da));ob=np.array((cx,cy))+db*.45/max(abs(db))
        qa=np.array((cx,cy))+da*.24;qb=np.array((cx,cy))+db*.24
        D._face(m,'rw_stainless',[P(*oa,39.94),P(*ob,39.94),P(*qb,39.94),P(*qa,39.94)],Z)
        D._face(m,'rw_steel_dark',[P(*qa,39.94),P(*qb,39.94),P(*qb,39.58),P(*qa,39.58)],np.r_[-(da+db),0])
      else:D._face(m,'rw_stainless',[P(*q,39.94) for q in poly],Z)
    # Two recessed screw heads hold the tray without blocking its perforations.
    for x in (-3.31,3.31):
     turn([(0,0),(.21,0),(.25,.06),(.20,.10),(0,.10)],'rw_steel_dark',c=(x,0,39.89),sides=20)
     B((x,0,40.005),(.25,.055,.015),'rw_black',.006)
    R.configure(m);m.tile_overrides['rw_stainless']=24.

    offset=K.uv_offset('ashtray')
    for paint,faces in m.polygons.items():
        for i,(points,normal) in enumerate(faces):
            if (paint,i) not in m.polygon_uvs:
                world=[K.to_world(p) for p in points];wn=K.to_world(normal);tile=m.tile_overrides[paint]
                m.polygon_uvs[(paint,i)]=[K.face_uv(p,wn,paint,offset,tile) for p in world]
    scale=np.array((r/4.,r/4.,height/40.));delta=target_origin
    for paint,faces in m.polygons.items():
        moved=[]
        for i,(points,normal) in enumerate(faces):
            nn=normal/scale;nn=nn/np.linalg.norm(nn)
            smooth=m.polygon_normals.get((paint,i))
            if smooth is not None:
                m.polygon_normals[(paint,i)]=[K.normalise(q/scale) for q in smooth]
            moved.append(([(p-O)*scale+delta for p in points],nn))
        m.polygons[paint]=moved
    return m

def append_to(target,e,n,z0=0.,r=4.,height=40.):
    target.collision_box((e-r,n-r,z0),(e+r,n+r,z0+height),D.METAL)
    m=model(e,n,z0,r,height)
    for paint,faces in m.polygons.items():
        alias='rh_as_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs[(paint,i)],normals=m.polygon_normals.get((paint,i)))

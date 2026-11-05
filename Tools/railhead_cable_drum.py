"""Approved east-yard cable reel: original wood finish with the new geometry."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
MAT="materials/railhead/cable-drum-v1"
def model():
    m=K.Model();A=np.array((1.,0.,0.));B=np.array((0.,1.,0.));Z=np.array((0.,0.,1.));C=np.array((1878.,-1632.,23.9))
    # Recover the installed reel's actual face mapping. The earlier proposal used
    # narrower, elongated grain and three tints; retain its shape with the original
    # unmodified material and original texture scale. Align the grain to the
    # physical boards so the texture's old diagonal seams do not cross them.
    timber_mapping={-1:np.array([[0.01418718077357361, -0.027843887719280872], [0.02784378435033119, 0.014187115728965694], [-17.303759202132888, 50.34228870153856]]),1:np.array([[-0.014187180773573423, 0.027843735460142204], [0.02784378435033119, 0.014187090950557035], [29.003270797867135, -40.54037705138993]])}
    def P(t,x,z):return C+A*t+B*x+Z*z
    def face(paint,pts,normal,uv=None):D._face(m,paint,pts,normal,uv=uv)
    def cyl(at,axis,length,r,paint,sides=20):G.lathe_axis(m,at,axis,[(0,0),(r,0),(r,length),(0,length)],paint,sides=sides)
    def clipped(poly,x0,x1):
     for bound,greater in ((x0,True),(x1,False)):
      result=[]
      for a,b in zip(poly,poly[1:]+poly[:1]):
       va=a[0]-bound;vb=b[0]-bound;ia=va>=-1e-8 if greater else va<=1e-8;ib=vb>=-1e-8 if greater else vb<=1e-8
       if ia:result.append(a)
       if ia!=ib:
        u=va/(va-vb);result.append(tuple(a[q]+u*(b[q]-a[q]) for q in range(2)))
      poly=result
      if len(poly)<3:return []
     return poly
    def draw_radial(paint,poly,t,normal):
     sign=1 if float(np.dot(normal,A))>0 else -1
     coeff=timber_mapping[sign]
     u_scale=np.linalg.norm(coeff[:2,0]);v_scale=np.linalg.norm(coeff[:2,1])
     face(paint,[P(t,x,z) for x,z in poly],normal,uv=[(x*u_scale+coeff[2,0],z*v_scale+coeff[2,1]) for x,z in poly])
    # Nine individual full-depth planks per flange, separated by narrow daylight
    # seams. Their centre opening stays open through both cheeks and the barrel.
    for sign in (-1,1):
     front=sign*15.4;back=sign*13.8
     for j in range(9):
      x0=-23.6+j*(47.2/9)+.035;x1=-23.6+(j+1)*(47.2/9)-.035
      paint=('timber_a','timber_c','timber_b','timber_a','timber_b','timber_c','timber_a','timber_c','timber_b')[j]
      for k in range(96):
       a0=math.tau*k/96;a1=math.tau*(k+1)/96
       radial=lambda r,a:(r*math.cos(a),r*math.sin(a))
       poly=clipped([radial(23.44,a0),radial(23.44,a1),radial(2.50,a1),radial(2.50,a0)],x0,x1)
       if poly:
        draw_radial(paint,poly,front,A*sign);draw_radial(paint,poly,back,-A*sign)
       # Chamfered outside rim, with the grain changing on the cut timber edge.
       for t0,r0,t1,r1 in ((front,23.44,front-sign*.16,23.6),(front-sign*.16,23.6,back+sign*.16,23.6),(back+sign*.16,23.6,back,23.44)):
        # Split the rim at each board boundary; no continuous disc bridges seams.
        p0=np.array(radial(r0,a0));p1=np.array(radial(r0,a1));q0=np.array(radial(r1,a0));q1=np.array(radial(r1,a1))
        lo,hi=0.,1.
        for edge0,edge1 in ((p0,p1),(q0,q1)):
         dx=edge1[0]-edge0[0]
         if abs(dx)<1e-8:
          if not x0<=edge0[0]<=x1:hi=-1
         else:
          aa=(x0-edge0[0])/dx;bb=(x1-edge0[0])/dx;lo=max(lo,min(aa,bb));hi=min(hi,max(aa,bb))
        if hi>lo:
         aa=p0+(p1-p0)*lo;bb=p0+(p1-p0)*hi;cc=q0+(q1-q0)*hi;dd=q0+(q1-q0)*lo
         face(paint,[P(t0,*aa),P(t0,*bb),P(t1,*cc),P(t1,*dd)],B*math.cos((a0+a1)/2)+Z*math.sin((a0+a1)/2))
      # The timber's sawn plank edges are visible inside the narrow seams.
      for xx,norm in ((x0,-B),(x1,B)):
       if abs(xx)>=23.44:continue
       zmax=math.sqrt(23.44**2-xx**2)
       intervals=[(-zmax,zmax)] if abs(xx)>=2.5 else [(-zmax,-math.sqrt(2.5**2-xx**2)),(math.sqrt(2.5**2-xx**2),zmax)]
       for z0,z1 in intervals:face(paint,[P(back,xx,z0),P(front,xx,z0),P(front,xx,z1),P(back,xx,z1)],norm)
     # A steel axle sleeve is an annulus, not a painted dot covering the bore.
     G.lathe_axis(m,P(sign*13.65,0,0),A*sign,[(2.50,0),(3.10,0),(3.28,.18),(3.28,1.55),(3.10,1.78),(2.50,1.78),(2.50,0)],'steel',sides=48)
     # Recessed washers, hexagonal nuts and their dark central stud ends.
     for k in range(6):
      a=k*math.tau/6+.20;x=13.0*math.cos(a);z=13.0*math.sin(a)
      cyl(P(front+sign*.025,x,z),A*sign,.065,.88,'recess',32)
      cyl(P(front+sign*.09,x,z),A*sign,.10,.78,'steel',32)
      cyl(P(front+sign*.19,x,z),A*sign,.38,.50,'steel',6)
      cyl(P(front+sign*.58,x,z),A*sign,.025,.21,'recess',16)
     # Small, separate fixing nails along the upper and lower plank edges.
     for j in range(1,8):
      x=-23.6+(j+.5)*47.2/9;zz=math.sqrt(23.44**2-x*x)-1.5
      for z in (-zz,zz):cyl(P(front+sign*.025,x,z),A*sign,.045,.12,'steel',10)
     # Stencilled inventory number on the timber, below the hub.
     D.stroke_text(m,'recess','01',P(front+sign*.025,-3,-19),B,Z,2.8,1.7,.19,gap=.65)
    # The barrel's timber core and the wound cable have a true open axle bore.
    G.lathe_axis(m,P(-13.8,0,0),A,[(2.50,0),(11.,0),(11.,27.6),(2.50,27.6),(2.50,0)],'timber_b',sides=64)
    G.lathe_axis(m,P(-13.50,0,0),A,[(11.,0),(14.80,0),(14.80,27.),(11.,27.)],'cable',sides=64)
    # A continuous twelve-turn helix exposes the cable jacket between the cheeks.
    turns=12;path=[]
    for u in np.linspace(0,1,turns*72+1):
     a=math.tau*turns*u;path.append(P(-12.50+25*u,16.0*math.cos(a),16.0*math.sin(a)))
    D.tube(m,path,1.02,'cable',sides=10)
    D.disc(m,'cable',path[0],K.normalise(path[0]-path[1]),1.02,10)
    D.disc(m,'cable',path[-1],K.normalise(path[-1]-path[-2]),1.02,10)
    m.material_overrides={p:MAT+'/'+p+'.vmat' for p in ('timber_a','timber_b','timber_c','cable','steel','recess')}
    m.tile_overrides={p:32 for p in m.polygons}
    return m

def append_to(target):
    legacy=K.Model();D.cable_drum(legacy,1878.,-1632.,.3,'e')
    target.boxes.extend(legacy.boxes);target.hulls.extend(legacy.hulls)
    m=model()
    for paint,faces in m.polygons.items():
        alias="rh_cd_"+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))

"""Approved east Railhead brick pallet, preserving its original collider."""
import math
import numpy as np
import map_kit as K
import railhead_dress_detail as D
import riverdale_parts as G
import belltower_furniture as F
def model():
    m=K.Model();frame=D.Frame(1884.,-1580.,.3,'+n');X,Y,Z=frame.x,frame.y,frame.z
    def P(x,y,z):return frame.p(x,y,z)
    def wood(c,size,seed):F.bevel_box(m,P(*c),(X,Y,Z),size,F.WOOD,bevel=.10,seed=seed)
    def box(c,size,paint,b=.04):G.bevel_box(m,P(*c),(X,Y,Z),size,paint,bevel=b)
    # Three bottom runners, nine bearing blocks, cross bearers and seven deck boards.
    for i,x in enumerate((-15.4,0.,15.4)):
     wood((x,0,.425),(4.8,47.2,.85),i+1)
     for j,y in enumerate((-18.3,0.,18.3)):wood((x,y,2.15),(4.8,6.,2.60),i*3+j+6)
    for j,y in enumerate((-18.3,0.,18.3)):wood((0,y,3.625),(39.4,5.,.35),j+20)
    for k,x in enumerate(np.linspace(-17.3,17.3,7)):
     wood((x,0,4.25),(4.8,47.2,.9),k+30)
     for y in (-18.3,0.,18.3):
      for dx in (-1.25,1.25):D.disc(m,'steel',P(x+dx,y,4.71),Z,.075,10)
    # UV patches lie inside the existing dressed-red image's individual blocks,
    # excluding its photographed mortar lines. The material/textures are unchanged.
    patches=((.03,.03,.20,.18),(.27,.03,.56,.18),(.62,.04,.82,.18),(.03,.24,.36,.38),(.42,.24,.66,.38),(.73,.25,.94,.38),(.05,.44,.21,.56),(.27,.44,.55,.56),(.62,.44,.94,.56))
    def brick(x,y,z,turn,seed,top=False):
     axes=(X,Y,Z) if not turn else (Y,-X,Z);size=np.array((9.4,4.6,2.64));centre=P(x,y,z)
     u0,v0,u1,v1=patches[seed%len(patches)]
     def uv(points,normal):
      nn=np.array([np.dot(normal,a) for a in axes]);dominant=int(np.argmax(np.abs(nn)));a,b=[i for i in range(3) if i!=dominant]
      return [(u0+(np.dot(q-centre,axes[a])/size[a]+.5)*(u1-u0),v0+(np.dot(q-centre,axes[b])/size[b]+.5)*(v1-v0)) for q in points]
     start=len(m.polygons['brick'])
     G.bevel_box(m,centre,axes,size,'brick',bevel=.075,skip=('+z',) if top else ())
     for index in range(start,len(m.polygons['brick'])):
      points,normal=m.polygons['brick'][index];m.polygon_uvs[('brick',index)]=uv(points,normal)
     if top:
      # A true recessed frog in each top brick, with sloping walls and a floor.
      def at(a,b,h):return centre+axes[0]*a+axes[1]*b+Z*h
      outer=[(-4.625,-2.225),(4.625,-2.225),(4.625,2.225),(-4.625,2.225)]
      opening=[(-3.30,-1.15),(3.30,-1.15),(3.30,1.15),(-3.30,1.15)]
      bottom=[(-3.05,-.90),(3.05,-.90),(3.05,.90),(-3.05,.90)]
      def face(points,normal):D._face(m,'brick',points,normal,uv=uv(points,normal))
      for k in range(4):
       j=(k+1)%4
       face([at(*outer[k],1.32),at(*outer[j],1.32),at(*opening[j],1.32),at(*opening[k],1.32)],Z)
       points=[at(*opening[k],1.32),at(*opening[j],1.32),at(*bottom[j],.82),at(*bottom[k],.82)]
       middle=(np.array(opening[k])+np.array(opening[j]))/2;hint=-axes[0]*middle[0]-axes[1]*middle[1]+Z*.5
       face(points,hint)
      face([at(a,b,.82) for a,b in bottom],Z)
    count_bricks=0
    for row in range(13):
     turn=row%2;nx,ny=(4,10) if not turn else (8,5);stepx,stepy=(9.54,4.68) if not turn else (4.72,9.44)
     for ix in range(nx):
      for iy in range(ny):
       x=(ix-(nx-1)/2)*stepx;y=(iy-(ny-1)/2)*stepy
       brick(x,y,4.7+row*2.72+1.32,turn,row*47+ix*13+iy*7,top=row==12);count_bricks+=1
    # Thin strapping wraps the brick stack and passes below the timber deck.
    def band(fixed,along_y=True,layer=0.):
     span=23.60 if along_y else 19.25;top=40.06+layer
     path=[(-span,4.3),(-span,top-.45),(-span+.45,top),(span-.45,top),(span,top-.45),(span,4.3),(span-.45,3.92),(-span+.45,3.92)]
     def at(w,a,z):return P(fixed+w,a,z) if along_y else P(a,fixed+w,z)
     axis=Y if along_y else X
     for (a,z),(b,zz) in zip(path,path[1:]+path[:1]):
      hint=axis*(-(zz-z))+Z*(b-a)
      D._face(m,'strap',[at(-.38,a,z),at(.38,a,z),at(.38,b,zz),at(-.38,b,zz)],hint)
    for x in (-9.6,9.6):
     band(x)
     box((x,0,40.13),(1.05,2.1,.12),'steel',.025)
     for y in (-.78,.78):box((x,y,40.205),(.75,.08,.035),'strap',.008)
    for y in (-11.5,11.5):band(y,False,.035)
    m.material_overrides={F.WOOD:'materials/railhead/rw_wood.vmat','brick':'materials/railhead/rw_dressed_red.vmat','strap':'materials/railhead/rw_black.vmat','steel':'materials/railhead/rw_steel_dark.vmat'}
    m.tile_overrides={paint:32 for paint in m.polygons}
    return m

def append_to(target):
    legacy=K.Model();D.brick_pallet(legacy,1884.,-1580.,.3,'n')
    target.boxes.extend(legacy.boxes);target.hulls.extend(legacy.hulls)
    m=model()
    for paint,faces in m.polygons.items():
        alias='rh_bp_'+paint
        target.material_overrides[alias]=m.material_overrides[paint]
        target.tile_overrides[alias]=m.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=m.polygon_uvs.get((paint,i)),normals=m.polygon_normals.get((paint,i)))

"""Rounded, fluted bronze entrance planters. Plan coordinates, inches.

Only the render shell changes; reefhall_map keeps the original soil and metal hull.
"""
import math
import numpy as np
import map_kit as K
import riverdale_parts as P

MATS = {'rhp_bronze':'materials/reefhall/bronze-planter-v1/bronze.vmat',
        'rhp_edge':'materials/reefhall/bronze-planter-v1/edge.vmat',
        'rhp_toe':'materials/reefhall/bronze-planter-v1/toe.vmat'}
CENTRES = ((-2885.5625,-98.75,0.),(-2885.5625,98.75,0.))

def perimeter(half, radius, depth):
    """Counterclockwise rounded square, with six recessed flutes on each flat."""
    points=[]
    for side in range(4):
        angle=side*math.pi/2; c,s=math.cos(angle),math.sin(angle)
        def turn(x,y):return (c*x-s*y,s*x+c*y)
        for j in range(36):
            t=j/36
            recess=depth*math.sin(math.pi*t*6)**4
            points.append(turn(-half+radius+(2*half-2*radius)*t,-half+recess))
        for j in range(8):
            a=-math.pi/2+j*math.pi/16
            points.append(turn(half-radius+radius*math.cos(a),-half+radius+radius*math.sin(a)))
    return points

def shell(model, centre=(0,0,0), z=0., width=21.875, height=46.25, foot=.8):
    e,n=centre[:2]; z+=centre[2] if len(centre)>2 else 0
    t=width/2; b=t*foot; h=height
    # Profile travels up the outside, around a rolled lip, and down its inner return.
    half=lambda zz:b+(t-b)*zz/(h-1.2)-.07
    profile=[(0,b-.22,1.1,0,'rhp_toe'),(.22,b-.18,1.1,0,'rhp_toe'),
      (1.6,b-.18,1.1,0,'rhp_toe'),(1.85,b+.015,1.15,0,'rhp_edge'),
      (2.2,half(2.2),1.25,0,'rhp_bronze'),(3.0,half(3.0),1.25,.18,'rhp_bronze'),
      (4.1,half(4.1),1.25,.28,'rhp_bronze'),(h-4.0,half(h-4.0),1.45,.28,'rhp_bronze'),
      (h-2.7,half(h-2.7),1.45,.18,'rhp_bronze'),(h-1.65,t-.09,1.5,0,'rhp_bronze'),
      (h-1.5,t+.12,1.55,0,'rhp_edge'),(h-1.25,t+.30,1.6,0,'rhp_edge'),
      (h-.75,t+.35,1.65,0,'rhp_edge'),(h-.23,t+.18,1.6,0,'rhp_edge'),
      (h,t-.12,1.55,0,'rhp_edge'),(h-.06,t-.45,1.35,0,'rhp_edge'),
      (h-.4,t-.65,1.15,0,'rhp_bronze'),(h-1.82,t-.65,1.15,0,'rhp_bronze')]
    rings=np.array([[(e+x,n+y,z+zz) for x,y in perimeter(r,radius,depth)] for zz,r,radius,depth,_ in profile])
    # Area weighted smooth vertex normals, split at the underside of the toe only.
    normals=np.zeros_like(rings); count=rings.shape[1]
    for a in range(len(profile)-1):
        for j in range(count):
            k=(j+1)%count
            normal=np.cross(rings[a,k]-rings[a,j],rings[a+1,j]-rings[a,j])
            for aa,jj in ((a,j),(a,k),(a+1,j),(a+1,k)):normals[aa,jj]+=normal
    normals/=np.maximum(np.linalg.norm(normals,axis=2)[:,:,None],1e-10)
    for a in range(len(profile)-1):
        for j in range(count):
            k=(j+1)%count
            inds=((a,j),(a,k),(a+1,k),(a+1,j)); pts=[rings[aa,jj] for aa,jj in inds]
            model.polygon(profile[a+1][4],pts,normals=[normals[aa,jj] for aa,jj in inds],
              uv=[(j/count*4,profile[a][0]/24),((j+1)/count*4,profile[a][0]/24),
                  ((j+1)/count*4,profile[a+1][0]/24),(j/count*4,profile[a+1][0]/24)])
    model.material_overrides.update(MATS)
    model.tile_overrides.update({paint:24.0 for paint in MATS})
    return model

def original(model, centre=(0,0,0), z=0., width=21.875, height=46.25, foot=.8):
    """Frozen original shell, without soil or collider, for exact face replacement."""
    import reefhall_map as R
    e,n=centre[:2];z+=centre[2] if len(centre)>2 else 0
    t,b,z1=width/2,width/2*foot,z+height
    corners=lambda r,zz:[(e-r,n-r,zz),(e+r,n-r,zz),(e+r,n+r,zz),(e-r,n+r,zz)]
    low,high=corners(b,z),corners(t,z1-1.2)
    for k in range(4):
        quad=[low[k],low[(k+1)%4],high[(k+1)%4],high[k]];mid=np.mean(quad,axis=0)
        R.facing(model,'rh_bronze',quad,(mid[0]-e,mid[1]-n,0))
    model.box((e-t-.35,n-t-.35,z1-1.2),(e+t+.35,n+t+.35,z1),{'default':'rh_bronze','-z':None})
    soil=z1-1.8
    for k in range(4):
        inner=corners(t-.6,soil)+corners(t-.6,z1+.01)
        quad=[inner[k],inner[(k+1)%4],inner[4+(k+1)%4],inner[4+k]];mid=np.mean(quad,axis=0)
        R.facing(model,'rh_bronze',quad,(e-mid[0],n-mid[1],0))
    return model

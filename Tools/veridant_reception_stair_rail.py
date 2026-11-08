"""Smooth black steel reception handrail with side-mounted anchor plates."""
import math
import numpy as np
import veridant_parts as P

def tube(m,a,b,r,paint='vr_steel',sides=24):
    a,b=np.array(a,float),np.array(b,float)
    P.tube(m,[a,b],[r,r],paint,sides=sides,cap=True,smooth=True)
    d=(b-a)/np.linalg.norm(b-a);u,_=P.P.perp(d);w=np.cross(d,u)
    P.card(m,paint,[a+r*(u*math.cos(t)+w*math.sin(t)) for t in np.linspace(0,2*math.pi,sides,endpoint=False)],-d)

def rounded_cap(m,p,d,r,paint='vr_steel'):
    p=np.array(p,float);d=np.array(d,float);d/=np.linalg.norm(d);u,_=P.P.perp(d);w=np.cross(d,u)
    rings=[]
    for theta in np.linspace(0,math.pi/2,7)[:-1]:
        row=[]
        for a in np.linspace(0,2*math.pi,24,endpoint=False):
            n=d*math.sin(theta)+(u*math.cos(a)+w*math.sin(a))*math.cos(theta)
            row.append((p+r*n,n))
        rings.append(row)
    for a,b in zip(rings,rings[1:]):
        for i in range(24):
            j=(i+1)%24;points=[a[i][0],a[j][0],b[j][0],b[i][0]];normals=[a[i][1],a[j][1],b[j][1],b[i][1]]
            P.card(m,paint,points,sum(normals),normals=normals)
    for i in range(24):
        j=(i+1)%24;P.card(m,paint,[rings[-1][i][0],rings[-1][j][0],p+d*r],rings[-1][i][1]+rings[-1][j][1]+d,normals=[rings[-1][i][1],rings[-1][j][1],d])

def build_into(m):
    a=np.array((-83.,260.,48.2));b=np.array((-83.,447.,169.2));d=(b-a)/np.linalg.norm(b-a)
    tube(m,a,b,.85,sides=32);rounded_cap(m,a,-d,.85);rounded_cap(m,b,d,.85)
    tube(m,(-83,260,28.84),(-83,447,149.84),.45,sides=20)
    for i in range(5):
        f=i/4;n=263+181*f;top=48.2+(n-260)*121/187
        # Match each fixing to the actual 17-tread stair profile, not the slope approximation.
        step=min(17,int(math.floor((n-260)/(187/17)))+1);floor=128/17*step
        bottom=max(0,floor-9)
        m.box((-83.9,n-2.5,bottom),(-83.3,n+2.5,floor-.35),'vr_steel')
        tube(m,(-83,n,bottom+1),(-83,n,top-.45),.7,sides=24)
        for nn in (n-1.65,n+1.65):
            for zz in (bottom+1.25,floor-1.6):
                tube(m,(-83.28,nn,zz),(-82.96,nn,zz),.22,'vr_mast',6)

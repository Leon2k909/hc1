"""A suspended cloth banner retaining Veridant's original printed atlas and mounting."""
import math
import numpy as np
import veridant_materials as VM

def build_into(m,centre_top=(10,-418,392),right=(-1,0,0),height=200,name='banner'):
    top=np.array(centre_top,float);r=np.array(right,float);r/=np.linalg.norm(r)
    up=np.array((0.,0.,1.));out=np.cross(r,up);width=height*VM.aspect(VM.PRINTS,name)
    def point(s,t):
        free=(1-t)
        # Attached flat along the top rod; free cloth gains broad, irregular billows.
        bow=6.0*math.sin(math.pi*free*.7)*math.sin(2*math.pi*s*1.15+.45+free*.8)
        bow+=1.8*free*math.sin(2*math.pi*s*3.1-free*.7)
        bow+=4.5*free
        sag=3.0*free*free*math.sin(math.pi*s)**2
        return top+r*((s-.5)*width)-up*(1+height*free+sag)+out*(4+bow)
    def normal(s,t):
        eps=.0001;ds=point(s+eps,t)-point(s-eps,t);dt=point(s,t+eps)-point(s,t-eps)
        n=np.cross(ds,dt);return n/np.linalg.norm(n)
    def uv(s,t):return VM.atlas_uv(VM.PRINTS,VM.PRINT_ATLAS,name,s,t)
    ss=np.linspace(0,1,25);ts=np.linspace(0,1,49)
    for s0,s1 in zip(ss,ss[1:]):
        for t0,t1 in zip(ts,ts[1:]):
            st=((s0,t0),(s1,t0),(s1,t1),(s0,t1));p=[point(s,t) for s,t in st];n=[normal(s,t) for s,t in st]
            m.polygon('vr_print',p,normal=out,uv=[uv(s,t) for s,t in st],normals=n)
            m.polygon('vr_black',[x-out*.08 for x in p[::-1]],normal=-out,normals=[-x for x in n[::-1]])
    for s in (0,1):
        for t0,t1 in zip(ts,ts[1:]):
            a,b=point(s,t0),point(s,t1);n=r*(1 if s==1 else -1)
            q=[a,b,b-out*.08,a-out*.08]
            if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),n)<0:q.reverse()
            m.polygon('vr_black',q,normal=n)
    for t in (0,1):
        for s0,s1 in zip(ss,ss[1:]):
            a,b=point(s0,t),point(s1,t);n=up*(1 if t==1 else -1)
            q=[a,b,b-out*.08,a-out*.08]
            if np.dot(np.cross(q[1]-q[0],q[2]-q[0]),n)<0:q.reverse()
            m.polygon('vr_black',q,normal=n)

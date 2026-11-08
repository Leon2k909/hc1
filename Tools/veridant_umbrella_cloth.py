"""Gathered burgundy canopy, close-fitting tie and rib caps for Veridant's terrace umbrella."""
import math
import numpy as np
from scipy.interpolate import PchipInterpolator
import veridant_parts as P

def build_into(m,base=(30,470),height=182,z0=128):
    centre=np.array((base[0],base[1],z0+height),float)
    profile=PchipInterpolator([0,.06,.18,.34,.54,.72,.86,1],[.9,2.3,4.,6.7,9.,10.6,10.,8.])
    def point(a,t,offset=0):
        phase=8*a+.28*math.sin(math.pi*t)
        gathered=.8+.2*math.cos(phase)
        radius=float(profile(t))*gathered
        radius*=1-.14*math.exp(-((t-.62)/.04)**2)
        radius+=offset
        z=-83*t-1.8*t**7*(.5+.5*math.cos(8*a))
        # Slight irregularity breaks the turned-object symmetry without changing the footprint.
        radius+=.14*math.sin(3*a+7*t)*math.sin(math.pi*t)
        return centre+np.array((radius*math.cos(a),radius*math.sin(a),z))
    def normal(a,t):
        d=.0001;da=point(a+d,t)-point(a-d,t);dt=point(a,t+d)-point(a,t-d)
        n=np.cross(dt,da);return n/np.linalg.norm(n)
    aa=np.linspace(0,2*math.pi,65);tt=np.linspace(0,1,33)
    for a0,a1 in zip(aa,aa[1:]):
        for t0,t1 in zip(tt,tt[1:]):
            st=((a0,t0),(a0,t1),(a1,t1),(a1,t0))
            m.polygon('vr_umbrella',[point(a,t) for a,t in st],normal=normal((a0+a1)/2,(t0+t1)/2),normals=[normal(a,t) for a,t in st],both_sides=True)
    # A strap follows the actual compressed folds rather than floating as a round hoop.
    for a0,a1 in zip(aa,aa[1:]):
        st=((a0,.608),(a0,.632),(a1,.632),(a1,.608))
        m.polygon('vr_umbrella_tie',[point(a,t,.11) for a,t in st],normal=normal((a0+a1)/2,.62),normals=[normal(a,t) for a,t in st])
    # Sewn panel ridges use the original darker cloth; these are fine cords, not hard ribs.
    for k in range(8):
        points=[]
        for t in np.linspace(.1,1,24):
            a=2*math.pi*k/8-.28*math.sin(math.pi*t)/8
            points.append(point(a,t,.045))
        P.tube(m,points,[.045]*len(points),'vr_umbrella_tie',sides=5,cap=True)
    # A small folded end to the tie, visible on the approach side.
    a=math.pi;anchor=point(a,.62,.13)
    m.box((anchor[0]-.07,anchor[1]-1.1,anchor[2]-1.4),(anchor[0]+.07,anchor[1]+1.1,anchor[2]+.8),'vr_umbrella_tie')
    # Retain the original tip locations with smoother steel and small protective caps.
    for k in range(8):
        a=2*math.pi*k/8+math.pi/8;d=np.array((math.cos(a),math.sin(a),0.))
        start=centre+d*9+np.array((0,0,-79));end=centre+d*10.5+np.array((0,0,-84))
        P.tube(m,[start,end],[.35,.35],'vr_steel',sides=12,cap=True)
        end2=end+(end-start)/np.linalg.norm(end-start)*.6
        P.tube(m,[end,end2],[.42,.36],'vr_black',sides=12,cap=True)

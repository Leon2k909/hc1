"""Steel saddle plates fixing the terrace's timber beams to their post caps."""
from riverdale_parts import box,lathe_axis
def build_into(m):
    for e in (-680,-520):
        for n in (88,177):
            for s in (-1,1):
                a,b=sorted((n+s*4.05,n+s*4.5))
                box(m,e-4.5,e+4.5,a,b,242.5,251.5,'vr_steel')
                for x in (-2.7,2.7):
                    for z in (245,249):
                        c=(e+x,n+s*4.5,z)
                        lathe_axis(m,c,(0,s,0),[(.5,0),(.5,.14)],'vr_steel',24,cap='vr_steel')
                        lathe_axis(m,c,(0,s,0),[(.34,.14),(.34,.47),(.28,.53)],'vr_steel',6,cap='vr_steel')

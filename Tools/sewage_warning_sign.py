"""Folded safety-board hardware; plan coordinates match Sewage's original warning face."""
import math
import numpy as np
import map_kit as K

MATERIALS = {
    'ww_sign_frame': 'materials/sewage/pipe-texture-v1/pipe.vmat',
    'ww_sign_metal': 'materials/sewage/crane-blocks-v1/steel.vmat',
    'ww_sign_rust': 'materials/sewage/rust.vmat',
    'ww_sign_recess': 'materials/sewage/crane-blocks-v1/dark.vmat',
}


def rod(m, a, b, radius, paint, sides=12):
    a, b = np.array(a, float), np.array(b, float)
    axis = K.normalise(b-a)
    u = K.normalise(np.cross(axis, (0, 0, 1) if abs(axis[2]) < .95 else (0, 1, 0)))
    v = np.cross(axis, u)
    ring = [u*math.cos(t)+v*math.sin(t) for t in np.linspace(0, math.tau, sides, endpoint=False)]
    for i in range(sides):
        j=(i+1)%sides
        m.polygon(paint, [a+ring[i]*radius,a+ring[j]*radius,b+ring[j]*radius,b+ring[i]*radius],
                  normals=[ring[i],ring[j],ring[j],ring[i]])
    m.polygon(paint, [a+r*radius for r in reversed(ring)])
    m.polygon(paint, [b+r*radius for r in ring])


def outline(e, width, height, chamfer):
    # Clockwise as seen from the front (-e); each list has the same corner indexing.
    w,h,c=width/2,height/2,chamfer
    return [np.array((e,n,z)) for n,z in (
        (-w+c,-h),(-w,-h+c),(-w,h-c),(-w+c,h),
        (w-c,h),(w,h-c),(w,-h+c),(w-c,-h))]


def join(m, a, b, paint):
    for i in range(len(a)):
        j=(i+1)%len(a)
        m.polygon(paint,[a[i],a[j],b[j],b[i]])


def emit(m, centre=(-615,-400,35)):
    """Add only hardware. The original lettering/UVs remain the sign's front face."""
    local=K.Model()
    local.material_overrides.update(MATERIALS)
    local.tile_overrides.update({p:48 for p in MATERIALS})
    front=outline(.10,110.6,65.6,1.1)
    rear=outline(1.65,110.6,65.6,1.1)
    # Plate sits behind the existing face, which remains at local e=0.
    local.polygon('ww_sign_frame',list(reversed(front)))
    local.polygon('ww_sign_frame',rear)
    join(local,front,rear,'ww_sign_frame')
    # Rolled sheet rim: back return, curved bevel and narrow forward-facing lip.
    loops=[outline(1.9,112.8,67.8,1.65),outline(-.15,112.8,67.8,1.65),
           outline(-.6,111.9,66.9,1.4),outline(-.6,109.1,64.1,.9),outline(.12,108.9,63.9,.8)]
    for i in range(len(loops)-1):
        join(local,loops[i],loops[i+1],'ww_sign_metal' if i==2 else 'ww_sign_frame')
    # Two pressed rear channels, with open ends and returns rather than solid bars.
    for n in (-38,38):
        local.box((1.65,n-2.0,-29),(2.05,n+2.0,29),'ww_sign_frame')
        for side in (-1,1):
            local.box((2.05,n+side*1.65-.18,-29),(4.6,n+side*1.65+.18,29),'ww_sign_metal')
            local.box((4.3,n+side*1.65-.5,-29),(4.7,n+side*1.65+.5,29),'ww_sign_frame')
        # Four saddle clamps wrap the existing handrail tubes, radius 1.8, at z=20/42.
        for z in (-15,7):
            local.box((3.5,n-2.9,z-3.5),(4.2,n+2.9,z+3.5),'ww_sign_metal')
            path=[]
            for t in np.linspace(-math.pi/2,math.pi/2,17):
                path.append((5+2.45*math.cos(t),n,z+2.45*math.sin(t)))
            for a,b in zip(path,path[1:]):rod(local,a,b,.25,'ww_sign_metal',8)
            for dz in (-2.45,2.45):
                rod(local,(3.0,n,z+dz),(5,n,z+dz),.25,'ww_sign_metal',10)
                rod(local,(2.65,n,z+dz),(3.35,n,z+dz),.65,'ww_sign_rust',6)
    # Six recessed washers and hex heads. Their scale suits the 2.8 m wide sign.
    for n in (-50,50):
        for z in (-27,0,27):
            rod(local,(-.10,n,z),(-.46,n,z),1.05,'ww_sign_recess',20)
            rod(local,(-.46,n,z),(-.64,n,z),.94,'ww_sign_metal',24)
            rod(local,(-.64,n,z),(-1.20,n,z),.68,'ww_sign_rust',6)
            local.box((-1.23,n-.38,z-.06),(-1.19,n+.38,z+.06),'ww_sign_recess')
    delta=np.array(centre,float)
    for paint,faces in local.polygons.items():
        for i,(pts,normal) in enumerate(faces):
            m.polygon(paint,[p+delta for p in pts],normal=normal,
                      uv=local.polygon_uvs.get((paint,i)),normals=local.polygon_normals.get((paint,i)))
    m.material_overrides.update(local.material_overrides)
    m.tile_overrides.update(local.tile_overrides)
    return m

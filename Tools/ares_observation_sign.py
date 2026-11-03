"""Approved Ares observation sign geometry. Plan inches; native import is renderer-only."""
import numpy as np
import map_kit as K
import boxyard_map as BY
MAT='materials/ares/observation-sign-v1'
def model():
    m=K.Model()
    def P(x,depth,z):return np.array((x,600-depth,420+z),float)
    def outline(w,h,c):
        return [(-w/2+c,-h/2),(w/2-c,-h/2),(w/2,-h/2+c),(w/2,h/2-c),(w/2-c,h/2),(-w/2+c,h/2),(-w/2,h/2-c),(-w/2,-h/2+c)]
    def ring(w,h,c,depth):return [P(x,depth,z) for x,z in outline(w,h,c)]
    def join(a,b,paint):
        for j in range(8):m.polygon(paint,[a[j],a[(j+1)%8],b[(j+1)%8],b[j]])
    def shell():
        # Closed rear, chamfered powder-coated casting, inset rubber seal and lens lip.
        a,b,c,e=ring(190,46,3,-3.2),ring(194,50,4,-1.2),ring(194,50,4,1.8),ring(190,46,3,3.1)
        m.polygon('dark',a[::-1]);join(a,b,'alloy');join(b,c,'panel');join(c,e,'panel')
        f=ring(181.5,40.5,1.6,3.1);join(e,f,'panel')
        g=ring(180.5,39.5,1.3,2.7);join(f,g,'gasket')
        h=ring(180,39,1.1,2.65);join(g,h,'dark')
        # Recessed face does not share a plane with the frame.
        m.polygon('face',[P(-90,2.64,-19.5),P(90,2.64,-19.5),P(90,2.64,19.5),P(-90,2.64,19.5)],normal=(0,-1,0),uv=[(0,0),(1,0),(1,1),(0,1)])
    shell()
    def box(x,d,z,w,depth,h,paint):
        m.oriented_box(P(x,d,z),((1,0,0),(0,1,0),(0,0,1)),(w,depth,h),paint)
    def rod(a,b,r,paint,sides=12):BY.rod(m,a,b,r,paint,sides=sides)
    # Captive fasteners sit on the metal margin, with recessed dark slots.
    for x in (-93,93):
        for z in (-17,17):
            rod(P(x,3.08,z),P(x,3.26,z),.85,'alloy',12)
            box(x,3.28,z,.75,.03,.14,'dark')
    # Cast end caps and rear service panel, deliberately kept within the old outer envelope.
    for x in (-96,96):
        for z in (-11,-5,1,7,13):box(x,0,z,.22,2.5,.65,'dark')
    box(0,-3.3,0,156,.16,30,'dark')
    for x in (-74,74):
        for z in (-11,11):rod(P(x,-3.4,z),P(x,-3.6,z),.55,'alloy',10)
    # Two real cable grips, retaining collars and ceiling plates replace the bare rods.
    for x in (-80,80):
        rod(P(x,1.2,24),P(x,1.2,29),1.5,'alloy',16)
        rod(P(x,1.2,29),P(x,1.2,32),1.05,'dark',12)
        rod(P(x,1.2,32),P(x,1.2,296),.42,'alloy',12)
        rod(P(x,1.2,293),P(x,1.2,298),1.1,'alloy',12)
        box(x,1.2,299,8,6,2,'panel')
        for dx in (-2.6,2.6):rod(P(x+dx,1.2,297.8),P(x+dx,1.2,298.1),.4,'dark',8)
    m.material_overrides={'face':MAT+'/face.vmat','panel':'materials/ares/interior-v1/panel.vmat','alloy':'materials/ares/interior-v1/alloy.vmat','dark':'materials/ares/interior-v1/dark.vmat','gasket':'materials/ares/ar_black.vmat'}
    m.tile_overrides={p:32 for p in m.polygons}
    return m

def append_to(target):
    source=model()
    for paint,faces in source.polygons.items():
        alias='ar_os_'+paint
        target.material_overrides[alias]=source.material_overrides[paint]
        target.tile_overrides[alias]=source.tile_overrides[paint]
        for i,(points,normal) in enumerate(faces):
            target.polygon(alias,points,normal,uv=source.polygon_uvs.get((paint,i)),normals=source.polygon_normals.get((paint,i)))

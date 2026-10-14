"""Reef Hall's operator furniture and restrained LCD material definitions.

The screen atlas is an ImageGen original, mapped by quadrant without resampling.
Geometry is built in the room's local frame; the existing cover hulls are kept.
"""
import math

RESOURCE_DIR = "materials/reefhall/consoles"
SCREEN = "rh_console_lcd"
FINISHES = {
    "rh_console_shell": ((0.52, 0.56, 0.57), 0.56, 0.05),
    "rh_console_worktop": ((0.69, 0.71, 0.70), 0.47, 0.0),
    "rh_console_edge": ((0.29, 0.33, 0.34), 0.40, 0.15),
    "rh_console_bezel": ((0.10, 0.12, 0.13), 0.56, 0.0),
    "rh_console_keys": ((0.60, 0.63, 0.62), 0.67, 0.0),
    "rh_console_status": ((0.15, 0.42, 0.31), 0.45, 0.0),
    "rh_console_amber": ((0.68, 0.34, 0.09), 0.50, 0.0),
}


def configure(model):
    for paint in (*FINISHES, SCREEN):
        model.material_overrides[paint] = f"{RESOURCE_DIR}/{paint}.vmat"
        model.tile_overrides[paint] = 24.0


def materials():
    """Source strings for the editor import and for reproducible staged builds."""
    out = {}
    for paint, (rgb, rough, metal) in FINISHES.items():
        color = "[" + " ".join(f"{v:.4f}" for v in rgb) + " 1.0]"
        glow = 0.35 if paint == "rh_console_status" else 0
        out[paint] = material(color, rough, metal, glow)
    out[SCREEN] = material(f"{RESOURCE_DIR}/rh_console_screen_atlas.png", 0.42, 0, 0.85)
    return out


def material(color, rough, metal, glow):
    lines = ["// Tools/reefhall_consoles.py", '"Layer0"', "{",
             '    shader "shaders/complex.shader"', '    F_SPECULAR "1"',
             f'    TextureColor "{color}"',
             '    TextureNormal "materials/default/default_normal.tga"',
             f'    TextureRoughness "[{rough} {rough} {rough} 1.0]"',
             '    TextureAmbientOcclusion "[1.0 1.0 1.0 1.0]"',
             f'    g_flMetalness "{metal}"', '    g_flRoughnessScaleFactor "1"',
             '    g_vColorTint "[1.0 1.0 1.0 1.0]"']
    if glow:
        lines += ['    F_SELF_ILLUM "1"', '    TextureSelfIllumMask "[1.0 1.0 1.0 1.0]"',
                  f'    g_flSelfIllumBrightness "{glow}"', '    g_flSelfIllumAlbedoFactor "1.0"',
                  '    g_vSelfIllumTint "[1.0 1.0 1.0 1.0]"']
    return "\n".join(lines + ["}", ""])


def build(model, centre, length, yaw=0.0, z=0.0):
    # Imported here to avoid the map/consoles module import cycle.
    import reefhall_map as R
    fr = R.Frame(centre[:2], (math.cos(math.radians(yaw)), math.sin(math.radians(yaw))))
    h = length / 2
    shell, top, edge, bezel, keys = ("rh_console_" + p for p in ("shell", "worktop", "edge", "bezel", "keys"))
    configure(model)

    def box(a, b, c, d, lo, hi, paint, surface=None):
        R.fbox(model, fr, a, b, c, d, z + lo, z + hi, paint, surface)

    def face(paint, points, towards):
        R.facing(model, paint, [fr.p(u, w, z + zz) for u, w, zz in points], fr.vec(*towards))

    def chamfered_panel(a, b, w0, w1, lo, hi, radius, paint):
        outline = [(a+radius,lo),(b-radius,lo),(b,lo+radius),(b,hi-radius),
                   (b-radius,hi),(a+radius,hi),(a,hi-radius),(a,lo+radius)]
        for w, sign in ((w0,-1),(w1,1)):
            face(paint, [(u,w,zz) for u,zz in outline], (0,sign,0))
        for (u0,z0),(u1,z1) in zip(outline,outline[1:]+outline[:1]):
            face(paint, [(u0,w0,z0),(u1,w0,z1),(u1,w1,z1),(u0,w1,z0)], (z1-z0,0,u0-u1))

    # Solid service cabinet: retain the original desk and cover collision exactly.
    box(-h,h,-16,16,0,30,shell,R.METAL)
    box(-h+2,h-2,-12,14,0,4.5,bezel)
    box(-h-2,h+2,-18,-16,5,27.8,shell)
    box(-h-2,h+2,-18.1,-17.95,27.8,28.4,bezel)
    box(-h-2,h+2,-18,17,29.3,30.7,edge)
    box(-h-1.5,h+1.5,-17.5,16.5,30.7,32.2,top)
    # Rear cable trough, with individual hatch seams and a satin lip.
    box(-h,h,5,16,32.2,36,edge)
    box(-h,h,5,15.7,36,36.3,top)

    bays = max(1, round(length / 92))
    width = length / bays
    for k in range(bays):
        c = -h + width * (k + 0.5)
        a,b = c-width/2+1.2,c+width/2-1.2
        # The inset paired access doors, folded edges, latches and ventilation slots.
        for left,right in ((a,c-0.35),(c+0.35,b)):
            R.fbox(model,fr,left,right,-18.6,-18.1,z+6,z+27,shell,skip=("back",))
            def door_face(lo,hi,paint,x0=left,x1=right):
                face(paint,[(x0,-18.6,lo),(x1,-18.6,lo),
                            (x1,-18.6,hi),(x0,-18.6,hi)],(0,-1,0))
            # Tessellate the front rather than stacking nearly coplanar decals:
            # these narrow vents must remain stable from across the room.
            door_face(6,6.3,edge)
            last = 6.3
            for slot in range(6):
                zz = 9 + slot*0.85
                door_face(last,zz,shell)
                door_face(zz,zz+0.28,shell,left,left+3)
                door_face(zz,zz+0.28,bezel,left+3,right-3)
                door_face(zz,zz+0.28,shell,right-3,right)
                last = zz+0.28
            door_face(last,27,shell)
            latch = right-2.0
            box(latch-0.5,latch+0.5,-19.1,-18.6,21.5,23.8,edge)
        box(a,a+0.3,5,15.7,36.3,36.36,bezel)
        # A compact keyboard and wrist rest, with real key caps at believable scale.
        ku = c-9
        box(ku-10.8,ku+10.8,-14,-5,32.2,32.8,bezel)
        box(ku-10.5,ku+10.5,-14,-12.2,32.8,33.05,edge)
        for row in range(4):
            for col in range(13):
                u = ku-9.75+col*1.5+(0.22 if row%2 else 0)
                w = -11.6+row*1.5
                box(u,u+1.25,w,w+1.18,32.8,33.22,keys)
        box(ku-4,ku+4,-13.2,-12.0,33.05,33.4,keys)
        # Trackball and a small operator panel: no luminous tabletop texture.
        box(c+4,c+11,-13.8,-5.4,32.2,32.8,edge)
        # A shallow hemispherical trackball, not a cylindrical push button.
        for ring in range(5):
            phi0,phi1 = ring*math.pi/10,(ring+1)*math.pi/10
            for seg in range(16):
                theta0,theta1 = seg*math.pi/8,(seg+1)*math.pi/8
                points=[]
                for phi,theta in ((phi0,theta0),(phi0,theta1),(phi1,theta1),(phi1,theta0)):
                    points.append(fr.p(c+7.5+1.35*math.cos(phi)*math.cos(theta),
                                       -8.7+1.35*math.cos(phi)*math.sin(theta),z+32.8+1.35*math.sin(phi)))
                normals=[R.normalise(p-fr.p(c+7.5,-8.7,z+32.8)) for p in points]
                model.polygon(keys,points,normals=normals)
        box(c+14,c+27,-13.8,-3.8,32.2,33.1,bezel)
        for row in range(3):
            for col in range(3):
                u,w = c+15.2+col*3.7,-12.4+row*2.65
                paint = "rh_console_amber" if row==0 and col==2 else keys
                box(u,u+2.7,w,w+1.75,33.1,33.4,paint)
        # Small folded side cheeks give the desk a readable manufactured edge.
        if k < bays-1:
            box(b+0.9,b+1.2,-17.5,16.5,30.7,32.3,edge)

    count = max(1,int(length/44))
    for k in range(count):
        u = -h+length*(k+0.5)/count
        box(u-7,u+7,6,14,36.3,36.9,bezel)
        box(u-1.0,u+1.0,9.9,12.2,36.9,47.0,edge)
        chamfered_panel(u-19.4,u+19.4,8.8,11.6,42.6,66,0.65,bezel)
        # A thicker rear electronics housing, mounting plate and ventilation ribs.
        chamfered_panel(u-13,u+13,11.6,13.3,46,61,0.7,edge)
        for rib in range(7):
            box(u-9,u+9,13.3,13.36,49+rib*1.1,49.3+rib*1.1,bezel)
        slot = (k + (2 if length < 200 else 0) + (1 if centre[1]<0 else 0)) % 4
        s0 = (slot%2)*0.5+0.0015
        s1 = (slot%2+1)*0.5-0.0015
        t0 = (0.5 if slot<2 else 0)+0.0015
        t1 = t0+0.497
        points = [fr.p(u-18.2,8.74,z+44.3),fr.p(u+18.2,8.74,z+44.3),
                  fr.p(u+18.2,8.74,z+64.775),fr.p(u-18.2,8.74,z+64.775)]
        R.uv_quad(model,SCREEN,points,[(s0,t0),(s1,t0),(s1,t1),(s0,t1)],fr.vec(0,-1,0))
        box(u+16.8,u+17.15,8.70,8.74,43.25,43.5,"rh_console_status")
        # Cable descending behind the stand, visible from the tank side.
        box(u+1.6,u+2.05,11.7,12.15,36.3,46,bezel)
    # The map's authored solid cover stays unchanged; this is a visual replacement.
    import numpy as np
    model.boxes.append((fr.p(0,0,z+33),((*fr.d,0.0),(*fr.f,0.0),(0.0,0.0,1.0)),
                        np.array((length+4,36,66)),R.METAL))

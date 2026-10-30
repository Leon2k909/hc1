"""Collider ceiling fabrication. Render geometry only; no lights or collision."""
from pathlib import Path
import numpy as np
from PIL import Image
import map_kit as K
import boxyard_map as B
import collider_finish as F
import collider_services as S

MATERIAL_DIR = 'materials/collider/ceiling-v1'
TILES = {'ch_soffit':64., 'ch_housing':32., 'ch_lens':32.}
UP = np.array((0., 0., 1.))
BEAMS = tuple(range(-1200, 1201, 300))
STATIONS = (-820., -420., 0., 460.)
PANELS = ((-1424.,1424.,-924.,690.,900.),
          (-1900.,-1424.,-900.,980.,880.), (1424.,1900.,-900.,980.,880.))


def configure(model):
    F.configure(model)
    for name,tile in TILES.items():
        if name in model.polygons:
            model.material_overrides[name] = f'{MATERIAL_DIR}/{name}.vmat'
            model.tile_overrides[name] = tile
    return model


def old_blocks():
    model = K.Model()
    for e in BEAMS:
        for n in STATIONS:
            model.box((e-14,n-5,828), (e+14,n+5,866), 'co_trim')
    return model


def old_parts(published=False):
    model=old_blocks()
    for e in BEAMS:
        if published:
            # The installed legacy mesh uses a solid beam envelope, whereas
            # the maintained generator already describes three flange/web parts.
            model.box((e-9,-900,866),(e+9,650,900),'co_steel')
        else:
            model.box((e-3,-900,872),(e+3,650,894),'co_steel')
            for z in (866,894):
                model.box((e-12,-900,z),(e+12,650,z+6),'co_trim')
    return model


def is_panel(points,normal):
    p = np.asarray(points)
    if normal[2] > -.99 or np.ptp(p[:,2]) > .001:
        return False
    lo,hi = p.min(0),p.max(0)
    return any(abs(lo[2]-z)<.001 and e0-.001<=lo[0] and hi[0]<=e1+.001
        and n0-.001<=lo[1] and hi[1]<=n1+.001 for e0,e1,n0,n1,z in PANELS)


def bolt(model,at,normal,r=.45):
    """Small closed low-poly hex heads, with a drive on the exposed face."""
    normal = K.normalise(normal)
    B.lathe(model,at,normal,[(r,0),(r,.20)],'cf_stainless',sides=6,cap='cf_stainless')


def block(model,lo,hi,paint='ch_housing',bevel=.12):
    F.block(model,lo,hi,paint,bevel)


def fixture(model,e,n):
    # Two flange clamps and paired yokes. The old 38-inch solid hanging block
    # becomes a bracket, heat sink and recessed two-channel LED luminaire.
    for side in (-1,1):
        a=e+side*10
        block(model,(a-2,n-5,864.7),(a+2,n+5,867.4),bevel=.10)
        block(model,(a-.65,n-4,835),(a+.65,n+4,865),bevel=.12)
        bolt(model,(a,n-3,867.4),UP,.50)
        bolt(model,(a,n+3,867.4),UP,.50)
        bolt(model,(a+side*.66,n,843),(side,0,0),.55)
    model.box((e-16,n-9,828),(e+16,n+9,836),
        {'default':'ch_housing','-z':None})
    # Extruded cooling fins and separate end plates explain the upper housing.
    for off in (-11,-6.5,-2,2,6.5,11):
        model.box((e+off-.38,n-6.5,836),(e+off+.38,n+6.5,840),'ch_housing')
    for side in (-1,1):
        block(model,(e+side*15-.6,n-8.5,828.7),(e+side*15+.6,n+8.5,836.6),bevel=.18)
    # Raised sealing rim surrounds actual recessed lenses, rather than a painted
    # white rectangle covering the bottom of an otherwise featureless box.
    for a,b in ((-15,-13),(13,15)):
        block(model,(e+a,n-7.8,827.7),(e+b,n+7.8,829.1),bevel=.18)
    for a,b in ((-7.8,-6),(-.6,.6),(6,7.8)):
        block(model,(e-13,n+a,827.7),(e+13,n+b,829.1),bevel=.15)
    for a,b in ((-6,-.6),(.6,6)):
        model.box((e-12.9,n+a+.1,829),(e+12.9,n+b-.1,829.15),'ch_lens')
    for de in (-14,14):
        for dn in (-7,7):
            bolt(model,(e+de,n+dn,827.68),-UP,.30)
    # A driver enclosure, cable gland and short swept conduit meet the supply
    # running along the beam. No free ends and no added runtime point lights.
    block(model,(e+16.1,n-3,830),(e+20.5,n+3,836.8),bevel=.35)
    B.lathe(model,(e+18.3,n+3,834),(0,1,0),[(.85,0),(.85,1.4)],
        'cf_gasket',sides=8,cap='cf_gasket')
    S.pipe_run(model,[(e+18.3,n+4.4,834),(e+18.3,n+11,834),
        (e+18.3,n+11,875)],.46,'cf_frame',sides=8,bend=4)


def panels(model):
    """Closed, recessed joint beds and lips; no coplanar joint decals."""
    for e0,e1,n0,n1,z in PANELS:
        es = [e0]+[float(e) for e in np.arange(-1800,1900,150) if e0<e<e1]+[e1]
        ns = [n0]+[float(n) for n in (-550,-200,150,500,850) if n0<n<n1]+[n1]
        for a,b in zip(es,es[1:]):
            for c,d in zip(ns,ns[1:]):
                # The slab's original upper surface and all physics stay intact.
                # Joint relief travels upward into the existing slab by .26in.
                lo=(a+.16 if a>e0 else a,c+.16 if c>n0 else c)
                hi=(b-.16 if b<e1 else b,d-.16 if d<n1 else d)
                model.polygon('ch_soffit',[(lo[0],lo[1],z),(lo[0],hi[1],z),
                    (hi[0],hi[1],z),(hi[0],lo[1],z)],-UP)
                for axis,val,start,end in ((0,lo[0],lo[1],hi[1]),(0,hi[0],lo[1],hi[1]),
                        (1,lo[1],lo[0],hi[0]),(1,hi[1],lo[0],hi[0])):
                    if (axis==0 and val in (e0,e1)) or (axis==1 and val in (n0,n1)):
                        continue
                    if axis==0:
                        pts=[(val,start,z),(val,end,z),(val,end,z+.26),(val,start,z+.26)]
                        normal=(1 if val==hi[0] else -1,0,0)
                    else:
                        pts=[(start,val,z),(end,val,z),(end,val,z+.26),(start,val,z+.26)]
                        normal=(0,1 if val==hi[1] else -1,0)
                    B.card(model,'ch_soffit',pts,normal)
        for e in es[1:-1]:
            model.polygon('cf_gasket',[(e-.16,n0,z+.26),(e-.16,n1,z+.26),
                (e+.16,n1,z+.26),(e+.16,n0,z+.26)],-UP)
        for n in ns[1:-1]:
            # Short separate runs meet the e joints, avoiding crossing faces.
            for a,b in zip(es,es[1:]):
                model.polygon('cf_gasket',[(a+.16,n-.16,z+.26),(a+.16,n+.16,z+.26),
                    (b-.16,n+.16,z+.26),(b-.16,n-.16,z+.26)],-UP)


def additions():
    model=K.Model()
    panels(model)
    for e in BEAMS:
        block(model,(e-3,-900,872),(e+3,650,894),bevel=.12)
        for z in (866,894):
            block(model,(e-12,-900,z),(e+12,650,z+6),bevel=.16)
        # The supply is visibly clipped to the beam's flange, not suspended
        # as an unconnected cable. Slightly offset from the existing web.
        S.pipe_run(model,[(e+18.3,-890,875),(e+18.3,640,875)],.65,
            'cf_frame',sides=8,bend=4)
        for n in (-880,-600,-200,200,620):
            model.box((e+10,n-1.3,873.8),(e+19.4,n+1.3,876.3),'ch_housing')
            bolt(model,(e+12,n,876.3),UP,.42)
        for n in STATIONS:
            fixture(model,e,n)
        # Thin web stiffeners and small seated end plates replace the reading
        # of three unrelated cuboids forming a beam. They meet both flanges.
        for n in (-880,630):
            model.box((e-11.5,n-.4,872),(e+11.5,n+.4,894),'ch_housing')
            for de in (-8,8):
                for z in (876,890):
                    bolt(model,(e+de,n-.41,z),(0,-1,0),.42)
    return configure(model)


def refine_structure(model):
    # Exact original signatures limit removal to this ceiling's 36 old blocks.
    def signature(p,points):
        return p,tuple(sorted(tuple(np.round(x,3)) for x in points))
    old={signature(p,points) for p,items in old_parts().polygons.items() for points,_ in items}
    replacement=K.Model()
    removed=0
    for paint,items in model.polygons.items():
        for i,(points,normal) in enumerate(items):
            if signature(paint,points) in old or (paint=='co_steel' and is_panel(points,normal)):
                removed+=1
                continue
            replacement.polygon(paint,points,normal,uv=model.polygon_uvs.get((paint,i)),
                normals=model.polygon_normals.get((paint,i)))
    assert removed==36*6+9*3*6+3, ('Unexpected ceiling source',removed)
    extra=additions()
    replacement.extend(extra)
    model.polygons=replacement.polygons
    model.polygon_uvs=replacement.polygon_uvs
    model.polygon_normals=replacement.polygon_normals
    configure(model)


def materials(out):
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    # Neutral fine cast concrete, with physical shallow pore relief. This is
    # a dedicated surface; no shared steel or other-map material is altered.
    n=1024; rng=np.random.default_rng(283101)
    fine=rng.standard_normal((n,n)).astype(np.float32)
    smooth=sum(np.roll(np.roll(fine,a,0),b,1) for a in (-2,-1,0,1,2) for b in (-2,-1,0,1,2))/25
    pores=(rng.random((n,n))<.009).astype(np.float32)
    relief=smooth*.25-pores*.9
    delta=smooth*2.8+fine*.85-pores*5
    rgb=np.clip(np.array((137,140,137))[None,None,:]+delta[...,None],0,255).astype(np.uint8)
    Image.fromarray(rgb).save(out/'soffit_color.png')
    normal=np.stack(((np.roll(relief,1,1)-np.roll(relief,-1,1))*.035,
        (np.roll(relief,-1,0)-np.roll(relief,1,0))*.035,np.ones_like(relief)),axis=-1)
    normal/=np.linalg.norm(normal,axis=-1,keepdims=True)
    Image.fromarray(np.uint8(np.clip(normal*.5+.5,0,1)*255)).save(out/'soffit_normal.png')
    Image.fromarray(np.uint8(np.clip(.88+fine*.012+pores*.04,0,1)*255)).save(out/'soffit_rough.png')
    (out/'ch_soffit.vmat').write_text(F.vmat(f'{MATERIAL_DIR}/soffit_color.png',
        f'{MATERIAL_DIR}/soffit_normal.png',f'{MATERIAL_DIR}/soffit_rough.png'),encoding='utf-8')
    (out/'ch_housing.vmat').write_text(F.vmat('materials/collider/finish-v1/paint_color.png',
        rough='materials/collider/finish-v1/paint_rough.png',tint=(.70,.73,.74)),encoding='utf-8')
    lens=F.vmat('[0.72 0.77 0.78 1]',rough_value=.52)
    lens=lens.rsplit('}',1)[0]+'    F_SELF_ILLUM "1"\n    TextureSelfIllumMask "[1 1 1 1]"\n    g_flSelfIllumBrightness "0.65"\n    g_flSelfIllumAlbedoFactor "1"\n    g_vSelfIllumTint "[1 0.97 0.90 1]"\n}\n'
    (out/'ch_lens.vmat').write_text(lens,encoding='utf-8')
    return sorted(p for p in out.iterdir() if p.suffix in ('.png','.vmat'))

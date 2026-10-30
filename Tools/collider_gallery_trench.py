"""Fitted gallery trench covers; replaces the original disconnected strips only."""
from pathlib import Path
import numpy as np
import map_kit as K
import boxyard_map as B
import collider_finish as F

STEEL = 'co_drain_frame'
MATERIAL = 'materials/collider/co_drain_frame.vmat'
UP = np.array((0., 0., 1.))
LEVEL = 256.
BRANCHES = (-840., 590.)


def legacy(model):
    """Exact original authoring retained for a bounded installed-mesh migration."""
    for e in (-1320, 1320):
        model.box((e-12, -870, LEVEL+.12), (e+12, 610, LEVEL+.3), 'ar_grating')
        for n in range(-850, 601, 150):
            model.box((e-15, n-2, LEVEL+.3), (e+15, n+2, LEVEL+.6), 'co_silver')
    for n in BRANCHES:
        model.box((-1300, n-9, LEVEL+.12), (1300, n+9, LEVEL+.3), 'ar_grating')


def subtract(rect, hole):
    x0, x1, y0, y1 = rect
    a, b, c, d = hole
    a, b, c, d = max(a,x0), min(b,x1), max(c,y0), min(d,y1)
    if a >= b or c >= d:
        return [rect]
    return [r for r in ((x0,a,y0,y1), (b,x1,y0,y1), (a,b,y0,c), (a,b,d,y1))
            if r[1]-r[0] > 1e-6 and r[3]-r[2] > 1e-6]


def layout():
    # Branch ends now meet the inner edges exactly, eliminating the 8-inch breaks.
    decks = [(e-12,e+12,-870.,610.) for e in (-1320.,1320.)]
    decks += [(-1308.,1308.,n-9,n+9) for n in BRANCHES]
    rims, seams, screws = [], [], []
    rim = .72
    for e in (-1320.,1320.):
        outer, inner = (e-12,e+12) if e < 0 else (e+12,e-12)
        rims.append(tuple(sorted((outer,outer+(rim if e<0 else -rim))))+(-870.,610.))
        for lo, hi in ((-870.,-849.),(-831.,581.),(599.,610.)):
            rims.append(tuple(sorted((inner,inner+(-rim if e<0 else rim))))+(lo,hi))
        rims += [(e-12,e+12,-870.,-870.+rim),(e-12,e+12,610.-rim,610.)]
        for n in range(-700, 451, 150):
            # Narrow flush panel joints stay inside the channel, rather than
            # wide bright straps projecting onto the concrete on either side.
            seams.append((e-12+rim,e+12-rim,n-.24,n+.24))
            screws += [(e-12+rim*.5,n), (e+12-rim*.5,n)]
    for n in BRANCHES:
        rims += [(-1308.,1308.,n-9,n-9+rim),(-1308.,1308.,n+9-rim,n+9)]
        for e in range(-1100,1101,200):
            seams.append((e-.24,e+.24,n-9+rim,n+9-rim))
            screws += [(e,n-9+rim*.5),(e,n+9-rim*.5)]
    return decks, rims, seams, screws


def append(model):
    decks, rims, seams, screws = layout()
    for deck in decks:
        pieces = [deck]
        for metal in rims+seams:
            pieces = [p for piece in pieces for p in subtract(piece,metal)]
        for x0,x1,y0,y1 in pieces:
            model.box((x0,y0,LEVEL+.12),(x1,y1,LEVEL+.30),'ar_grating')
    for x0,x1,y0,y1 in rims:
        F.block(model,(x0,y0,LEVEL+.07),(x1,y1,LEVEL+.34),STEEL,.075)
    for x0,x1,y0,y1 in seams:
        # Two fitted metal lips separated by a 2 mm dark joint; no overlapping faces.
        if x1-x0 > y1-y0:
            mid=(y0+y1)/2
            pairs=[(x0,x1,y0,mid-.04),(x0,x1,mid+.04,y1)]
        else:
            mid=(x0+x1)/2
            pairs=[(x0,mid-.04,y0,y1),(mid+.04,x1,y0,y1)]
        model.box((x0,y0,LEVEL+.13),(x1,y1,LEVEL+.17),'co_rubber')
        for a,b,c,d in pairs:
            F.block(model,(a,c,LEVEL+.17),(b,d,LEVEL+.30),STEEL,.035)
    for x,y in screws:
        p=np.array((x,y,LEVEL+.335))
        B.lathe(model,p,UP,[(.145,0),(.145,.018),(.12,.035)],STEEL,sides=10,cap=STEEL)
        # A small recessed drive breaks up the highlight without oversized bolts.
        B.card(model,'co_rubber',[(x-.075,y-.015,LEVEL+.371),(x+.075,y-.015,LEVEL+.371),
                                (x+.075,y+.015,LEVEL+.371),(x-.075,y+.015,LEVEL+.371)],UP)
    model.material_overrides[STEEL]=MATERIAL
    model.tile_overrides[STEEL]=12.


def materials(out):
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    text=F.vmat('materials/railhead/rw_galvanised_color.png',
                'materials/railhead/rw_galvanised_normal.png',
                'materials/railhead/rw_galvanised_rough.png',metalness=.80,
                tint=(.86,.88,.90),scale=64/12)
    (out/'co_drain_frame.vmat').write_text(text,encoding='utf-8')

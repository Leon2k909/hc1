"""Construction details on Railhead's existing bridge and central columns.

The geometry is visual only: flanges, stiffeners, connections and cast collars.
It stays above passage headroom or on existing column bases. No collision.
"""
from pathlib import Path
import argparse
import json
import map_kit as K
import railhead_station as S

ROOT=Path(__file__).resolve().parents[1]
STEEL='rw_steel_dark'
BOLT='rw_steel_grey'


def bolt(model,e,n,z,outward,radius=.38):
    S.tube(model,(e,n,z),(e,n+outward*.32,z),radius,BOLT,sides=8,cap=True)


def _runs(r0,r1,gaps):
    out,at=[],r0
    for a,b in sorted(gaps):
        if b<=at or a>=r1: continue
        if a-at>2: out.append((at,a))
        at=max(at,b)
    if r1-at>2: out.append((at,r1))
    return out


def build():
    model=K.Model()
    # The plate girders carry real flange lips and web stiffeners. Keep the
    # existing stair openings in the parapet clear.
    for n,side in ((S.BRIDGE_N0,-1),(S.BRIDGE_N1,1)):
        for z in (S.DECK_Z-32,S.DECK_Z-2):
            model.box((-S.WALL_IN,n-2.0,z),(S.WALL_IN,n+2.0,z+1.2),STEEL)
        for e in range(-1120,1121,80):
            a,b=sorted((n+side*.08,n+side*2.2))
            model.box((e-1.2,a,S.DECK_Z-30.8),(e+1.2,b,S.DECK_Z-2),STEEL)
            for z in (S.DECK_Z-27,S.DECK_Z-7):
                bolt(model,e,n+side*2.22,z,side)
        # Break the parapet into plausible folded panels, with narrow raised
        # seams. A seam is never placed in a stair's access opening.
        stairs=[(a,b,d) for a,b,d in S.BRIDGE_STAIRS if (d>0)==(side>0)]
        gaps=[(sign*a,sign*b) for a,b,d in stairs for sign in (-1,1)]
        gaps=[(min(a,b)-6,max(a,b)+6) for a,b in gaps]
        for e in range(-1120,1121,80):
            if any(a-2<e<b+2 for a,b in gaps): continue
            a,b=sorted((n+side*.08,n+side*.65))
            model.box((e-.65,a,S.DECK_Z+1),(e+.65,b,247),STEEL)
        # The parapet plate's edge angles, riveted at 6 inches, broken at the stairs' openings.
        import railhead_profiles as P
        for z0,z1,zr in ((S.DECK_Z+0.2,S.DECK_Z+3.2,S.DECK_Z+1.7),(244.0,247.6,245.8)):
            for a,b in _runs(-S.WALL_IN,S.WALL_IN,gaps):
                lo,hi=sorted((n+side*.08,n+side*.9))
                model.box((a,lo,z0),(b,hi,z1),STEEL)
                e=a+3.0
                while e<b-2:
                    P.rivet(model,(e,n+side*.9,zr),(0,side,0),radius=.42,height=.3,paint=STEEL)
                    e+=6.0
    # Bolted bearing shoes and knee braces on the seven pairs of supports.
    for e in (-935.,-755.,-510.,0.,510.,755.,935.):
        for n in (S.BRIDGE_N0+4,S.BRIDGE_N1-4):
            model.box((e-6.5,n-6.5,174),(e+6.5,n+6.5,179.5),STEEL)
            for side in (-1,1):
                model.beam((e+side*5,n,143),(e+side*31,n,178),(2.0,2.0),STEEL)
            for de in (-7,7):
                for dn in (-7,7):
                    model.cylinder((e+de,n+dn),.62,3.05,3.9,BOLT,sides=6)
    # The shed columns' bases and capitals are moulded (railhead_architecture.shed_column). Their holding-down bolts
    # are cast into the plinth (its 30 in square leaves no ledge for nuts), so none are drawn here.
    assert not model.boxes and not model.hulls
    return model


def write_brick_material(mdir):
    """ rw_brick is railhead_finish's now (Reichsformat cross bond): write it there rather than the old scan copy. """
    import railhead_finish
    railhead_finish.brick(mdir)
    return


def _old_brick_material(mdir):
    material=(ROOT/'Assets/materials/railhead/rw_signal_box_brick.vmat').read_text(encoding='utf-8')
    # Existing building-brick UVs tile over 64 inches. The already installed
    # Poly Haven scan represents 55.11811 inches: preserve its measured size.
    scale=64/55.11811
    material=material.replace('// Tools/railhead_signal_box.py','// Tools/railhead_ironwork.py; same CC0 scan as railhead_signal_box_sources.json')
    material=material.replace('    g_flMetalness',f'    g_vTexCoordScale "[{scale:.7f} {scale:.7f}]"\n    g_flMetalness')
    mdir.mkdir(parents=True,exist_ok=True)
    (mdir/'rw_brick.vmat').write_text(material,encoding='utf-8')


def stage(destination):
    import railhead_map as R
    model=R.configure(build())
    out=destination/'models/maps/railhead'
    out.mkdir(parents=True,exist_ok=True)
    K.write_model(out,'models/maps/railhead','railhead_ironwork',model)
    write_brick_material(destination/'materials/railhead/finish')
    remapped=[]
    for source in (ROOT/'Assets/models/maps/railhead').glob('*.vmdl'):
        old=source.read_text(encoding='utf-8')
        new=old.replace('materials/buildings/brick.vmat','materials/railhead/finish/rw_brick.vmat')
        if new!=old:
            (out/source.name).write_text(new,encoding='utf-8',newline='\n')
            remapped.append(source.name)
    (destination.parent/'ironwork.json').write_text(json.dumps({'triangles':model.triangle_count(),'collision_shapes':0,'brick_remaps':remapped},indent=2),encoding='utf-8')
    print(model.triangle_count(),'visual triangles;',len(remapped),'brick remaps; no collision')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage',type=Path,default=ROOT/'output/railhead/quality/ironwork-stage')
    stage(parser.parse_args().stage)

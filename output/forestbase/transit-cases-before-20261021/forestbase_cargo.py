"""Reference-oriented loading islands, merged into the existing two chunks.

Six deliberate cover pockets retain the central lanes and marked door bays.
All dimensions are inches. No new scene objects, bitmaps or buildings.
"""
ISLANDS=(
    ('yard','motor north stock',(-1230,-105),2,2,1,3),
    ('yard','motor east loading',(-630,-155),2,2,2,-5),
    ('logistics','central receiving',(-250,500),2,2,2,4),
    # The original northing 480 overlapped the east command entrance stair.
    ('logistics','command service',(600,250),1,2,2,-4),
    ('logistics','workshop spares',(860,70),2,1,1,5),
    ('logistics','east lane stock',(760,-440),1,2,2,-7),
)


def build(target,chunk,api):
    for owner,name,center,rows,cols,tiers,angle in ISLANDS:
        if owner!=chunk:continue
        m=api['model'](not isinstance(target,api['CollisionOnlyModel']))
        box,bevel,panel=api['box'],api['bevel_box'],api['panel']
        width=128 if cols==2 else 80;depth=106 if rows==2 else 64
        # One low proxy covers the pallet deck; all crate boxes are separate.
        m.collision_box((-width/2,-depth/2,0),(width/2,depth/2,9),'wood')
        for e in (-width*.38,0,width*.38):
            box(m,(e-4,-depth/2,0),(e+4,depth/2,6),'timber')
        for k in range(9):
            n=-depth/2+4+(depth-8)*k/8
            box(m,(-width/2,n-3,6),(width/2,n+3,9),'timber')
        for r in range(rows):
            for c in range(cols):
                e=(c-(cols-1)/2)*58;n=(r-(rows-1)/2)*48
                for tier in range(tiers):
                    api['crate'](m,e,n,z=9+tier*48,w=56,h=48,
                                 paint=f'case_{(r+c+tier)%3}')
        front=-((rows-1)*48+56*.76)/2
        top=9+tiers*48
        # Bands follow the cases, not the wider pallet. Slight metal fittings
        # stay inside the authored crate proxy tolerance.
        for e in (-18,18) if cols==2 else (-12,12):
            box(m,(e-.6,front-.35,10),(e+.6,front-.08,top),'rubber')
            box(m,(e-.6,front,top+.05),(e+.6,-front,top+.32),'rubber')
            bevel(m,(e-2,front-.8,27),(e+2,front-.3,32),'case_hardware',.3)
        panel(m,[(-18,front-.85,31),(18,front-.85,31),(18,front-.85,47),(-18,front-.85,47)],
              'cargo_1' if chunk=='yard' else 'cargo_0')
        if tiers==1:
            # Small service cans break up the plain low stack silhouette.
            for e in (-12,12):
                bevel(m,(e-5,-8,top),(e+5,7,top+17),'olive',1,'metal')
                box(m,(e-3,-1,top+17),(e+3,2,top+20),'steel')
                box(m,(e-4,-8.3,top+5),(e+4,-8.1,top+6),'yellow')
        target.extend(api['transform'](m,(*center,0),angle))

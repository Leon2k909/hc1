"""Publish source edits atomically when editor indexing keeps old files mapped."""
from pathlib import Path

root=Path(__file__).resolve().parents[3]
replacements={
 'Tools/belltower_architecture.py':[(
'''    wall_moulding(model,wall,opening.r0-3,opening.r1+3,opening.z0-4,
        ((-.5,0),(1.65,0),(1.65,.5),(2.35,.5),(2.35,0),(2.65,0)),paint) if False else None
''','')],
 'Tools/belltower_map.py':[
('''            Architecture.shutter(model,wall,r0,r1,o.z0,o.z1,2.2,paint)''',
'''            angle = pick((0,0,12,25,42),"shutter_angle",wall.outward,wall.across[0],r0,o.z0) if o.z0>120 else 0
            left_leaf = r1 < o.r0
            Architecture.shutter(model,wall,r0,r1,o.z0,o.z1,2.2,paint,
                                 angle=-angle if left_leaf else angle,hinge=r1 if left_leaf else r0)'''),
('''                slab_at( model, wall, o.r0 - 3, o.r1 + 3, -0.5, 3.0, o.z0 - 4, o.z0, style.get( "sill", "ashlar" ) )''',
'''                Architecture.window_sill(model,wall,o,style.get("sill","ashlar"))'''),
('''            slab_at( model, wall, o.r0 - band, o.r0, 0.0, 1.5, o.z0, o.z1 + band, paint )
            slab_at( model, wall, o.r1, o.r1 + band, 0.0, 1.5, o.z0, o.z1 + band, paint )
            slab_at( model, wall, o.r0, o.r1, 0.0, 1.5, o.z1, o.z1 + band, paint )
            # Its hood: a little cornice over the head, which throws a line of shadow, where it clears the eaves and
            # the openings beside it.
            if o.z1 + band + 4.5 <= wall.z[1] and room_beside( wall, o.r0 - band - 2, o.r1 + band + 2 ):
                slab_at( model, wall, o.r0 - band - 2, o.r1 + band + 2, 0.0, 3.0, o.z1 + band, o.z1 + band + 2.5, paint )''',
'''            hood = o.z1 + band + 7 <= wall.z[1] and room_beside(wall,o.r0-band-2,o.r1+band+2)
            Architecture.window_surround(model,wall,o,paint,style.get("surround_profile",0),hood)'''),
('''    gutter = "copper_brown" if chance( 0.55, "gutter", e0, n0 ) else "metal"''',
'''    gutter = "copper_brown" if chance( 0.55, "gutter", e0, n0 ) else "metal"
    style["surround_profile"] = pick((0,1,2),"surround_profile",e0,n0)'''),
('''        slab_at( model, wall, *returned( wall.outward, *wall.run, eave - 24, 7.0 ), 0.0, 7.0, eave - 24, eave - 12, trim )''',
'''        Architecture.cornice(model,wall,*returned(wall.outward,*wall.run,eave-24,7.0),
                             eave-24,trim,style["surround_profile"])'''),
('''    model.box( ( e0 - 1.5, n0 - 1.5, z1 - 4 ), ( e1 + 1.5, n1 + 1.5, z1 ), cap, STONE )''',
'''    Architecture.coping(model,(e0-1.5,n0-1.5,z1-4),(e1+1.5,n1+1.5,z1),cap,STONE)'''),
('''    model.box( ( e - h - 2, n - h - 2, z0 + height ), ( e + h + 2, n + h + 2, z0 + height + 4 ), "ashlar_grey", STONE )''',
'''    Architecture.coping(model,(e-h-2,n-h-2,z0+height),(e+h+2,n+h+2,z0+height+4),"ashlar_grey",STONE)'''),
('''            model.box( ( r - 1.5, -1001.5, 28 ), ( g0 + ( 1.5 if g0 < 0 else 0 ), -986.5, 32 ), "ashlar_grey", STONE )''',
'''            Architecture.coping(model,(r-1.5,-1001.5,28),(g0+(1.5 if g0<0 else 0),-986.5,32),"ashlar_grey",STONE)'''),
 ]}
prepared=[]
for relative,edits in replacements.items():
    path=root/relative
    original=path.read_bytes()
    text=original.decode('utf-8')
    newline='\r\n' if '\r\n' in text else '\n'
    normalized=text.replace('\r\n','\n')
    for before,after in edits:
        expected=2 if 'style.get( "sill", "ashlar" )' in before else 1
        assert normalized.count(before)==expected,(relative,before[:70])
        normalized=normalized.replace(before,after)
    prepared.append((path,original,normalized.replace('\n',newline).encode('utf-8')))
for path,original,updated in prepared:
    assert path.read_bytes()==original
    temp=path.with_name(path.name+'.facades.tmp')
    temp.write_bytes(updated)
    temp.replace(path)
    print('Updated',path.relative_to(root))

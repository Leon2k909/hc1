from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];pp=ROOT/'Tools/riverside_parts.py';rp=ROOT/'Tools/riverside_map.py';p=pp.read_bytes();r=rp.read_bytes()
def change(d,a,b):
 a=a.encode();b=b.encode()
 if a not in d:a=a.replace(b'\n',b'\r\n');b=b.replace(b'\n',b'\r\n')
 assert d.count(a)==1,a[:90];return d.replace(a,b)
assert b'GRAFFITI_BOARDS = []' not in p
p=change(p,'WATER_TANKS = []','GRAFFITI_BOARDS = []    # approved STILL HERE plank board\nWATER_TANKS = []')
p=change(p,'    WATER_TANKS.clear()','    GRAFFITI_BOARDS.clear()\n    WATER_TANKS.clear()')
p=change(p,' + WATER_TANKS',' + WATER_TANKS + GRAFFITI_BOARDS')
p=change(p,'def park_sign( m, base, facing, scale=1.0, height=None ):','def park_sign( m, base, facing, scale=1.0, height=None, board_model=False ):')
a='''    obox( m, pc, right, ( pw, 1.5, ph ), "rs_plywood", WOOD )
    paint( m, "still_here", pc + f * 0.8, right, ph * 0.86, tone="red", off=0.0 )'''
b='''    if board_model:
        GRAFFITI_BOARDS.append( [ m, tuple( float( q ) for q in pc ), math.degrees( math.atan2( right[1], right[0] ) ) ] )
        obox( m, pc, right, ( pw, 1.5, ph ), { "default": None }, WOOD )
    else:
'''+ '\n'.join('    '+s for s in a.splitlines())
p=change(p,a,b)
r=change(r,'P.park_sign( m, SIGN[0], SIGN[1], scale=0.7, height=370 )','P.park_sign( m, SIGN[0], SIGN[1], scale=0.7, height=370, board_model=True )')
r=change(r,'def water_tank_objects():','''def graffiti_board_objects():
    return [ K.game_object( ids, "STILL HERE Board", f"graffiti_board/{k}", K.to_world( pos ), K.yaw_rotation( yaw ), components=[
        K.component( ids, "Sandbox.ModelRenderer", f"graffiti_board/{k}/renderer", Model="models/props/riverside/still_here_board_v1/board.vmdl", RenderType="On", Tint="1,1,1,1" ) ] )
        for k, ( owner, pos, yaw ) in enumerate( P.GRAFFITI_BOARDS ) ]


def water_tank_objects():''')
r=change(r,'        K.game_object( ids, "Water Tower Tanks", "water_tanks", children=water_tank_objects() ),','        K.game_object( ids, "Water Tower Tanks", "water_tanks", children=water_tank_objects() ),\n        K.game_object( ids, "Park Graffiti Boards", "graffiti_boards", children=graffiti_board_objects() ),')
compile(p,str(pp),'exec');compile(r,str(rp),'exec');pp.write_bytes(p);rp.write_bytes(r)

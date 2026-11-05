from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];pp=ROOT/'Tools/riverside_parts.py';rp=ROOT/'Tools/riverside_map.py';p=pp.read_bytes();r=rp.read_bytes()
def change(data,a,b):
    a=a.encode();b=b.encode()
    if a not in data:a=a.replace(b'\n',b'\r\n');b=b.replace(b'\n',b'\r\n')
    assert data.count(a)==1,a[:80];return data.replace(a,b)
assert b'TOWER_LADDERS = []' not in p
p=change(p,'WATER_TANKS = []','TOWER_LADDERS = []      # [owner, ladder foot, plan yaw]: approved fitted Lowtide design\nWATER_TANKS = []')
p=change(p,'    WATER_TANKS.clear()','    TOWER_LADDERS.clear()\n    WATER_TANKS.clear()')
p=change(p,' + WATER_TANKS',' + WATER_TANKS + TOWER_LADDERS')
p=change(p,'def guard_tower( m, base, facing=( 0, -1 ), deck=520.0, aim=None ):','def guard_tower( m, base, facing=( 0, -1 ), deck=520.0, aim=None, ladder_model=False ):')
a='''    for sx in ( -1, 1 ):
        rod( m, lb + side * ( sx * 9 ), lb + side * ( sx * 9 ) + UP * deck - f * -20 + f * 0, 1.2, "rs_wood", 5 )
    for zz in np.arange( 12, deck, 12 ):
        p = lb + UP * zz + f * ( 20 * zz / deck )
        rod( m, p - side * 9, p + side * 9, 0.9, "rs_wood", 5 )'''
b='''    if ladder_model:
        TOWER_LADDERS.append( [ m, tuple( float( q ) for q in lb ), math.degrees( math.atan2( -side[1], -side[0] ) ) ] )
    else:
'''+ '\n'.join('    '+s for s in a.splitlines())
p=change(p,a,b)
r=change(r,'P.guard_tower( m, TOWER[0], TOWER[1], aim=SEARCH_TARGET )','P.guard_tower( m, TOWER[0], TOWER[1], aim=SEARCH_TARGET, ladder_model=True )')
r=change(r,'def water_tank_objects():','''def tower_ladder_objects():
    return [ K.game_object( ids, "Guard Tower Ladder", f"tower_ladder/{k}", K.to_world( pos ), K.yaw_rotation( yaw ), components=[
        K.component( ids, "Sandbox.ModelRenderer", f"tower_ladder/{k}/renderer", Model="models/props/riverside/tower_ladder_v1/ladder.vmdl", RenderType="On", Tint="1,1,1,1" ) ] )
        for k, ( owner, pos, yaw ) in enumerate( P.TOWER_LADDERS ) ]


def water_tank_objects():''')
r=change(r,'        K.game_object( ids, "Water Tower Tanks", "water_tanks", children=water_tank_objects() ),','        K.game_object( ids, "Water Tower Tanks", "water_tanks", children=water_tank_objects() ),\n        K.game_object( ids, "Guard Tower Ladders", "tower_ladders", children=tower_ladder_objects() ),')
compile(p,str(pp),'exec');compile(r,str(rp),'exec');pp.write_bytes(p);rp.write_bytes(r);print('Narrow ladder hook installed')

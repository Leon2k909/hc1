"""Install only A's vessel hook, preserving the original tower structure, lights and collision."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];pp=ROOT/'Tools/riverside_parts.py';rp=ROOT/'Tools/riverside_map.py'
p=pp.read_bytes();r=rp.read_bytes();assert b'WATER_TANKS = []' not in p
def change(data,old,new):
    a=old.encode();b=new.encode()
    if a not in data and b'\r\n' in data:a=a.replace(b'\n',b'\r\n');b=b.replace(b'\n',b'\r\n')
    assert data.count(a)==1,old[:100]
    return data.replace(a,b)
p=change(p,'HITCHES = []','WATER_TANKS = []        # [ owner, vessel base, plan yaw ]: approved A water-tower vessel\nHITCHES = []')
p=change(p,'    HITCHES.clear()','    WATER_TANKS.clear()\n    HITCHES.clear()')
p=change(p,' + HITCHES', ' + HITCHES + WATER_TANKS')
p=change(p,'def water_tower( m, base, facing=( -1, -1 ) ):','def water_tower( m, base, facing=( -1, -1 ), tank_model=False ):')
a='''    cylinder( m, b, r_tank, bz + z0, bz + z1, "rs_tank", 28, bottom="rs_tank" )
    lathe( m, b, [ ( r_tank + 2, bz + z1 ), ( r_tank * 0.55, bz + z1 + 70 ), ( 18, bz + z1 + 110 ), ( 0, bz + z1 + 112 ) ], "rs_tank", 28 )'''
b='''    if tank_model:
        WATER_TANKS.append( [ m, tuple( float( q ) for q in b + UP * z0 ), 0.0 ] )
    else:
'''+ '\n'.join('    '+l for l in a.splitlines())
p=change(p,a,b)
p=change(p,'    paint( m, "sticks", c, right, ( z1 - z0 ) * 0.8, tone="white", off=0.0 )','    if not tank_model:\n        paint( m, "sticks", c, right, ( z1 - z0 ) * 0.8, tone="white", off=0.0 )')
r=change(r,'P.water_tower( m, WATER_TOWER[0], WATER_TOWER[1] )','P.water_tower( m, WATER_TOWER[0], WATER_TOWER[1], tank_model=True )')
r=change(r,'def hitch_objects():','''def water_tank_objects():
    """Approved A vessel; original support structure and lights remain in the backdrop."""
    out = []
    for k, ( owner, position, yaw ) in enumerate( P.WATER_TANKS ):
        key = f"water_tank/{k}"
        out.append( K.game_object( ids, "Riverside Water Tank", key, K.to_world( position ), K.yaw_rotation( yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model="models/props/riverside/water_tank_v1/tank.vmdl",
                         RenderType="On", Tint="1,1,1,1" ) ] ) )
    return out


def hitch_objects():''')
r=change(r,'        K.game_object( ids, "Trailer Hitches", "trailer_hitches", children=hitch_objects() ),','        K.game_object( ids, "Trailer Hitches", "trailer_hitches", children=hitch_objects() ),\n        K.game_object( ids, "Water Tower Tanks", "water_tanks", children=water_tank_objects() ),')
compile(p,str(pp),'exec');compile(r,str(rp),'exec');pp.write_bytes(p);rp.write_bytes(r)
print('A vessel generator hook installed; original frame, lighting and collision retained. No map regeneration.')

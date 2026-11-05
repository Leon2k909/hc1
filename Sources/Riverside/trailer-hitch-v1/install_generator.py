"""Narrow deterministic T2 hitch hook; preserve concurrent generator edits and line endings."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3];parts=ROOT/'Tools/riverside_parts.py';mp=ROOT/'Tools/riverside_map.py'
p=parts.read_bytes();r=mp.read_bytes();assert b'HITCHES = []' not in p
def change(data,old,new):
    a=old.encode();b=new.encode()
    if a not in data and b'\r\n' in data:a=a.replace(b'\n',b'\r\n');b=b.replace(b'\n',b'\r\n')
    assert data.count(a)==1,old[:100]
    return data.replace(a,b)
p=change(p,'AERIALS = []','HITCHES = []            # [ owner, body-end centre, plan yaw ]: approved T2 trailer hitch\nAERIALS = []')
p=change(p,'    AERIALS.clear()','    HITCHES.clear()\n    AERIALS.clear()')
p=change(p,' + AERIALS + CAMPERS + TRAILER_DOORS:', ' + AERIALS + CAMPERS + TRAILER_DOORS + HITCHES:')
p=change(p,'entry_door_model=False ):','entry_door_model=False, hitch_model=False ):')
a='''        for sy in ( -1, 1 ):
            m.beam( v( -hx, sy * 30, 18 ), v( -hx - 46, 0, 14 ), ( 3, 4 ), "rs_rust" )
        cylinder( m, ( -hx - 44, 0 ), 1.6, 0, 18, "rs_rust", 6 )
        obox( m, v( -hx - 44, 0, 1 ), ( 1, 0, 0 ), ( 8, 8, 2 ), "rs_concrete" )'''
b='''        if hitch_model:
            HITCHES.append( [ m, ( -float( hx ), 0.0, 0.0 ), 0.0 ] )
        else:
'''+ '\n'.join('    '+l for l in a.splitlines())
p=change(p,a,b)
r=change(r,'entry_door_model=( name == "T2" ) )','entry_door_model=( name == "T2" ), hitch_model=( name == "T2" ) )')
r=change(r,'def aerial_objects():','''def hitch_objects():
    """The approved T2 hitch; original body collision remains in the zone."""
    out = []
    for k, ( owner, position, yaw ) in enumerate( P.HITCHES ):
        key = f"hitch/{k}"
        out.append( K.game_object( ids, "T2 Trailer Hitch", key, K.to_world( position ), K.yaw_rotation( yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model="models/props/riverside/trailer_hitch_v1/hitch.vmdl",
                         RenderType="On", Tint="1,1,1,1" ) ] ) )
    return out


def aerial_objects():''')
r=change(r,'        K.game_object( ids, "Roof TV Aerials", "roof_aerials", children=aerial_objects() ),','        K.game_object( ids, "Roof TV Aerials", "roof_aerials", children=aerial_objects() ),\n        K.game_object( ids, "Trailer Hitches", "trailer_hitches", children=hitch_objects() ),')
compile(p,str(parts),'exec');compile(r,str(mp),'exec');parts.write_bytes(p);mp.write_bytes(r)
print('Narrow hitch generator hook installed; map not regenerated.')

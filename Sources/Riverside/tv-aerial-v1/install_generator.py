"""Apply the narrow aerial hook without rewriting mixed line endings elsewhere."""
from pathlib import Path
ROOT=Path(__file__).absolute().parents[3]
parts=ROOT/'Tools/riverside_parts.py';mp=ROOT/'Tools/riverside_map.py'
p=parts.read_bytes();r=mp.read_bytes()
assert b'AERIALS = []' not in p,'Hook already exists; inspect rather than apply twice.'
def change(data,old,new):
    a=old.encode();b=new.encode()
    if a not in data and b'\r\n' in data:a=a.replace(b'\n',b'\r\n');b=b.replace(b'\n',b'\r\n')
    assert data.count(a)==1,old[:100]
    return data.replace(a,b)
p=change(p,'FLUORESCENTS = []','AERIALS = []            # [ owner, mast base, plan yaw ]: approved T2 rooftop aerial\nFLUORESCENTS = []')
p=change(p,'    FLUORESCENTS.clear()','    AERIALS.clear()\n    FLUORESCENTS.clear()')
p=change(p,' + FLUORESCENTS + PIN_INSULATORS:', ' + FLUORESCENTS + PIN_INSULATORS + AERIALS:')
p=change(p,'roof_ac_model=False ):','roof_ac_model=False, aerial_model=False ):')
a='''        rod( m, base, base + UP * 70, 0.8, "rs_steel", 6 )
        for k in range( 5 ):
            zz = 50 + k * 4
            L2 = 30 - k * 4
            rod( m, base + UP * zz - v( 0, L2 / 2, 0 ), base + UP * zz + v( 0, L2 / 2, 0 ), 0.4, "rs_steel", 4 )'''
b='''        if aerial_model:
            AERIALS.append( [ m, tuple( float( q ) for q in base ), 0.0 ] )
        else:
'''+ '\n'.join('    '+l for l in a.splitlines())
p=change(p,a,b)
r=change(r,'part, info = P.trailer( L, W, tint, seed=seed, door_side=side, lit_share=0.6, boarded_share=0.15 )','part, info = P.trailer( L, W, tint, seed=seed, door_side=side, lit_share=0.6, boarded_share=0.15, aerial_model=( name == "T2" ) )')
r=change(r,'def fluorescent_objects():','''def aerial_objects():
    """The approved T2 rooftop aerial; other trailers retain their original arrays."""
    out = []
    for k, ( owner, position, yaw ) in enumerate( P.AERIALS ):
        key = f"aerial/{k}"
        out.append( K.game_object( ids, "T2 Rooftop TV Aerial", key, K.to_world( position ), K.yaw_rotation( yaw ), components=[
            K.component( ids, "Sandbox.ModelRenderer", f"{key}/renderer", Model="models/props/riverside/tv_aerial_v1/aerial.vmdl",
                         RenderType="On", Tint="1,1,1,1" ) ] ) )
    return out


def fluorescent_objects():''')
r=change(r,'        K.game_object( ids, "Store Ceiling Lights", "fluorescents", children=fluorescent_objects() ),','        K.game_object( ids, "Store Ceiling Lights", "fluorescents", children=fluorescent_objects() ),\n        K.game_object( ids, "Roof TV Aerials", "roof_aerials", children=aerial_objects() ),')
compile(p,str(parts),'exec');compile(r,str(mp),'exec')
parts.write_bytes(p);mp.write_bytes(r);print('Narrow generator hook installed; map not regenerated.')

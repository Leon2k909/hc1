from pathlib import Path
import inspect
import sys

root=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(root/'Tools'))
import ares_map as A
p=root/'Tools/ares_map.py';raw=p.read_bytes()
newline=b'\r\n' if b'\r\n' in raw else b'\n'
old=inspect.getsource(A.case)
d=root/'Sources/Ares/crate-v2';d.mkdir(exist_ok=True)
assert not (d/'original-case.py.txt').exists()
(d/'original-case.py.txt').write_text(old)
backup=root/'output/ares/crate-v2/ares_map-before.py'
assert not backup.exists();backup.write_bytes(raw)
old_b=old.replace('\n',newline.decode()).encode();assert raw.count(old_b)==1
replacement='''def case( m, e, n, z, heading, size=AM.CASE, front="front_text", side="side_logo", top="top_ribs", collide=True ):
    """An authored Ares case instance over the existing collision footprint."""
    from ares_cargo_case import append_instance
    return append_instance( m, e, n, z, heading, size, front, side, top, collide )
'''
raw=raw.replace(old_b,replacement.replace('\n',newline.decode()).encode(),1)
old_sig=b'def write_scene( written, light_list, probe_list ):'
assert raw.count(old_sig)==1
raw=raw.replace(old_sig,b'def write_scene( written, light_list, probe_list, case_props=None ):',1)
marker=b'    light_objects = [';assert raw.count(marker)==1
addition=('    from ares_cargo_case import scene_group\n'
          '    world["Children"].append( scene_group( ids, case_props ) )\n')
raw=raw.replace(marker,addition.replace('\n',newline.decode()).encode()+marker,1)
old_call=b'        write_scene( written, light_list, probe_list )'
assert raw.count(old_call)==1
raw=raw.replace(old_call,b'        write_scene( written, light_list, probe_list, models["ares_dressing"].props )',1)
temporary=p.with_name(p.name+'.crate-incoming');temporary.write_bytes(raw);temporary.replace(p)
print('Updated regeneration hooks; complete original source preserved.')

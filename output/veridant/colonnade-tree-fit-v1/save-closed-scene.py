"""Persist the verified light relocation only while this project's editor is closed."""
from pathlib import Path
import json,re
p=Path('C:/sbox-projects/hc1/forked-shooter-main/Assets/scenes/maps/Veridant/veridant.scene')
text=p.read_text();data=json.loads(text);queue=[data];matches=[]
while queue:
    item=queue.pop()
    if isinstance(item,dict):
        if item.get('__guid')=='ef336f5f-eb44-538d-aa5e-2fbddec68eb9':matches.append(item)
        queue.extend(item.values())
    elif isinstance(item,list):queue.extend(item)
assert len(matches)==1
assert matches[0]['Position'] in ('20,222,46.0999985','-1,244,46.0999985')
pattern=r'("__guid"\s*:\s*"ef336f5f-eb44-538d-aa5e-2fbddec68eb9".*?"Position"\s*:\s*")[^"]+(" )'
# Match only the position field within the exact object's header.
pattern=r'("__guid"\s*:\s*"ef336f5f-eb44-538d-aa5e-2fbddec68eb9"(?:(?!"__guid").)*?"Position"\s*:\s*")[^"]+(")'
updated,count=re.subn(pattern,lambda m:m[1]+'-1,244,46.0999985'+m[2],text,flags=re.S)
assert count==1;json.loads(updated)
p.write_text(updated)
print('Saved only Colonnade olive uplight position')

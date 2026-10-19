"""Inspect concurrent Lowtide edits without rewriting scene data."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
before=json.loads((OUT/"candidates/lowtide.json").read_text())
path=ROOT/"Assets/scenes/maps/lowtide/lowtide.scene"
current=json.loads(path.read_text(encoding="utf-8-sig"))
def collect(value, parent="", result=None):
    result={} if result is None else result
    if isinstance(value,dict):
        name=value.get("Name",value.get("__type",parent))
        if "__guid" in value:
            result[value["__guid"]]={"name":name,"type":value.get("__type"),"parent":parent,"value":value}
        for child in value.values():
            collect(child,str(name),result)
    elif isinstance(value,list):
        for child in value: collect(child,parent,result)
    return result
old,new=collect(before),collect(current)
brief=lambda entry:{key:value for key,value in entry.items() if key != "value"}
print(json.dumps({"file":str(path),"mtime":path.stat().st_mtime,"lines":len(path.read_text().splitlines()),"old_roots":len(before["GameObjects"]),"new_roots":len(current["GameObjects"]),"added_count":len(new.keys()-old.keys()),"added":[brief(new[k]) for k in sorted(new.keys()-old.keys())],"removed":[brief(old[k]) for k in sorted(old.keys()-new.keys())]},indent=2))

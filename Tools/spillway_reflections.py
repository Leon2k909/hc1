"""Project native camera faces into static Spillway reflection panoramas.

The engine sky asset compiler performs the cube conversion. This follows the
verified Sewage path without invoking the workstation's unstable GGX bake.
"""
from pathlib import Path
import ast
import sys
import sewage_reflections as shared

ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/"Tools/sewage_reflections.py").read_text()
function=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=="panorama")
body=ast.get_source_segment(source,function).replace("sewage","spillway")
revision="_v3" if "--v3" in sys.argv else "_v2" if "--v2" in sys.argv else ""
if revision:
    body=body.replace("reflection_{index}.exr","reflection_{index}"+revision+".exr").replace("reflection_{index}.vmat","reflection_{index}"+revision+".vmat")
    body=body.replace("+str(index)+'.exr", "+str(index)+'"+revision+".exr")
namespace=dict(vars(shared));namespace["ROOT"]=ROOT
exec(compile(body,"spillway_reflection_panorama","exec"),namespace)
for index in range(5):namespace["panorama"](index)

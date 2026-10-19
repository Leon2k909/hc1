"""Convert native camera faces into Collider's static reflection sources.

Uses the verified Sewage panorama projection and EXR writer, parameterized here
without modifying its assets. Native sky material compilation produces the cube.
"""
from pathlib import Path
import argparse
import ast
import numpy as np
from PIL import Image
import sewage_reflections as shared

ROOT=Path(__file__).resolve().parents[1]


def panorama(label):
    if label not in ("Hall","Beam","West","East"):
        raise ValueError(label)
    # The existing converter has a fixed map path. Reuse its verified function
    # body with this map's paths while preserving the vector projection exactly.
    source=(ROOT/"Tools/sewage_reflections.py").read_text()
    tree=ast.parse(source)
    function=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=="panorama")
    body=ast.get_source_segment(source,function)
    body=body.replace("output/sewage/reflections","output/collider/reflections")
    body=body.replace("output/sewage/stage/materials/sewage/reflections","output/collider/stage/materials/collider/reflections")
    body=body.replace("materials/sewage/reflections/","materials/collider/reflections/")
    namespace=dict(vars(shared)); namespace["ROOT"]=ROOT
    exec(compile(body,"collider_reflection_panorama","exec"),namespace)
    namespace["panorama"](label)


if __name__=="__main__":
    parser=argparse.ArgumentParser();parser.add_argument("label",choices=("Hall","Beam","West","East","all"))
    label=parser.parse_args().label
    for item in ("Hall","Beam","West","East") if label=="all" else (label,): panorama(item)

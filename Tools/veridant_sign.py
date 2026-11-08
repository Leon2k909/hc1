"""Retain the reviewed reception sign geometry when regenerating Veridant."""
from pathlib import Path
import importlib.util

def build_into(model):
    path=Path(__file__).resolve().parent.parent/'Sources/Veridant/sign-v2/build.py'
    spec=importlib.util.spec_from_file_location('veridant_reception_sign_v2',path)
    source=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(source)
    model.extend(source.build_sign())
    model.collision_box((110,96,0),(140,196,166),'default')
    model.collision_box((109,95,166),(141,197,170),'default')

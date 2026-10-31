# Turn the old grenade's compiled maps back into plain maps Blender can use, only to render the "before". See adapt.py.
#   python old_maps.py <work dir>
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import adapt  # noqa: E402

adapt.run("old_maps.py", [("v_smoke_grenade_color.png", "v_incendiary_grenade_color.png"), ("v_smoke_grenade_normal.png", "v_incendiary_grenade_normal.png")], os.path.abspath(__file__))

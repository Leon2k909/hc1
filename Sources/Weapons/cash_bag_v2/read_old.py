# Pull the old dev duffel bag out of its compiled file, only to render a fair "before". Nothing here is shipped.
# Runs the HE grenade's reader with its paths changed, rather than keep a second copy of it.
#   python read_old.py <project root> <out dir>
import sys

sys.dont_write_bytecode = True
ROOT, OUT = sys.argv[1].replace("\\", "/"), sys.argv[2].replace("\\", "/")
source = open(f"{ROOT}/Sources/Weapons/he_grenade_v2/read_old.py", encoding="utf-8").read()
source = source.replace('CLOUD = "C:/sbox-projects/hc1/forked-shooter-main/.sbox/cloud/models/weapons/sbox_grenade_explosive"', f'CLOUD = "{ROOT}/.sbox/cloud/models/dev/duffelbag"')
source = source.replace('OUT = "C:/sbox-projects/hc1/forked-shooter-main/output/asset-improvement-20261030/he-grenade/old"', f'OUT = "{OUT}"')
source = source.replace('"w_he_grenade.vmdl_c"', '"dufflebag_money.vmdl_c"')
exec(compile(source, "read_old", "exec"))

"""Create the lawn variant of the established isolated material comparison tool."""
from pathlib import Path
root=Path.cwd()
code=(root/'Tools/veridant_megascans_gravel_trial_20261105.py').read_text()
for before,after in [
    ('megascans-gravel-trial-20261105','megascans-lawn-trial-20261105'),
    ('gravel_ground_vi0maebg_2k.zip','lawn_grass_tkynejer_4k.zip'),
    ('vi0maebg','tkynejer'),
    ('c19d425f-4957-4238-b1d7-34c984e9867f','f50d1f4a-d91a-41c2-86ad-10c4ffe7f658'),
    ('gravel.vmat','lawn.vmat'),('vr_gravel.vmat','vr_lawn.vmat'),
    ('Gravel Ground','Lawn Grass'),('gravel slots','lawn slots'),
    ('[1.2192 1.2192]','[1.6256 1.6256]'),
    ('texture_size\':2048','texture_size\':4096'),
    ("'position':'-850,150,64','angles':'25,-90,0'","'position':'287,506,182','angles':'25.09,-51.65,0'"),
    ("'fov':65","'fov':53"),
    ("if phase=='after-streamed':","if phase in ('before','after','after-streamed'):"),
    ('MarkUsed(2048)','MarkUsed(4096)'),
    ('"g_tRoughness"','"g_tRma"'),
    ('2x2 metre original 2K scan','2x2 metre original 4K scan'),
]:code=code.replace(before,after)
# Request full-size textures for both captures, while pinning exposure identically.
code=code.replace('var trialMaterial=Material.Load("RELPATH/lawn.vmat");','var trialMaterial=Material.Load(config["name"].GetValue<string>()=="before" ? "materials/veridant/vr_lawn.vmat" : "RELPATH/lawn.vmat");')
code=code.replace('"texture-audit.json"','config["name"].GetValue<string>()+"-texture-audit.json"')
(root/'Tools/veridant_megascans_lawn_trial_20261105.py').write_text(code)
print('Prepared lawn comparison tool')

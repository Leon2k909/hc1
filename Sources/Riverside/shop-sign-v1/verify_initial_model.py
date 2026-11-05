from pathlib import Path
import json,hashlib,subprocess,sys
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('C:/sbox-projects/hc1/forked-shooter-main');REVIEW=Path(__file__).resolve().parents[3];HERE=Path(__file__).parent;OUT=REVIEW/'output/riverside/shop-sign-v1'
subprocess.run(['rtk','proxy',sys.executable,str(HERE/'check_geometry.py')],cwd=REVIEW,check=True)
m=json.loads((OUT/'manifest.json').read_text());r=json.loads((OUT/'materials-verified.json').read_text());capture=json.loads((OUT/'isolated-native-review.json').read_text())
assert r['AllMaterialsLoaded'] and r['Face']['Emission']==1 and capture['UserStatePreserved']
assert r['Candidate']['LodCount']==3 and [mesh['Triangles'] for mesh in r['Candidate']['Meshes']]==m['triangles']
assert [mesh['LodMask'] for mesh in r['Candidate']['Meshes']]==[1,2,4]
assert r['Original']['TotalTriangles']-r['Without']['TotalTriangles']==136
a={mesh['Name']:mesh for mesh in r['Original']['Meshes']};b={mesh['Name']:mesh for mesh in r['Without']['Meshes']}
for name,mesh in a.items():
    assert mesh['LodMask']==b[name]['LodMask']
    assert mesh['Triangles']-b[name]['Triangles']==(136 if name=='riverside_store' else 0)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(ROOT/m['source_model'])==m['source_sha256'] and sha(ROOT/m['source_vmdl'])==m['source_vmdl_sha256']
assert all(sha(ROOT/p)==h for p,h in m['files'].items()) and all(sha(ROOT/p)==h for p,h in m['external_files'].items())
marker='_class = "PhysicsShapeList"';a=(ROOT/m['source_vmdl']).read_text();b=(REVIEW/'Assets/models/maps/riverside/shop-sign-v1/store_without_shop_sign.vmdl').read_text();assert a[a.index(marker):]==b[b.index(marker):]
for output,source in [('face_color.png','rs_lit_color.png'),('face_illum.png','rs_lit_illum.png')]:
    im=Image.open(ROOT/'Assets/materials/riverside'/source);scale=im.width/4096
    expected=im.crop(tuple(round(v*scale) for v in (2048,640,4096,1152))).resize((2048,512),Image.Resampling.LANCZOS)
    actual=Image.open(REVIEW/'Assets/materials/riverside/shop-sign-v1'/output)
    assert expected.mode==actual.mode and expected.tobytes()==actual.tobytes()
def compose(prefix,destination,caption,height=800):
    sheet=Image.new('RGB',(1600,height+92),'#111416');draw=ImageDraw.Draw(sheet)
    font=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',27);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',19)
    for offset,variant,title in [(0,'before','CURRENT'),(800,'after','UPGRADE PREVIEW')]:
        draw.text((offset+28,15),title,font=font,fill='#eeeeea');draw.text((offset+28,51),caption,font=small,fill='#aeb8ba')
        im=Image.open(OUT/f'{prefix}-{variant}.png').convert('RGB');sheet.paste(im.resize((800,height),Image.Resampling.LANCZOS),(offset,92))
    sheet.save(OUT/destination)
compose('isolated','engine-comparison.png','Native asset preview | same lighting')
game=json.loads((OUT/'runtime-review.json').read_text());restored=json.loads((OUT/'state-restored.json').read_text())
assert game['ActualPlayMode'] and game['PlayerCount']>0 and not game['ErrorModels'] and game['NoExtraLights'] and restored['restored']
assert [mesh['Triangles'] for mesh in game['Candidate']['Meshes']]==m['triangles']
assert game['PublicStore']['TotalTriangles']-game['StoreWithout']['TotalTriangles']==136
compose('in-game','in-game-comparison.png','Actual play | existing map lights',600)
report=dict(preview_only=True,engine_render_verified=True,in_game_checked=True,all_materials_loaded=True,lettering_and_emission_mask_preserved=True,no_added_map_lights=True,removed_old_triangles=136,other_upgrades_preserved=True,physics_unchanged=True,source_hashes_unchanged=True,user_state_preserved=True,editor_state_restored=True,geometry=json.loads((OUT/'geometry-verified.json').read_text()))
(OUT/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report,indent=2))

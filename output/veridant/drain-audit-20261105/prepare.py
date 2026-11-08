from pathlib import Path
import json
root=Path('C:/sbox-projects/hc1/forked-shooter-main')
out=root/'output/veridant/drain-audit-20261105'
ex=Path('C:/Users/leon2/AppData/Local/Temp/sbox-cli/5d0428de1508495cb0c30e55c93bd71c')
text=(ex/'threshold-before.cs').read_text()
text=text.replace('new Vector3(-405,-320,60)','new Vector3(-190,-420,60)')
text=text.replace('new Vector3(1,0,-0.20f)','new Vector3(150,-80,-60).Normal')
text=text.replace('Door threshold QA camera','Drain audit camera')
text=text.replace('new Vector2(1000,900)','new Vector2(1200,800)').replace('new Bitmap(1000,900)','new Bitmap(1200,800)')
start=text.index('var path = @"')
end=text.index(';',start)
text=text[:start]+'var path = @"'+str(out/'courtyard-drain.png')+'"'+text[end:]
path=ex/'drain-audit.cs'
path.write_text(text)
(out/'capture.json').write_text(json.dumps({'path':str(path)}))

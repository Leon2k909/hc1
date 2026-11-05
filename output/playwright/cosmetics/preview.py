"""Browser layout review of production cosmetics SCSS; not an s&box runtime test."""
from pathlib import Path
import json
import re

root = Path.cwd()
out = root / 'output/playwright/cosmetics'
scss = (root / 'Code/UI/MenuSystem/Shared/CosmeticCollectionPanel.razor.scss').read_text()
theme = (root / 'Code/UI/Styles/MenuPage.scss').read_text()
(out / 'preview.scss').write_text(theme + '\n' + re.sub(r'@import[^;]+;', '', scss))
text = (root / 'Code/Cosmetics/CosmeticCatalog.cs').read_text()
items = re.findall(r'new CosmeticArt\( "([^"]+)", "([^"]+)", "([^"]*)" \)', text)
art = [dict(id=i, name=n, image='/Assets/' + p if p else '') for i,n,p in items]
template = '''<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="preview.css"><style>
*{box-sizing:border-box}body{margin:0;background:#08090b;color:white;font:16px Arial,sans-serif;height:100vh;display:flex;flex-direction:column}div,CosmeticCollectionPanel{display:flex}button,input{font:inherit;color:inherit}button{display:flex}label{display:block}header{padding:24px 40px;border-bottom:1px solid #303136;display:flex;gap:30px;align-items:center}header strong{letter-spacing:4px}header button{background:transparent;border:0;padding:8px;color:#ff7a1a;cursor:pointer}CosmeticCollectionPanel{overflow-y:auto}input{background:#08090b}.cosmetic-options{display:flex}.cosmetic-grid img{flex-shrink:0}.cosmetic-custom-actions button{cursor:pointer}i{font-style:normal}.cosmetic-preview img{flex-shrink:0}
@media(max-width:900px){header{padding:16px 24px}}
</style></head><body><header><strong>RAZED / PROFILE</strong><button onclick="render(false)">SPRAYS</button><button onclick="render(true)">LOADING SCREENS</button></header><CosmeticCollectionPanel></CosmeticCollectionPanel><script>
const art=__ART__; let loading=false; const picks={spray:'precision',loading:'orion'};
function render(isLoading){loading=isLoading;document.body.className='main-menu-root'+(innerWidth<1100?' narrow':''); const list=loading?art.slice(6):art.slice(0,6),id=picks[loading?'loading':'spray']; const sel=list.find(x=>x.id===id)||list[0];
document.querySelector('CosmeticCollectionPanel').innerHTML=`<div class="cosmetic-intro"><label class="cosmetic-heading">${loading?'LOADING SCREENS':'SPRAYS'}</label><label class="cosmetic-description">${loading?'Choose artwork for your loading screen, or use your own image.':'Choose a spray to leave on walls and floors during a match.'}</label>${loading?'':'<label class="cosmetic-note">Bind Spray in Settings → Controls. One active spray, with a 10-second cooldown.</label>'}</div><div class="cosmetic-body"><div class="cosmetic-preview-panel"><div class="cosmetic-preview ${loading?'landscape':'spray'}">${sel.image?`<img src="${sel.image}">`:'<i>◇</i>'}</div><label class="cosmetic-selected-name">${sel.name}</label><label class="cosmetic-equipped">EQUIPPED</label></div><div class="cosmetic-options"><div class="cosmetic-grid">${list.map(x=>`<button class="cosmetic-option ${loading?'landscape':'spray'} ${x.id===id?'selected':''}" onclick="pick('${x.id}')">${x.image?`<img src="${x.image}">`:'<i>◇</i>'}<label>${x.name}</label>${x.id===id?'<i class="cosmetic-check">✓</i>':''}</button>`).join('')}</div>${loading?'<div class="cosmetic-custom"><label class="cosmetic-custom-title">YOUR IMAGE</label><label class="cosmetic-description">Paste a direct HTTPS link to a PNG, JPG or WebP image. This image is only shown to you.</label><input class="cosmetic-url" placeholder="https://example.com/image.png"><div class="cosmetic-custom-actions"><button class="cosmetic-use">USE IMAGE</button><button onclick="pick(\'default\')">RESTORE DEFAULT</button></div><label class="cosmetic-note">Use a direct image link, not a page link. If the host is unavailable, try another image or restore the default.</label></div>':''}</div></div>`;
}
function pick(id){picks[loading?'loading':'spray']=id;render(loading)}window.addEventListener('resize',()=>render(loading));render(false);
</script></body></html>'''
template = template.replace("pick('default')", "pick(&quot;default&quot;)")
(out / 'preview.html').write_text(template.replace('__ART__',json.dumps(art)),encoding='utf-8')
print(out / 'preview.html')

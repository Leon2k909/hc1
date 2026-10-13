const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const sass = require(process.argv[2]);
const project = path.resolve(__dirname, '../../..');
const url = file => '/' + path.relative(project, file).split(path.sep).map(encodeURIComponent).join('/');
const importer = { findFileUrl(value) { return value.startsWith('/UI/') ? pathToFileURL(path.join(project, 'Code', value.slice(1))) : null; } };
const result = sass.compile(path.join(project, 'Code/UI/MenuSystem/Shared/Career/CareerLanding.razor.scss'), { importers: [importer], logger: { warn() {}, debug() {} } });
fs.writeFileSync(path.join(__dirname, 'CareerLanding.css'), result.css);
const files = fs.readdirSync(path.join(project, 'Assets'), { recursive: true }).filter(file => file.endsWith('.equip'));
const weapons = files.map(file => JSON.parse(fs.readFileSync(path.join(project, 'Assets', file), 'utf8').replace(/^\uFEFF/, '')))
  .filter(equip => equip.Slot === 'Primary' || equip.Slot === 'Secondary')
  .map(equip => ({ ...equip, Category: equip.Category || 'AssaultRifle' }))
  .sort((a,b) => a.Name.localeCompare(b.Name));
const categories = ['None','AssaultRifle','SMG','LMG','Sniper','Shotgun','Marksman','Pistol','Launcher','Melee'].filter(category => weapons.some(w => w.Category === category));
const names = { None: 'OTHER', AssaultRifle: 'ASSAULT', Sniper: 'SNIPER', Marksman: 'MARKSMAN' };
const escape = text => String(text).replaceAll('&','&amp;').replaceAll('"','&quot;').replaceAll('<','&lt;');
const stats = { 'AK-105': [19,363,122], 'AK-12': [2,6,1], 'AK-15': [1,2,0], 'AK-74M': [7,0,0] };
function weapon(w) {
  const [level,kills,heads] = stats[w.Name] || [1,0,0];
  return `<careerweapon class="career-weapon"><div class="weapon-heading"><label class="weapon-name">${escape(w.Name)}</label><div class="weapon-icon" style="background-image:url('${url(path.join(project, 'Assets', w.Icon || ''))}')"></div></div><div class="weapon-level-row"><label class="weapon-level-badge">LEVEL ${level}</label><div class="weapon-xp-bar-wrap"><div class="weapon-xp-bar-fill" style="width:45%"></div></div></div><div class="weapon-stat-row"><label>Kills</label><label class="weapon-stat-value">${kills}</label></div><div class="weapon-stat-row"><label>Headshot Kills</label><label class="weapon-stat-value">${heads}</label></div></careerweapon>`;
}
function document(state = {}) {
 const visible = state.empty ? [] : state.search ? weapons.filter(w => w.Name.replace(/[^a-z0-9]/gi,'').toLowerCase().includes(state.search.toLowerCase())) : weapons;
 const categoriesHtml = `<button class="weapon-category ${!state.category ? 'active' : ''}"><label>ALL WEAPONS</label><label class="category-count">${weapons.length}</label></button>` + categories.map(c => `<button class="weapon-category ${state.category === c ? 'active' : ''}"><label>${names[c] || c.toUpperCase()}</label><label class="category-count">${weapons.filter(w => w.Category === c).length}</label></button>`).join('');
 return `<!doctype html><html><head><meta charset="utf-8"><title>Career record source layout preview</title><link rel="stylesheet" href="CareerLanding.css"><style>
 @font-face { font-family:'Chakra Petch'; src:url('${url(path.join(project,'Assets/fonts/ChakraPetch-Regular.ttf'))}'); font-weight:400; }
 @font-face { font-family:'Chakra Petch'; src:url('${url(path.join(project,'Assets/fonts/ChakraPetch-Medium.ttf'))}'); font-weight:500; }
 @font-face { font-family:'Chakra Petch'; src:url('${url(path.join(project,'Assets/fonts/ChakraPetch-SemiBold.ttf'))}'); font-weight:600; }
 @font-face { font-family:'Chakra Petch'; src:url('${url(path.join(project,'Assets/fonts/ChakraPetch-Bold.ttf'))}'); font-weight:700; }
 * { box-sizing:border-box; } html,body,.main-menu-root { margin:0; width:100%; height:100%; } body { background:#08090b; }
 div,careerlanding,careerweapon,careerstat,button { display:flex; } label { display:block; } button { font:inherit; text-align:left; }
 .weapon-search-entry { display:flex; border:0; background:none; outline:none; width:100%; }
 .weapon-search i,.weapon-record-empty i,.weapon-clear i { font-family:Arial; font-style:normal; }
 .preview-note { position:fixed; bottom:6px; right:16px; color:#aaa; font:11px Arial; }
 </style></head><body><div class="main-menu-root"><careerlanding class="hc1 progression-page"><div class="progression-body">
 <div class="player-stats"><label class="section-title">FIELD STATISTICS</label>${['Kills','Headshot Kills','Deaths'].map(n=>`<careerstat><label class="name">${n}</label><label class="value">0</label></careerstat>`).join('')}</div>
 <div class="progression-content"><div class="weapon-record"><div class="weapon-record-heading"><label class="section-title">WEAPON RECORD</label><label class="weapon-record-count">${visible.length} / ${weapons.length} WEAPONS</label></div><div class="weapon-categories">${categoriesHtml}</div>
 <div class="weapon-record-tools"><div class="weapon-search"><i>⌕</i><input class="weapon-search-entry" placeholder="Search weapons" value="${escape(state.search || '')}"></div><div class="weapon-sort"><label class="weapon-sort-label">SORT BY</label>${['Name','Kills','Level'].map(n=>`<button class="weapon-sort-option ${n==='Name' ? 'active' : ''}"><label>${n}</label></button>`).join('')}</div>${state.search ? '<button class="weapon-clear"><i>×</i><label>CLEAR FILTERS</label></button>' : ''}</div>
 ${visible.length ? `<div class="weapon-stats-grid">${visible.map(weapon).join('')}</div>` : '<div class="weapon-record-empty"><i>⌕</i><label class="weapon-empty-title">No weapons match your filters.</label><label>Try another name or category.</label></div>'}
 </div></div></div></careerlanding></div><label class="preview-note">SOURCE LAYOUT PREVIEW · SAMPLE STATISTICS</label><script>
 function resize(){ const root=document.querySelector('.main-menu-root'); root.classList.toggle('compact',innerWidth<1600); root.classList.toggle('narrow',innerWidth<1200); root.classList.toggle('portrait',innerWidth<800); } resize();addEventListener('resize',resize);
 </script></body></html>`;
}
for(const [file,state] of [['index',{}],['search',{search:'AK74'}],['empty',{search:'zzzzz',empty:true}]]) fs.writeFileSync(path.join(__dirname,file+'.html'), document(state));
console.log(JSON.stringify({weapons:weapons.length,categories:categories.map(c=>({category:c,count:weapons.filter(w=>w.Category===c).length})),files:['index.html','search.html','empty.html']}));

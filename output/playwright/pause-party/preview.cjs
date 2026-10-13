const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const sass = require(process.argv[2]);
const { chromium } = require(process.argv[3]);
const project = path.resolve(__dirname, '../../..');
const url = file => pathToFileURL(file).href;

const importer = {
  findFileUrl(value) {
    return value.startsWith('/UI/') ? pathToFileURL(path.join(project, 'Code', value.slice(1))) : null;
  }
};
for (const [input, output] of [
  ['Code/Party/PartyPanel.razor.scss', 'PartyPanel.css'],
  ['Code/UI/MenuSystem/PauseMenu/PausePage.razor.scss', 'PausePage.css']
]) {
  const result = sass.compile(path.join(project, input), { importers: [importer], logger: { warn() {}, debug() {} } });
  fs.writeFileSync(path.join(__dirname, output), result.css);
}

const member = (name, leader = false) => `<div class="party-roster-row"><div class="party-roster-avatar"></div><div class="party-roster-identity"><label class="party-roster-name">${name}</label>${leader ? '<label class="party-roster-role">Party Leader</label>' : ''}</div></div>`;
const action = (label, primary = false) => `<button class="party-social-button${primary ? ' primary' : ''}"><i>person_add</i><label>${label}</label></button>`;
const roster = (count, privacy = false) => `<partypanel class="expanded"><div class="party-roster-header"><label class="party-roster-title">YOUR SQUAD</label><label class="party-roster-count">${count} / 8</label></div>
  <div class="party-roster">${member('Leon', true)}${Array.from({ length: count - 1 }, (_, i) => member(i === 0 ? 'A very long squadmate name that should fit without hiding controls' : `Squadmate ${i + 1}`)).join('')}</div>
  ${count > 1 ? action('Leave Party') : ''}
  <div class="party-social-actions">${action('Invite Friends', true)}${action('Friends')}${action('Invite Players')}${action('Squad Privacy')}</div>
  ${privacy ? '<div class="party-privacy-options"><button class="party-privacy-option selected"><label>OPEN SQUAD</label></button><button class="party-privacy-option"><label>INVITE ONLY</label></button><button class="party-privacy-option"><label>PRIVATE SQUAD</label></button></div>' : ''}
  </partypanel>`;
const options = ['Resume', 'Change Class', 'Gunsmith', 'Settings', 'Report a Bug', 'Leave Match', 'Quit to s&amp;box'];
const html = `<!doctype html><html><head><meta charset="utf-8"><title>Pause party source preview</title>
  <link rel="stylesheet" href="PartyPanel.css"><link rel="stylesheet" href="PausePage.css">
  <style>
    @font-face { font-family: Dinish; src: url("${url(path.join(project, 'Assets/fonts/Dinish-Regular.ttf'))}"); font-weight: 400; }
    @font-face { font-family: Dinish; src: url("${url(path.join(project, 'Assets/fonts/Dinish-Bold.ttf'))}"); font-weight: 700; }
    @font-face { font-family: 'Chakra Petch'; src: url("${url(path.join(project, 'Assets/fonts/ChakraPetch-Regular.ttf'))}"); font-weight: 400; }
    @font-face { font-family: 'Chakra Petch'; src: url("${url(path.join(project, 'Assets/fonts/ChakraPetch-Bold.ttf'))}"); font-weight: 700; }
    * { box-sizing: border-box; }
    html,body { margin: 0; width: 100%; height: 100%; }
    body { background: url("${url('C:/Users/leon2/AppData/Local/Temp/codex-clipboard-c429d58b-cc8f-4c25-a1e5-61e5f8ac8590.png')}") center/cover; }
    div, pausepage, partypanel, button { display: flex; }
    label { display: block; }
    button { flex-direction: row; text-align: left; }
    pausepage { position: relative; }
    .preview-note { position: absolute; bottom: 10px; right: 16px; font: 12px Dinish; opacity: .5; color: white; }
    i { display: none; }
  </style></head><body><pausepage class="pause-page">
    <div class="pause-side"><div class="pause-head"><div class="pause-accent"></div><label class="pause-title">PAUSED</label></div>
    <div class="pause-items">${options.map((label, i) => `${i === 5 ? '<div class="pause-sep"></div>' : ''}<div class="pause-item${i === 0 ? ' primary' : ''}"><label>${label}</label></div>`).join('')}</div></div>
    <div class="pause-social">${roster(3)}</div><label class="preview-note">SOURCE LAYOUT PREVIEW · NOT AN IN-GAME CAPTURE</label>
    </pausepage></body></html>`;
fs.writeFileSync(path.join(__dirname, 'index.html'), html);

(async () => {
  const browser = await chromium.launch({ headless: true, channel: 'chrome' });
  try {
    const page = await browser.newPage({ viewport: { width: 1280, height: 720 } });
    await page.goto(url(path.join(__dirname, 'index.html')));
    await page.evaluate(() => document.fonts.ready);
    const check = async name => {
      const result = await page.evaluate(() => {
        const panel = document.querySelector('partypanel');
        const bounds = panel.getBoundingClientRect();
        const menu = document.querySelector('.pause-items').getBoundingClientRect();
        const issues = [];
        if (bounds.right > innerWidth || bounds.bottom > innerHeight || bounds.top < 0) issues.push('party panel outside viewport');
        if (bounds.left < menu.right) issues.push('party panel overlaps pause actions');
        for (const row of document.querySelectorAll('.party-social-button,.party-roster-row,.party-roster-header')) {
          if (row.scrollWidth > row.clientWidth + 1) issues.push(`${row.className} overflows horizontally`);
        }
        return { viewport: [innerWidth, innerHeight], panel: [bounds.x, bounds.y, bounds.width, bounds.height], issues };
      });
      console.log(JSON.stringify({ name, ...result }));
      await page.screenshot({ path: path.join(__dirname, `${name}.png`) });
      if (result.issues.length) throw new Error(result.issues.join('\n'));
    };
    await check('party-three-1280');
    await page.evaluate(markup => document.querySelector('.pause-social').innerHTML = markup, roster(8));
    await check('party-eight-1280');
    await page.evaluate(markup => document.querySelector('.pause-social').innerHTML = markup, roster(8, true));
    await check('party-eight-privacy-1280');
    await page.setViewportSize({ width: 1024, height: 720 });
    await check('party-eight-privacy-1024');
    await page.evaluate(markup => document.querySelector('.pause-social').innerHTML = markup, roster(1));
    await check('solo-1024');
    await page.setViewportSize({ width: 1920, height: 1080 });
    await page.evaluate(markup => document.querySelector('.pause-social').innerHTML = markup, roster(3));
    await check('party-three-1920');
    console.log('Source layout checks passed; no Steam invites were sent.');
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

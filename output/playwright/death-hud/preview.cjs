const fs = require('node:fs');
const path = require('node:path');
const { pathToFileURL } = require('node:url');
const { chromium } = require(process.argv[2]);

const directory = __dirname;
const project = path.resolve(directory, '../../..');
const fileUrl = file => pathToFileURL(file).href;
const escape = value => value.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('"', '&quot;');
const mouseGlyph = `data:image/svg+xml,${encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24"><rect x="6" y="2" width="12" height="20" rx="6" fill="#f4f4f0"/><path d="M12 3v7M7 10h10" stroke="#141414" stroke-width="1.5"/></svg>')}`;
const hint = action => `<inputhint data-action="${action}"><img src="${mouseGlyph}"></inputhint>`;
const death = (name, title, heading, entries, prompt, inflicted = '') => `
  <deathcam class="hud with-deadzone">
    <div class="killer-summary"><div class="killer-identity"><label class="section-title">${title}</label><label class="killer-name">${escape(name)}</label></div></div>
    <div class="damage-summary"><div class="damage-section"><label class="section-title">${heading}</label>
      ${entries.map(([source, value]) => `<div class="damage-row"><label class="damage-source">${escape(source)}</label><label class="damage-value">${value}</label></div>`).join('')}
    </div>${inflicted}</div>
    <div class="spectate-prompt">${prompt}</div>
  </deathcam>`;
const spectator = (name, freecam = false) => `
  <spectating class="hud with-deadzone"><div class="spectator-target">${hint('SpectatorPrev')}
    <div class="spectator-identity"><label class="spectator-title">SPECTATING</label><label class="spectator-name">${escape(name)}</label></div>${hint('SpectatorNext')}
    </div>${freecam ? '' : `<div class="spectator-controls"><div class="spectator-action">${hint('SpectatorFreeCam')}<label>Freecam</label></div><div class="spectator-action">${hint('SpectatorMode')}<label>Mode</label></div></div>`}
  </spectating>`;

const background = fileUrl('C:/Users/leon2/AppData/Local/Temp/codex-clipboard-c429d58b-cc8f-4c25-a1e5-61e5f8ac8590.png');
const html = `<!doctype html><html><head><meta charset="utf-8"><title>Death HUD source preview</title>
  <style>
    @font-face { font-family: Dinish; src: url("${fileUrl(path.join(project, 'Assets/fonts/Dinish-Regular.ttf'))}"); font-weight: 400; }
    @font-face { font-family: Dinish; src: url("${fileUrl(path.join(project, 'Assets/fonts/Dinish-Bold.ttf'))}"); font-weight: 700; }
    * { box-sizing: border-box; }
    html, body { margin: 0; width: 100%; height: 100%; overflow: hidden; }
    body { background: linear-gradient(rgba(45,8,10,.5), rgba(35,4,7,.62)), url("${background}") center/cover; }
    body.spectator { background: linear-gradient(rgba(0,0,0,.15), rgba(0,0,0,.2)), url("${background}") center/cover; }
    .canvas { display: flex; position: relative; justify-content: center; align-items: center; width: 100%; height: 100%; }
    div, deathcam, spectating, inputhint { display: flex; }
    label { display: block; }
    inputhint { align-items: center; justify-content: center; }
    inputhint img { display: block; }
    .with-deadzone { margin: 25px; }
    .preview-note { position: absolute; left: 20px; top: 16px; color: #fff; font: 12px Dinish; opacity: .55; }
  </style>
  <link rel="stylesheet" href="Deathcam.css"><link rel="stylesheet" href="Spectating.css">
  </head><body><div class="canvas"><label class="preview-note">SOURCE LAYOUT PREVIEW · NOT AN IN-GAME CAPTURE</label>
  ${death('Echo BOT', 'KILLED BY', 'DAMAGE TAKEN', [['Echo BOT', '107 damage in 5 hits']], `<label>Press</label>${hint('Attack1')}<label>or</label>${hint('Attack2')}<label>to start spectating</label>`)}
  </div></body></html>`;
fs.writeFileSync(path.join(directory, 'index.html'), html);

const failures = [];
const browser = awaitBrowser();
async function awaitBrowser() { return chromium.launch({ headless: true, channel: 'chrome' }); }

(async () => {
  const instance = await browser;
  try {
    const page = await instance.newPage({ viewport: { width: 1024, height: 640 }, deviceScaleFactor: 1 });
    await page.goto(fileUrl(path.join(directory, 'index.html')));
    await page.evaluate(() => document.fonts.ready);
    const check = async (state, width) => {
      const findings = await page.evaluate(() => {
        const target = document.querySelector('deathcam, spectating');
        const bounds = target.getBoundingClientRect();
        const problems = [];
        if (bounds.left < 0 || bounds.right > window.innerWidth || bounds.bottom > window.innerHeight || bounds.top < 0) problems.push('HUD exceeds viewport');
        for (const row of document.querySelectorAll('.damage-row, .spectate-prompt, .spectator-target, .spectator-controls')) {
          if (row.scrollWidth > row.clientWidth + 1) problems.push(`${row.className}: horizontal overflow`);
        }
        return { width: window.innerWidth, panel: { x: bounds.x, y: bounds.y, width: bounds.width, height: bounds.height }, problems };
      });
      failures.push(...findings.problems.map(problem => `${state}@${width}: ${problem}`));
      console.log(JSON.stringify({ state, ...findings }));
      await page.screenshot({ path: path.join(directory, `${state}-${width}.png`) });
    };
    await check('death', 1024);
    await page.setViewportSize({ width: 640, height: 480 });
    await page.evaluate(markup => document.querySelector('.canvas').innerHTML = markup,
      death('A very long player name that should stay inside the death report', 'TUÉ PAR', 'DÉGÂTS SUBIS', [
        ['A very long attacker name with enough characters to need clipping', '107 dégâts en 5 coups'],
        ['Raven BOT', '24 dégâts en 2 coups']
      ], `<label>Appuyez sur</label>${hint('Attack1')}<label>ou</label>${hint('Attack2')}<label>pour observer</label>`,
      '<div class="damage-section"><label class="section-title">DÉGÂTS INFLIGÉS</label><div class="damage-row inflicted-row"><label class="damage-value">63 dégâts en 3 coups</label></div></div>'));
    await check('translated-long-names', 640);
    await page.setViewportSize({ width: 1024, height: 640 });
    await page.evaluate(markup => { document.body.className = 'spectator'; document.querySelector('.canvas').innerHTML = markup; }, spectator('Nova BOT'));
    await check('spectating', 1024);
    await page.setViewportSize({ width: 640, height: 480 });
    await page.evaluate(markup => document.querySelector('.canvas').innerHTML = markup, spectator('A very long spectator player name to check the navigation controls'));
    await check('spectating-long-name', 640);
    await page.evaluate(markup => document.querySelector('.canvas').innerHTML = markup, spectator('FREECAM', true));
    await check('freecam', 640);
    if (failures.length) throw new Error(failures.join('\n'));
    console.log('Layout checks passed. Native state transitions and glyph textures still require the game.');
  } finally {
    await instance.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });

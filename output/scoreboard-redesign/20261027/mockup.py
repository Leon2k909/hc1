"""Browser mockup of the scoreboard from its real SCSS (sass), rendered with headless Chrome at 1920x1080.

python mockup.py <scss file> <out.png> [backdrop.png]
s&box panels are all flex rows by default; the base CSS below imitates that."""
import subprocess, sys, html
from pathlib import Path

root = Path(r"C:\sbox-projects\hc1\forked-shooter-main")
here = Path(__file__).parent
scss_path = Path(sys.argv[1]); out = Path(sys.argv[2]).resolve()
backdrop = Path(sys.argv[3]).resolve() if len(sys.argv) > 3 else None

theme = (root / "Code/UI/Styles/Theme.scss").read_text(encoding="utf8")
src = theme[:theme.index("@import")] + "\n"
src += (root / "Code/UI/Styles/Colors.scss").read_text(encoding="utf8") + "\n"
src += (root / "Code/UI/Styles/Hud.scss").read_text(encoding="utf8")
src += "\n" + scss_path.read_text(encoding="utf8").replace('@import "/UI/Styles/Theme.scss";', "")
(here / "tmp.scss").write_text(src, encoding="utf8")
css = subprocess.run("npx --yes sass --no-source-map tmp.scss", cwd=here, shell=True, capture_output=True, text=True)
if css.returncode: sys.exit(css.stderr)
css = css.stdout

fonts = root / "Assets/fonts"
def face(family, file, weight, style="normal"):
    return f"@font-face {{ font-family: '{family}'; src: url('{(fonts / file).as_uri()}'); font-weight: {weight}; font-style: {style}; }}"
faces = "\n".join([face("Chakra Petch", f"ChakraPetch-{n}.ttf", w) for n, w in
                   [("Light", 300), ("Regular", 400), ("Medium", 500), ("SemiBold", 600), ("Bold", 700)]]
                  + [face("Dinish", "Dinish-Regular.ttf", 400), face("Dinish", "Dinish-Bold.ttf", 700),
                     face("Material Icons", "MaterialIcons-Regular.ttf", 400)])
icon_font = Path(r"C:\Program Files (x86)\Steam\steamapps\common\sbox\core\fonts\MaterialIcons-Regular.ttf")
faces = faces.replace((fonts / "MaterialIcons-Regular.ttf").as_uri(), icon_font.as_uri())

base = """
html, body { margin: 0; width: 1920px; height: 1080px; overflow: hidden; background: #222; }
body { position: relative; }
scoreboard, scoreboard * { display: flex; flex-direction: row; box-sizing: border-box; flex-shrink: 1; }
scoreboard label { display: block; }
scoreboard i { font-family: 'Material Icons'; font-style: normal; font-weight: normal; line-height: 1; }
scoreboard button { background: none; border: none; padding: 0; color: inherit; }
scoreboard .scoreboard-body { overflow: auto; scrollbar-width: none; }
.backdrop { position: absolute; inset: 0; background-size: cover; }
.strip { position: absolute; top: 16px; left: 0; right: 0; display: flex; flex-direction: column; align-items: center; z-index: 3000;
  font-family: Dinish; font-weight: bold; color: #F4F4F0; }
.strip .row { display: flex; height: 36px; border: 1px solid rgba(0,0,0,.5); }
.strip .t { min-width: 70px; display: flex; align-items: center; justify-content: center; font-size: 24px; }
.strip .c { min-width: 88px; display: flex; align-items: center; justify-content: center; font-size: 22px; background: rgba(8,10,13,.9); border-bottom: 2px solid #FF7A1A; }
.strip .m { margin-top: 6px; font-size: 12px; letter-spacing: 3px; text-shadow: 0 0 4px black; }
"""

img = lambda p: (root / "Assets" / p).as_uri()
RED, BLUE = "#E42028", "#0592EB"

def hexa(c, a):
    return c + format(round(a * 255), "02x")

def band(c):
    return f"border-left-color: {c}; background-image: linear-gradient( to right, {hexa(c, .3)}, {hexa(c, .03)} );"

def row(i, name, pts, k, d, ping=None, bot=None, local=False, dead=False, prestige=0, party=False):
    cls = "scoreboard-row" + (" local" if local else "") + (" dead" if dead else "") + (" bot-row" if bot else "")
    style = f"background-color: {hexa(bot, .045)}; border-left-color: {hexa(bot, .5)};" if bot else ""
    if bot:
        portrait = f'<img class="bot-avatar" src="{img("ui/bot_avatar.png")}" style="background-color: {hexa(bot, .18)}; border-color: {hexa(bot, .4)};"/>'
        accent = bot
        meta = f'<label class="bot-prefix" style="color: {accent}">BOT</label><label class="latency" style="color: {accent}">AI</label>'
        meta += '<div class="row-actions"><button class="mute-toggle kick-bot"><i>person_remove</i></button></div>'
    else:
        portrait = f'<div style="width:34px;height:34px;background:linear-gradient(135deg,#4a5866,#232a31);border-radius:2px"></div>'
        meta = ('<i class="local-marker">arrow_right</i>' if local else "")
        meta += f'<i class="connection-icon">signal_cellular_alt</i><label class="latency">{ping} ms</label>'
        if party: meta += f'<img src="{img("ui/party-member.png")}" style="width:16px;height:16px"/>'
        if not local:
            meta += '<div class="row-actions"><button class="mute-toggle"><i>speaker_notes</i></button><button class="mute-toggle"><i>mic</i></button></div>'
    pres = f'<img class="prestige" src="{img(f"ui/prestige/prestige_{prestige}_readable.png")}"/>' if prestige else ""
    crown = f'<div class="leader-crown" style="width:16px;height:16px;background-color:#FFB13D;-webkit-mask:url({img("ui/crown.png")}) center/contain no-repeat"></div>' if i == 1 else ""
    arrow = '' if bot else '<i class="sharing-arrow">chevron_right</i>'
    ratio = f"{k / max(d, 1):.2f}"
    return f'''<div class="{cls}" style="{style}"><label class="col placement">{i:02d}</label>
<div class="col playername"><div class="portrait">{portrait}</div><div class="player-identity">
<span class="name-line {'' if bot else 'inspectable'}">{pres}<label class="player-label">{html.escape(name)}</label>{crown}{arrow}</span>
<div class="player-meta">{meta}</div></div></div>
<label class="col stat score-value">{pts}</label><label class="col stat">{k}</label><label class="col stat">{d}</label><label class="col stat">{ratio}</label></div>'''

cols = '<div class="scoreboard-columns"><label class="col placement">#</label><label class="col playername">PLAYER</label><label class="col stat score-value">POINTS</label><label class="col stat">KILLS</label><label class="col stat">DEATHS</label><label class="col stat">RATIO</label></div>'

def roster(name, color, logo, score, rows):
    return f'''<div class="team-roster"><div class="team-heading" style="{band(color)}">
<img class="team-logo" src="{img(logo)}" style="width:54px;height:54px"/>
<div class="team-identity"><label class="team-name">{name}</label><label class="team-count">{len(rows)} PLAYERS</label></div>
<button class="add-bot"><i>person_add</i><label>ADD BOT</label></button>
<label class="team-score">{score}</label></div>{cols}{''.join(rows)}</div>'''

red = [row(1, "Leon", 2350, 21, 9, 12, local=True, prestige=3, party=True),
       row(2, "Mason", 1800, 16, 11, bot=RED),
       row(3, "kaiserschmarrn", 1425, 12, 10, 48, party=True),
       row(4, "Okafor", 900, 8, 13, bot=RED, dead=True),
       row(5, "Petrova", 650, 5, 14, bot=RED)]
blue = [row(1, "Reyes", 2100, 19, 12, bot=BLUE),
        row(2, "xX_Gh0st_Xx", 1700, 15, 13, 87, prestige=1),
        row(3, "Lindqvist", 1300, 11, 12, bot=BLUE, dead=True),
        row(4, "Tanaka", 1050, 9, 15, bot=BLUE),
        row(5, "Haddad", 700, 6, 16, bot=BLUE)]

board = f'''<scoreboard class="hidden scoreboard-root visible"><div class="scoreboard-panel">
<div class="match-heading"><div class="match-identity"><label class="eyebrow">SCOREBOARD</label><label class="match-title">TEAM DEATHMATCH</label></div>
<div class="match-state"><label class="match-status">Play Game</label></div>
<div class="match-clock"><i>schedule</i><label>7:42</label></div></div>
<div class="scoreboard-body"><div class="rosters split-rosters">
{roster("RED TEAM", RED, "ui/teams/red_team_logo.png", 61, red)}
{roster("BLUE TEAM", BLUE, "ui/teams/blue_team_logo.png", 58, blue)}
</div></div>
<div class="communications"><div class="voice-label"><i>headset_mic</i><label>VOICE CHANNEL:</label></div>
<div class="voice-options"><button class="voice-option selected">AUTO</button><button class="voice-option">LOBBY</button><button class="voice-option">TEAM</button><button class="voice-option">PARTY</button></div>
<button class="proximity-option selected"><i>spatial_audio_off</i><label>PROX CHAT</label></button></div>
<div class="scoreboard-footer"><label class="sharing-hint">Click a player to copy their gun builds or crosshair.</label>
<div class="scoreboard-key"><span style="font-family:Chakra Petch;font-size:11px;font-weight:700;color:#ddd;border:1px solid rgba(255,255,255,.3);padding:2px 6px;border-radius:2px">TAB</span><label>SCOREBOARD</label></div></div>
</div></scoreboard>'''

strip = f'<div class="strip"><div class="row"><div class="t" style="background:{RED}">61</div><div class="c">7:42</div><div class="t" style="background:{BLUE}">58</div></div><div class="m">TEAM DEATHMATCH</div></div>'
bg = f'<div class="backdrop" style="background-image:url({backdrop.as_uri()})"></div>' if backdrop else ""
doc = f"<!doctype html><html><head><meta charset='utf-8'><style>{faces}\n{base}\n{css}</style></head><body>{bg}{board}{strip}</body></html>"
page = here / (out.stem + ".html")
page.write_text(doc, encoding="utf8")
chrome = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
subprocess.run([chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--allow-file-access-from-files",
                "--force-device-scale-factor=1", "--window-size=1920,1080", f"--screenshot={out}", page.as_uri()],
               capture_output=True, timeout=120)
print(out, out.exists())

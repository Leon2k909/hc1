"""
The AK-105's shot, voiced away from Call of Duty's sound design towards what a shooter hears from a real short 5.45 rifle.

    python Tools/ak105_shot.py [--preview <wav>]

ak105_assets.py makes the shot with build() here, from MWII's rip: the recording and its ADS take, turned down
SHOT_GAIN_DB to the 74u's level. Run on its own, this script does the same and rewrites
Assets/Weapons/AK105/sounds/ak105_shot_01-04.wav and ak105.fire.sound's list and pitch, leaving the gun's other sounds
alone. --preview writes a demo instead of the assets: the ripped shot, the voiced one, then eight rounds at the gun's
600 rpm each way. The ripped shot as it was, levelled, is in Backups/ak105_shot_rip/. The steps are shot_voicing.py's.

As ripped, the shot is a game sound more than a gunshot:
- under the blast, a designed sub "drop" peaks at 27 Hz and rings for 300 ms. No rifle puts that at the shooter's ear;
- its low thump (60-120 Hz) is louder than the blast's crack, where a short barrel's blast is loudest in the midrange;
- it's dry: 0.4 s after its loudest 100 ms it's 45 dB down, where the other rifles' shots are 22-35 dB down. CoD plays
  environment tails on top, which the port doesn't.

Its voicing, by shot_voicing's steps:
1. Pitch up 3%: a lighter, snappier report than CoD's heavy one.
2. Low end: a high-pass at 40 Hz (the 27 Hz drop falls 14 dB), and after the blast's first 35 ms everything under
   110 Hz eases down 5 dB.
3. The blast: the 1.5-5 kHz presence of its first 25 ms up 4 dB, the sharp crack a short barrel gives.
4. The ground 7.2 ms after the direct sound (the muzzle 0.6 m ahead of the ear: a 2.5 m longer path), 18 dB down.
5. Echoes from 35 ms to 1.4 s. The tail sits where the M16A4's and AUG's do.
The two recordings make two takes each. Voiced, the soft clipper takes about 2.4 dB off the blast's peaks.
"""
import tempfile
from pathlib import Path

import shot_voicing
from shot_voicing import Voicing

OUT = Path(__file__).resolve().parent.parent / "Assets" / "Weapons" / "AK105" / "sounds"
FIRE_EVENT = OUT / "ak105.fire.sound"

VOICING = Voicing(
    name="ak105_shot",
    pitch=1.03,
    # A little pitch spread per round, as the other guns' events have. Four takes, so less than the rip's two needed.
    event_pitch="0.98 1.02",
    takes=((0, 105), (1, 106), (0, 107), (1, 108)),
    rpm=600,
    preview_bursts=(8,),
)
EVENT_PITCH = VOICING.event_pitch


def ripped():
    """The two recordings as they come from the rip, turned down SHOT_GAIN_DB, and as ak105_assets levelled them
    before they were voiced."""
    from ak105_assets import SHOT, SHOT_GAIN_DB, level_shots
    from ks74u_assets import EXTRACTED
    sources = [SHOT, f"{SHOT}_ads"]
    raw = shot_voicing.decode([EXTRACTED / "sound" / f"{source}.ogg" for source in sources], SHOT_GAIN_DB)
    with tempfile.TemporaryDirectory() as temp:
        levelled = [shot_voicing.read_wav(str(path)) for path in level_shots(Path(temp), sources, "ak105_shot")]
    return raw, levelled


def build(out):
    """Writes the takes into `out` (a Path) and returns their WAV paths."""
    return shot_voicing.build(VOICING, out, ripped)


if __name__ == "__main__":
    shot_voicing.main(VOICING, ripped, OUT, FIRE_EVENT)

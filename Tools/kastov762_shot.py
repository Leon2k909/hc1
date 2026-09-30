"""
The Kastov 762's shot (the RPK fires it too), voiced away from Call of Duty's sound design towards what a shooter hears
from a real 7.62x39 AK fired outdoors.

    python Tools/kastov762_shot.py [--preview <wav>]

kastov_sounds.py makes the shot with build() here, from MW2019's AK-47 rip (the MW base addon's three close shots).
Run on its own, this script does the same and rewrites Assets/sounds/weapons/kastov/kastov_shot_01-04.wav and
kastov_shot.sound's list and pitch, leaving the gun's other sounds alone. --preview writes a demo instead of the
assets: the ripped shot, the voiced one, then eight rounds at the gun's 600 rpm each way. The ripped shot as it was
(each close shot mixed with its atmosphere tail) is in Backups/kastov762_shot_rip/. The steps are shot_voicing.py's.

As ripped, the shot is two of CoD's layers, mixed at 0.65 as the game plays them:
- the close shot: the blast clipped near full scale for its first 40 ms (kept, as on the AK-105 and M16A4), the bolt
  carrier slamming home ~92 ms later (kept: at 600 rpm that's the real cycle, and the shooter hears it), then under
  150 Hz a designed rumble that runs on for the whole second, 20 dB over everything else;
- an "atmosphere" tail that opens with a boom of its own, 45-180 Hz at full scale for its first 20 ms, as loud as the
  blast's midrange, then washes out over 4.7 s like a hall. The real report's low end is the blast's own; the tail at
  the shooter is echoes off what's around. The voicing leaves this layer out and makes the echoes from the blast.

Its voicing, by shot_voicing's steps:
1. Pitch down 2%: the 7.62x39's heavier charge and wider bore give a longer, deeper blast than the 5.45 and 5.56 rifles'
   (the AK-105's is voiced 3% up).
2. Low end: a high-pass at 40 Hz, and after the blast's first 40 ms everything under 130 Hz eases down 6 dB. The first
   40 ms keep their thump, which is the 7.62's. The rip's own sound eases 10 dB from 110 ms, after the carrier's clack,
   so the rumble gives way to the echoes.
3. The blast: its 1.5-5 kHz presence up 2 dB for its first 20 ms. Less than the carbines' (3-4 dB): the rip's crack is
   already bright, and a 7.62x39's blast is weighted lower.
4. The ground 7.1 ms after the direct sound: the AKM is 0.88 m long, so with the cheek a quarter of it from the butt
   the muzzle is 0.63 m ahead of the ear, 1.5 m up: a 2.4 m longer path. The RPK's muzzle is 0.16 m further out
   (6.7 ms), close enough to share it.
5. Echoes from 35 ms to 1.4 s, the same surroundings as the AK-105's and M16A4's, with their own seeds.
The three recordings make four takes, and the event's pitch spread stays 0.98-1.02. Loudness matches the old mix's.
"""
import tempfile
from pathlib import Path

import shot_voicing
from shot_voicing import Voicing

OUT = Path(__file__).resolve().parent.parent / "Assets" / "sounds" / "weapons" / "kastov"
FIRE_EVENT = OUT / "kastov_shot.sound"

VOICING = Voicing(
    name="kastov_shot",
    pitch=0.98,
    event_pitch="0.98 1.02",
    takes=((0, 761), (1, 762), (2, 763), (0, 764)),
    rip_pitch=(0.98, 1.02),
    rpm=600,
    preview_bursts=(8,),
    high_pass=40.0,
    low_split=130.0,
    low_cut_db=-6.0,
    low_hold=0.04,
    low_ease=0.04,
    rip_tail_db=-10.0,
    rip_tail_hold=0.11,
    rip_tail_ease=0.12,
    presence=(1500.0, 5000.0),
    presence_db=2.0,
    presence_hold=0.02,
    presence_ease=0.02,
    ground_delay=0.0071,
    tail_at_400ms=-33.0,
)
EVENT_PITCH = VOICING.event_pitch


def ripped():
    """The three close shots as they come from the rip, and as kastov_sounds mixed them with their atmosphere tails
    before they were voiced."""
    from kastov_sounds import SOURCE, mix
    shots = [SOURCE / "fire" / f"weap_rex_akilo_fire_plr_shot_{index:02d}.wav" for index in (1, 2, 3)]
    raw = shot_voicing.decode(shots, 0.0)
    levelled = []
    with tempfile.TemporaryDirectory() as temp:
        for index, shot in enumerate(shots, start=1):
            path = Path(temp) / f"mixed_{index}.wav"
            mix(shot, SOURCE / "fire" / f"weap_rex_akilo_fire_plr_atmo_{index:02d}.wav", path)
            levelled.append(shot_voicing.read_wav(str(path)))
    return raw, levelled


def build(out):
    """Writes the takes into `out` (a Path) and returns their WAV paths."""
    return shot_voicing.build(VOICING, out, ripped)


if __name__ == "__main__":
    shot_voicing.main(VOICING, ripped, OUT, FIRE_EVENT)

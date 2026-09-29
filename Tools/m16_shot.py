"""
The M16A4's shot, voiced away from Call of Duty's sound design towards what a shooter hears from a real 20-inch 5.56
rifle.

    python Tools/m16_shot.py [--preview <wav>]

m16_assets.py makes the shot with build() here, from the addon's rip (MWII's M4 recording and its ADS take), turned down
SHOT_GAIN_DB to the AK-105's level. Run on its own, this script does the same and rewrites
Assets/Weapons/M16/sounds/m16_shot_01-04.wav and m16.fire.sound's list and pitch, leaving the gun's other sounds alone.
--preview writes a demo instead of the assets: the ripped shot, the voiced one, then three three-round bursts at the
gun's 800 rpm each way. The ripped shot as it was, levelled, is in Backups/m16_shot_rip/. The steps are
shot_voicing.py's.

As ripped, it's a carbine's shot mastered for a game:
- a 48 Hz boom holds for 200 ms under the blast, and under 200 Hz a rumble runs on for the whole second, 20-30 dB
  over everything else in the tail. That's CoD's designed low end, not a rifle outdoors: at the shooter the tail is
  echoes, and they're mostly mids;
- in its first 150 ms the lows (20-300 Hz) are as loud as the blast's midrange, which is a carbine's concussion. The
  M16A4's 20-inch barrel burns more of the powder before the muzzle: less pressure there, and a less concussive, sharper
  report;
- its first 83 ms are clipped flat at full scale, 150 times per channel, and the codec has smeared the plateaus, so
  the samples round them hover near full scale too. That's beyond repair by interpolating across the plateaus (tried:
  the fits stay flat), so the voiced shot keeps it, as the AK-105's does.

Its voicing, by shot_voicing's steps:
1. Pitch up 2%: the lower muzzle pressure gives a shorter blast, a little higher than the carbine's.
2. Low end: a high-pass at 45 Hz (the boom's lower half), and after the blast's first 25 ms everything under 140 Hz
   eases down 8 dB, which takes the rumble out from under the tail.
3. The blast: its 1.5-6 kHz presence up 3 dB for its first 20 ms.
4. The ground 6.8 ms after the direct sound: the muzzle 0.75 m ahead of the ear (the rifle's 1 m length, the cheek a
   quarter of it from the butt), 1.5 m up, so a 2.3 m longer path.
5. Echoes from 35 ms to 1.4 s, the same surroundings as the AK-105's, with their own seeds. With the rumble gone, the
   tail sits where the rip's did (-32.5 dB 0.4 s after the loudest 100 ms), but it's echoes instead.
The ADS take is nearly the hip take, so the four takes differ mostly in their echoes, and the event's pitch spread.
"""
import tempfile
from pathlib import Path

import shot_voicing
from shot_voicing import Voicing

OUT = Path(__file__).resolve().parent.parent / "Assets" / "Weapons" / "M16" / "sounds"
FIRE_EVENT = OUT / "m16.fire.sound"

VOICING = Voicing(
    name="m16_shot",
    pitch=1.02,
    event_pitch="0.98 1.02",
    takes=((0, 161), (1, 162), (0, 163), (1, 164)),
    rpm=800,
    preview_bursts=(3, 3, 3),
    high_pass=45.0,
    low_split=140.0,
    low_cut_db=-6.0,
    low_hold=0.025,
    low_ease=0.03,
    rip_tail_db=-12.0,
    rip_tail_hold=0.08,
    rip_tail_ease=0.12,
    presence=(1500.0, 6000.0),
    presence_db=3.0,
    presence_hold=0.02,
    presence_ease=0.02,
    ground_delay=0.0068,
    tail_at_400ms=-33.0,
)
EVENT_PITCH = VOICING.event_pitch


def ripped():
    """The two recordings as they come from the rip, turned down SHOT_GAIN_DB, and as m16_assets levelled them
    before they were voiced."""
    from m16_assets import EXTRACTED, SHOT, SHOT_GAIN_DB, level_shots
    sources = [SHOT, f"{SHOT}_ads"]
    raw = shot_voicing.decode([EXTRACTED / "sound" / f"{source}.wav" for source in sources], SHOT_GAIN_DB)
    with tempfile.TemporaryDirectory() as temp:
        levelled = [shot_voicing.read_wav(str(path))
                    for path in level_shots(Path(temp), sources, "m16_shot", SHOT_GAIN_DB)]
    return raw, levelled


def build(out):
    """Writes the takes into `out` (a Path) and returns their WAV paths."""
    return shot_voicing.build(VOICING, out, ripped)


if __name__ == "__main__":
    shot_voicing.main(VOICING, ripped, OUT, FIRE_EVENT)

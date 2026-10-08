"""
The rest of the ported guns' shots, voiced away from Call of Duty's sound design towards what a shooter hears from the
real gun fired outdoors, as ak105_shot.py, m16_shot.py and kastov762_shot.py do for theirs. The steps are
shot_voicing.py's; this holds each gun's Voicing, where its rip comes from and what the rip gets wrong.

    python Tools/ported_shots.py <gun>|all [--preview <wav>]

<gun> is vityaz, bizon, vepr12, p90, mp7, aug, uzi, fal, m18, famas, mcx, l85a2, hk416, ak12, ak15 or ak74m. Each
gun's assets script builds its shot with build() here. Run on its own, this does the same: it rewrites the gun's
<name>_NN.wav takes and its fire event's list and pitch, leaving the gun's other sounds alone. --preview writes a demo
instead: the ripped shot, the voiced one, then a burst at the gun's rate each way. The ripped shots and events as they
were are in Backups/ported_shots_rip/<gun>/. The suppressed shots are voiced from these voicings by
suppressed_shots.py.

What every rip here gets wrong, measured on the levelled files (python's describe(): the loudest 100 ms, the level
0.2 / 0.4 s after it, and the lows under 150 Hz against the blast's first 100 ms, 100-250 ms after the onset):
- The lows ring on after the blast. At a real shooter's ear the thump is the blast's own and over in tens of ms; CoD
  holds a designed boom under it. It's at its worst in the FAL (as loud as the blast at 100-250 ms), the Vepr-12 (-2 dB)
  and the Vityaz (-9 dB); the voiced rifles have it at -22.
- The single-recording MW2019 guns (P90, MP7A1, AUG, Uzi, FAMAS, L85A2) are dry: nothing of the surroundings, or a short
  designed room, and one recording replayed for every round. Here each recording makes several takes with their own
  echoes.
- The HK416's two are Escape from Tarkov's, with an outdoor tail baked in: 14-17 dB under the blast at 0.2 s, where the
  voiced rifles' are 18-20 dB under it. The AK-12's four are Tarkov's too, each under the tail Tarkov plays after the
  last round: 18 dB under the blast at 0.2 s, but still 23 at 0.4 s, where the voiced rifles' are 33. The AK-15's
  (Tarkov's AKM) are built the same way, but their tail is already the voiced rifles', and the AK-74M's is quieter
  than theirs (36 dB under at 0.4 s).
- Some are dark: the Uzi's first 150 ms sit almost all under 300 Hz (its first 30 ms centre at 435 Hz, the voiced
  rifles' at 1.4-1.6 kHz), the AUG's and FAMAS's at 1.0-1.3 kHz. A small-arms blast at the shooter is a sharp crack.

Each gun's voicing, by shot_voicing's steps:
1. Pitch, by the charge and the barrel. A smaller charge, burnt out in a short barrel, makes a smaller, shorter blast
   (so higher); a heavier one a longer, deeper one: the 9 mm guns and the P90 2% up, the MP7A1's 4.6x30 3%, the FAMAS's
   5.56 from a 488 mm barrel 1%, the AUG, the L85A2 and the HK416 as ripped (5.56 shots), the AK-12 and AK-74M as
   ripped (5.45) and the AK-15 (7.62x39 from the same barrel), the M18 as ripped (a 9 mm pistol burns much of its
   powder past the muzzle), the Vepr-12's 12-gauge 1% down and the FAL's 7.62x51 2% down.
2. Low end: a 40 Hz high-pass (the Uzi's at 70), and after the blast's first 20-50 ms (the Uzi's 8) the lows ease
   down 3-10 dB. The FAL's, Vepr-12's and AUG's designed tails are eased too, from 100, 150 and 80 ms, as the
   M16A4's is, the Uzi's a little from 120 ms, the HK416's baked-in one 20 dB from 80 ms, the AK-12's 14 dB, and the
   AK-15's and AK-74M's 6 dB from 100 ms.
3. The blast's 1.5-5 kHz up 2-4 dB for its first 20-25 ms: less on the rips that are already bright (Vityaz, Bizon,
   P90), more on the dark ones (AUG, FAMAS, FAL, MP7A1, AK-74M). The Uzi's 1-6 kHz 7 dB, for 30 ms.
4. The ground, with the muzzle 1.5 m up and ahead of the ear by the gun's length (the cheek a little ahead of the butt;
   a pistol at arm's length): 6.6 ms for the FAL (0.87 m) to 7.7 ms for the P90 (0.4 m, a bullpup).
5. Echoes from 35 ms to 1.4 s, the same surroundings as the voiced rifles'. The echoes' level against the direct blast
   follows how far the muzzle is from the ear: -33 dB 0.4 s after the loudest 100 ms at a rifle's 0.6-0.7 m, -35 for
   the SMGs' ~0.47 m, -36 for the P90's 0.4, -31.5 for the FAL's 0.87, -34 for the MCX's 0.54 and the HK416's 0.56,
   and -33 for the AK-12's, AK-15's and AK-74M's 0.73.
Loudness matches each rip as its assets script levelled it (K-weighted, loudest 100 ms). The event's pitch spread is
0.98-1.02 where the rip has several recordings, and 0.97-1.03 where it has one (the takes' echoes vary, not the blast).
"""
import argparse
import json
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

import shot_voicing
from shot_voicing import Voicing

ASSETS = Path(__file__).resolve().parent.parent / "Assets"


@dataclass(frozen=True)
class Gun:
    voicing: Voicing
    # Where the takes go, and the fire event whose list and pitch they replace.
    folder: str
    event: str
    # The recordings as decode() gives them (float, turned down to the gun's level, not limited) and as the gun's
    # assets script levels them (limited to -1 dBFS): () -> (raw, levelled).
    ripped: Callable[[], tuple[list, list]]
    # How far the muzzle is from the ear, and why, for the record.
    note: str = ""


def _read(paths):
    return [shot_voicing.read_wav(str(p)) for p in paths]


def _levelled(level):
    """What the assets script's own levelling writes, read back: level(temp dir) -> WAV paths."""
    with tempfile.TemporaryDirectory() as temp:
        return _read(level(Path(temp)))


def _mix(layers):
    out = np.zeros((max(len(x) for x in layers), 2))
    for x in layers:
        out[:len(x)] += x
    return out


def _vityaz():
    import vityaz_assets as a
    src = a.EXTRACTED / "sound" / a.SOUND_DIR
    raw = [_mix(shot_voicing.decode([src / f"weap_aviktor_fire_plr_shot_{i:02d}.ogg",
                                     src / f"weap_aviktor_fire_plr_mech_{i:02d}.ogg"], a.SHOT_GAIN_DB))
           for i in range(1, a.SHOTS + 1)]
    return raw, _levelled(lambda out: a.mix_shots(out, "fire_plr_shot", "x"))


def _bizon():
    import bizon_assets as a
    src = a.EXTRACTED / "sound" / a.SOUND_DIR
    raw = shot_voicing.decode([src / f"weap_beta_fire_plr_shot_{i:02d}_mech.ogg" for i in range(1, a.SHOTS + 1)],
                              a.SHOT_GAIN_DB)
    return raw, _levelled(lambda out: a.level_shots(out, "fire_plr_shot", "x"))


def _vepr12():
    import vepr12_assets as a
    sources = [a.SHOT, f"{a.SHOT}_ads"]
    raw = shot_voicing.decode([a.EXTRACTED / "sound" / f"{s}.ogg" for s in sources], a.SHOT_GAIN_DB)
    return raw, _levelled(lambda out: a.level_shots(out, sources, "x"))


def _single(module):
    """A gun whose assets script levels one recording with level_shot(out, SHOT, name, SHOT_GAIN_DB)."""
    def ripped():
        a = __import__(module)
        raw = shot_voicing.decode([a.EXTRACTED / "sound" / a.SHOT], a.SHOT_GAIN_DB)
        return raw, _levelled(lambda out: [a.level_shot(out, a.SHOT, "x", a.SHOT_GAIN_DB)])
    return ripped


def _fal():
    import fal_assets as a
    raw = shot_voicing.decode([a.EXTRACTED / "sound" / s for s in a.SHOTS], a.SHOT_GAIN_DB)
    return raw, _levelled(lambda out: a.level_shots(out, a.SHOTS, "x", a.SHOT_GAIN_DB))


def _mcx():
    import mcx_assets as a
    raw = shot_voicing.decode([a.EXTRACTED / "sound" / s for s in a.SHOTS], a.SHOT_GAIN_DB)
    return raw, _levelled(lambda out: a.level_shots(out, a.SHOTS, "x", a.SHOT_GAIN_DB))


FAMAS_SHOT = "viper/weapons/falpha/weap_famas_fire_plr_01.wav"


def _hk416():
    import hk416_assets as a
    raw = [x for source, gain in a.SHOTS for x in shot_voicing.decode([a.EXTRACTED / "sound" / source], gain)]
    return raw, _levelled(lambda out: a.level_shots(out, "x"))


def _start_and_tail(module):
    """Tarkov's shots as its pack plays a single one: each start mixed under the last round's tail."""
    def ripped():
        a = __import__(module)
        starts, tail, gain = a.SHOTS
        raw = [_mix([*shot_voicing.decode([a.EXTRACTED / "sound" / start], gain),
                     *shot_voicing.decode([a.EXTRACTED / "sound" / tail], gain)]) for start in starts]
        return raw, _levelled(lambda out: a.level_shots(out, "x"))
    return ripped


_ak12 = _start_and_tail("ak12_assets")
_ak15 = _start_and_tail("ak15_assets")
_ak74m = _start_and_tail("ak74m_assets")


def _famas():
    import famas_assets as a
    from ks74u_assets import ffmpeg

    def level(out):
        # famas_assets.sounds() converts the shot this way (0 dB, limited), alongside everything else.
        wav = out / "x_01.wav"
        ffmpeg(["-i", str(a.EXTRACTED / "sound" / FAMAS_SHOT), "-af",
                "volume=0dB,alimiter=limit=0.891:attack=1:release=50:level=false",
                "-ar", "44100", "-ac", "2", "-c:a", "pcm_s16le", str(wav)])
        return [wav]
    raw = shot_voicing.decode([a.EXTRACTED / "sound" / FAMAS_SHOT], 0.0)
    return raw, _levelled(level)


def _takes(recordings, seed, count=None):
    """(recording, seed) for each take: one per recording, or `count` cycling through them."""
    count = count or recordings
    return tuple((i % recordings, seed + i) for i in range(count))


GUNS = {
    # 9x19 from a 230 mm barrel, 750 rpm. The rip mixes each shot with its bolt's mechanical layer (kept: it's the
    # gun's own cycle). As levelled: the lows hold at -9 dB 100-250 ms after the onset and -20 at 250-500; the tail is
    # a dry -40 dB at 0.4 s. The blast is already bright (its first 30 ms centre at 2.0 kHz).
    "vityaz": Gun(Voicing(
        name="vityaz_shot", pitch=1.02, event_pitch="0.98 1.02", takes=_takes(8, 1901), rip_pitch=(0.98, 1.02),
        rpm=750, preview_bursts=(8,), low_split=130.0, low_cut_db=-7.0, low_hold=0.03, low_ease=0.03,
        presence_db=2.0, presence_hold=0.02, ground_delay=0.0075, tail_at_400ms=-35.0),
        "Weapons/Vityaz/sounds", "Weapons/Vityaz/sounds/vityaz.fire.sound", _vityaz,
        "stock extended, 0.71 m long: the muzzle ~0.5 m ahead of the ear"),
    # 9x18 from a 230 mm barrel, 680 rpm, eight recordings with the mechanical layer in them. Its lows fall away
    # quickly already (-31 dB at 100-250 ms); the tail is -35 dB at 0.4 s. Bright: 2.4 kHz.
    "bizon": Gun(Voicing(
        name="bizon_shot", pitch=1.02, event_pitch="0.98 1.02", takes=_takes(8, 1911), rip_pitch=(0.98, 1.02),
        rpm=680, preview_bursts=(8,), low_split=130.0, low_cut_db=-3.0, low_hold=0.03, low_ease=0.03,
        presence_db=2.0, presence_hold=0.02, ground_delay=0.0075, tail_at_400ms=-35.0),
        "Weapons/Bizon/sounds", "Weapons/Bizon/sounds/bizon.fire.sound", _bizon,
        "stock unfolded, 0.66 m long: the muzzle ~0.47 m ahead"),
    # 12-gauge 00 buck from a 305 mm barrel, semi (fired here at a steady 300 rounds a minute). The hip and aimed shots.
    # As levelled: a designed boom under 150 Hz at -2 dB 100-250 ms after the onset and -12 at 250-500, and the whole
    # sound still -25 dB at 0.4 s. Dark: everything over 800 Hz 6-12 dB under the lows. A 12-gauge's report is a
    # deep boom, but its body is the blast's first tens of ms.
    "vepr12": Gun(Voicing(
        name="vepr12_shot", pitch=0.99, event_pitch="0.97 1.03", takes=_takes(2, 1921, 4), rip_pitch=(0.96, 1.04),
        rpm=300, preview_bursts=(3,), high_pass=40.0, low_split=150.0, low_cut_db=-8.0, low_hold=0.05,
        low_ease=0.04, rip_tail_db=-10.0, rip_tail_hold=0.15, rip_tail_ease=0.12, presence_db=3.0,
        presence_hold=0.025, ground_delay=0.0069, tail_at_400ms=-33.0),
        "Weapons/Vepr12/sounds", "Weapons/Vepr12/sounds/vepr12.fire.sound", _vepr12,
        "~0.95 m long: the muzzle ~0.7 m ahead"),
    # SS190 from a 264 mm barrel, 900 rpm, one recording. As levelled: the lows hold at -1.5 dB 30-100 ms after the
    # onset; then nothing at all, -58 dB at 0.4 s, and the blast clipped flat for 2.5 ms.
    "p90": Gun(Voicing(
        name="p90_shot", pitch=1.02, event_pitch="0.97 1.03", takes=_takes(1, 1931, 4), rip_pitch=(0.95, 1.05),
        rpm=900, preview_bursts=(10,), low_split=130.0, low_cut_db=-6.0, low_hold=0.025, low_ease=0.03,
        presence_db=2.0, presence_hold=0.02, ground_delay=0.0077, tail_at_400ms=-36.0),
        "Weapons/P90/sounds", "Weapons/P90/sounds/p90.fire.sound", _single("p90_assets"),
        "a bullpup, 0.5 m long: the muzzle ~0.4 m ahead"),
    # DM11 from a 180 mm barrel, 950 rpm, one recording. As levelled: the lows at -2 dB 30-100 ms after the onset;
    # dark (its first 30 ms centre at 1.4 kHz, over 800 Hz 10-18 dB under the lows); -40 dB at 0.4 s.
    "mp7": Gun(Voicing(
        name="mp7_shot", pitch=1.03, event_pitch="0.97 1.03", takes=_takes(1, 1941, 4), rip_pitch=(0.95, 1.05),
        rpm=950, preview_bursts=(10,), low_split=130.0, low_cut_db=-6.0, low_hold=0.025, low_ease=0.03,
        presence_db=4.0, presence_hold=0.02, ground_delay=0.0076, tail_at_400ms=-35.0),
        "Weapons/MP7/sounds", "Weapons/MP7/sounds/mp7.fire.sound", _single("mp7_assets"),
        "stock extended, 0.64 m long: the muzzle ~0.45 m ahead"),
    # M855 from a 407 mm barrel, 715 rpm, one recording (MW2019's 5.56 conversion). As levelled: the lows at -2 dB
    # 30-100 ms after the onset; dark (1.05 kHz, over 800 Hz 9-18 dB down); -33 dB at 0.4 s (a short designed room).
    "aug": Gun(Voicing(
        name="aug_shot", pitch=1.0, event_pitch="0.97 1.03", takes=_takes(1, 1951, 4), rip_pitch=(0.95, 1.05),
        rpm=715, preview_bursts=(8,), low_split=130.0, low_cut_db=-6.0, low_hold=0.03, low_ease=0.035,
        rip_tail_db=-10.0, rip_tail_hold=0.08, rip_tail_ease=0.1, presence_db=4.0, presence_hold=0.025,
        ground_delay=0.0071, tail_at_400ms=-33.0),
        "Weapons/AUG/sounds", "Weapons/AUG/sounds/aug.fire.sound", _single("aug_assets"),
        "a bullpup, 0.79 m long: the muzzle ~0.64 m ahead"),
    # 9x19 from a 260 mm barrel, 600 rpm from the open bolt, one recording. As levelled the loudest band in its first
    # 150 ms is 60-120 Hz, everything over 300 Hz 11-18 dB under it: a designed thud, centred at 435 Hz. Then -20 dB at
    # 0.2 s and -35 at 0.4. It takes the most: the lows from 8 ms, and 1-6 kHz up 7 dB. Voiced, its first 30 ms centre
    # at ~0.95 kHz, still the darkest of the guns (the other 9 mm rips are at 1.9-2.4): a bigger lift only made the
    # lift itself the sound (10 dB got to 1.1 kHz).
    "uzi": Gun(Voicing(
        name="uzi_shot", pitch=1.02, event_pitch="0.97 1.03", takes=_takes(1, 1961, 4), rip_pitch=(0.95, 1.05),
        rpm=600, preview_bursts=(8,), high_pass=70.0, low_split=200.0, low_cut_db=-10.0, low_hold=0.008,
        low_ease=0.02, rip_tail_db=-6.0, rip_tail_hold=0.12, rip_tail_ease=0.1, presence=(1000.0, 6000.0),
        presence_db=7.0, presence_hold=0.03, ground_delay=0.0075, tail_at_400ms=-35.0),
        "Weapons/Uzi/sounds", "Weapons/Uzi/sounds/uzi.fire.sound", _single("uzi_assets"),
        "metal stock extended, 0.65 m long: the muzzle ~0.48 m ahead"),
    # M80 from a 533 mm barrel, 675 rpm, six dry recordings. As levelled: under 150 Hz a designed rumble as loud as the
    # blast 100-250 ms after the onset and -12 dB at 250-500; the whole sound -8 dB at 0.2 s and -22 at 0.4.
    "fal": Gun(Voicing(
        name="fal_shot", pitch=0.98, event_pitch="0.98 1.02", takes=_takes(6, 1971), rip_pitch=(0.97, 1.03),
        rpm=675, preview_bursts=(6,), low_split=140.0, low_cut_db=-6.0, low_hold=0.04, low_ease=0.04,
        rip_tail_db=-12.0, rip_tail_hold=0.1, rip_tail_ease=0.1, presence_db=3.0, presence_hold=0.02,
        ground_delay=0.0066, tail_at_400ms=-31.5),
        "Weapons/FAL/sounds", "Weapons/FAL/sounds/fal.fire.sound", _fal,
        "1.09 m long: the muzzle ~0.87 m ahead"),
    # M1152 from a 99 mm barrel, semi (fired here at 300 rounds a minute), one recording: the pack's near channel.
    # As levelled: the lows at -8 dB 30-100 ms after the onset; -36 dB at 0.4 s.
    "m18": Gun(Voicing(
        name="m18_shot", pitch=1.0, event_pitch="0.97 1.03", takes=_takes(1, 1981, 4), rip_pitch=(0.95, 1.05),
        rpm=300, preview_bursts=(4,), low_split=130.0, low_cut_db=-4.0, low_hold=0.025, low_ease=0.03,
        presence_db=3.0, presence_hold=0.02, ground_delay=0.0067, tail_at_400ms=-33.0),
        "Weapons/M18/sounds", "Weapons/M18/sounds/m18.fire.sound", _single("p320_assets"),
        "at arm's length: the muzzle ~0.7 m ahead, 1.45 m up"),
    # 5.56 from a 488 mm barrel, one recording. As levelled: the lows at -3 dB 30-100 ms after the onset; dark
    # (1.3 kHz, over 800 Hz 6-15 dB down); -41 dB at 0.4 s.
    "famas": Gun(Voicing(
        name="famas_fire", pitch=1.01, event_pitch="0.97 1.03", takes=_takes(1, 1991, 4), rip_pitch=(0.97, 1.03),
        rpm=1000, preview_bursts=(3, 8), low_split=130.0, low_cut_db=-6.0, low_hold=0.03, low_ease=0.035,
        presence_db=4.0, presence_hold=0.025, ground_delay=0.0071, tail_at_400ms=-33.0),
        "Weapons/FAMAS/sounds", "Weapons/FAMAS/sounds/famas.fire.sound", _famas,
        "a bullpup, 0.76 m long: the muzzle ~0.62 m ahead"),
    # M855 from a 292 mm (11.5-inch) barrel, 850 rpm, six dry recordings. As levelled: a designed low ring, under
    # 150 Hz at -11 dB 100-250 ms after the onset (the voiced rifles' -19 to -24), and dark: the first 30 ms centre at
    # 0.67-1.15 kHz (theirs at 1.25-1.85), the lows in the first 150 ms as loud as anything; -36 to -41 dB at 0.4 s. An
    # SBR's blast at the shooter is a sharp crack, much of its powder burning past the muzzle, so it keeps its pitch and
    # gets the lows eased 8 dB and 5 dB of presence: voiced, -23 dB and 1.1-1.55 kHz.
    "mcx": Gun(Voicing(
        name="mcx_shot", pitch=1.0, event_pitch="0.98 1.02", takes=_takes(6, 2001), rip_pitch=(0.97, 1.03),
        rpm=850, preview_bursts=(8,), low_split=130.0, low_cut_db=-8.0, low_hold=0.03, low_ease=0.035,
        presence_db=5.0, presence_hold=0.025, ground_delay=0.0073, tail_at_400ms=-34.0),
        "Weapons/MCX/sounds", "Weapons/MCX/sounds/mcx.fire.sound", _mcx,
        "stock extended, 0.76 m long: the muzzle ~0.54 m ahead"),
    # M855 from a 518 mm barrel, 690 rpm, one recording (MW2019's L86A2: its short barrel makes it the L85A2). As
    # levelled: the lows at -6 dB 30-100 ms after the onset and -18 at 100-250, a little more than the voiced rifles'
    # -19 to -23; its first 30 ms centre at 1.35 kHz, about the M16A4's. So it's eased and lifted as the M16A4's is.
    "l85a2": Gun(Voicing(
        name="l85a2_shot", pitch=1.0, event_pitch="0.97 1.03", takes=_takes(1, 2011, 4), rip_pitch=(0.95, 1.05),
        rpm=690, preview_bursts=(8,), low_split=130.0, low_cut_db=-6.0, low_hold=0.03, low_ease=0.035,
        presence_db=3.0, presence_hold=0.025, ground_delay=0.0071, tail_at_400ms=-33.0),
        "Weapons/L85A2/sounds", "Weapons/L85A2/sounds/l85a2.fire.sound", _single("l85a2_assets"),
        "a bullpup, 0.79 m long: the muzzle ~0.64 m ahead"),
    # M855 from a 279 mm (11-inch) barrel, 850 rpm, Tarkov's two close recordings. As ripped: the lows round 60 Hz as
    # loud as anything in the first 150 ms, and a baked-in outdoor tail only 14-17 dB down at 0.2 s and 15-19 at 0.4 s.
    # So the tail is eased as the FAL's is (harder: from 0.4 s it ran 3-10 dB over the MCX's and the L85A2's), and the
    # lows as the MCX's (the same round from a barrel half an inch shorter).
    "hk416": Gun(Voicing(
        name="hk416_shot", pitch=1.0, event_pitch="0.98 1.02", takes=_takes(2, 2021, 4), rip_pitch=(0.97, 1.03),
        rpm=850, preview_bursts=(8,), low_split=130.0, low_cut_db=-8.0, low_hold=0.03, low_ease=0.035,
        rip_tail_db=-20.0, rip_tail_hold=0.08, rip_tail_ease=0.08, presence_db=2.0, presence_hold=0.025,
        ground_delay=0.0073, tail_at_400ms=-34.0),
        "Weapons/HK416/sounds", "Weapons/HK416/sounds/hk416.fire.sound", _hk416,
        "stock extended, 0.80 m long: the muzzle ~0.56 m ahead"),
    # 7N6 from a 415 mm barrel, 700 rpm, Tarkov's four close recordings, each under its tail. As levelled: the lows at
    # 60-300 Hz as loud as anything in the first 150 ms, as the HK416's were, and the tail still 23 dB under the blast
    # at 0.4 s, 10 dB over the voiced rifles'. The blast's first 150 ms is a little dark (800 Hz-5 kHz 4-10 dB under
    # the lows). So the lows are eased as the HK416's, its tail 14 dB from 80 ms, and the presence lifted 3 dB.
    "ak12": Gun(Voicing(
        name="ak12_shot", pitch=1.0, event_pitch="0.98 1.02", takes=_takes(4, 2041), rip_pitch=(0.98, 1.02),
        rpm=700, preview_bursts=(8,), low_split=130.0, low_cut_db=-8.0, low_hold=0.03, low_ease=0.035,
        rip_tail_db=-14.0, rip_tail_hold=0.08, rip_tail_ease=0.08, presence_db=3.0, presence_hold=0.025,
        ground_delay=0.0069, tail_at_400ms=-33.0),
        "Weapons/AK12/sounds", "Weapons/AK12/sounds/ak12.fire.sound", _ak12,
        "stock extended, 0.945 m long: the muzzle ~0.73 m ahead"),
    # 7.62x39 PS from a 415 mm barrel, 700 rpm: Tarkov's AKM, the same round from the same barrel length, four close
    # recordings each under the AKM's tail. As levelled: the lows round 60 Hz the loudest band in the first 150 ms and
    # the blast's 2-10 kHz 7-8 dB under them, darker than the AK-12's 5.45; the tail already the voiced rifles' (-27 dB
    # 0.2 s after the loudest 100 ms, -33 at 0.4 s). So the lows are eased as the AK-12's, its tail only 6 dB from
    # 100 ms, and the presence lifted 3 dB.
    "ak15": Gun(Voicing(
        name="ak15_shot", pitch=1.0, event_pitch="0.98 1.02", takes=_takes(4, 2051), rip_pitch=(0.98, 1.02),
        rpm=700, preview_bursts=(8,), low_split=130.0, low_cut_db=-8.0, low_hold=0.03, low_ease=0.035,
        rip_tail_db=-6.0, rip_tail_hold=0.1, rip_tail_ease=0.1, presence_db=3.0, presence_hold=0.025,
        ground_delay=0.0069, tail_at_400ms=-33.0),
        "Weapons/AK15/sounds", "Weapons/AK15/sounds/ak15.fire.sound", _ak15,
        "stock extended, 0.945 m long: the muzzle ~0.73 m ahead"),
    # 7N6 from a 415 mm barrel, 650 rpm: Tarkov's AK-74M, the AK-12's round and barrel length, four close recordings
    # each under the AK-74M's tail. As levelled: the lows round 60-120 Hz the loudest band in the first 150 ms and the
    # blast's 800 Hz-10 kHz 8-12 dB under them, darker than the AK-12's recordings of the same round; the tail quieter
    # than the voiced rifles' (-29 dB 0.2 s after the loudest 100 ms, -36 at 0.4 s). So the lows are eased as the
    # AK-12's, its tail only 6 dB from 100 ms, as the AK-15's, and the presence lifted 4 dB, as the AK-105's.
    "ak74m": Gun(Voicing(
        name="ak74m_shot", pitch=1.0, event_pitch="0.98 1.02", takes=_takes(4, 2061), rip_pitch=(0.98, 1.02),
        rpm=650, preview_bursts=(8,), low_split=130.0, low_cut_db=-8.0, low_hold=0.03, low_ease=0.035,
        rip_tail_db=-6.0, rip_tail_hold=0.1, rip_tail_ease=0.1, presence_db=4.0, presence_hold=0.025,
        ground_delay=0.0069, tail_at_400ms=-33.0),
        "Weapons/AK74M/sounds", "Weapons/AK74M/sounds/ak74m.fire.sound", _ak74m,
        "stock unfolded, 0.943 m long: the muzzle ~0.73 m ahead"),
}


def event_pitch(gun: str) -> str:
    return GUNS[gun].voicing.event_pitch


def build(gun: str, out: Path) -> list[Path]:
    """Writes the gun's takes into `out` and returns their WAV paths (its assets script names them in its fire event)."""
    g = GUNS[gun]
    return shot_voicing.build(g.voicing, Path(out), g.ripped)


def write(gun: str) -> None:
    """Rewrites the gun's takes in Assets and its fire event's list and pitch, as the assets script would."""
    from ks74u_assets import asset_path
    g = GUNS[gun]
    paths = build(gun, ASSETS / g.folder)
    event_path = ASSETS / g.event
    event = json.loads(event_path.read_text(encoding="utf-8"))
    event["Pitch"] = g.voicing.event_pitch
    event["Sounds"] = [asset_path(p.with_suffix(".vsnd")) for p in paths]
    with open(event_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(event, indent=2) + "\n")
    print(f"{gun}: {len(paths)} takes -> {g.folder}")


def preview(gun: str, out: str) -> None:
    g = GUNS[gun]
    v = g.voicing
    raw, recordings = g.ripped()
    voiced = shot_voicing.takes(v, raw, recordings)
    for name, x in [(f"ripped {i}", x) for i, x in enumerate(recordings, start=1)] + \
            [(f"take {i}", x) for i, x in enumerate(voiced, start=1)]:
        shot_voicing.describe(name, x)
    rng = np.random.default_rng(1)
    pitches = tuple(float(p) for p in v.event_pitch.split())
    gap = np.zeros((int(0.6 * shot_voicing.SR), 2))
    demo = np.concatenate([recordings[0], gap, voiced[0], gap, shot_voicing.bursts(v, recordings, v.rip_pitch, rng),
                           gap, shot_voicing.bursts(v, voiced, pitches, rng)])
    shot_voicing.write_wav(out, demo * min(0.5, shot_voicing.CEILING / np.abs(demo).max()))
    print(f"preview: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gun", choices=[*GUNS, "all"])
    parser.add_argument("--preview", help="write a before/after demo WAV here instead of the assets (one gun)")
    args = parser.parse_args()
    if args.preview:
        if args.gun == "all":
            sys.exit("--preview takes one gun")
        preview(args.gun, args.preview)
    else:
        for name in (GUNS if args.gun == "all" else [args.gun]):
            write(name)

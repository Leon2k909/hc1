"""
The ported guns' suppressed shots, voiced away from CoD's sound design with shot_voicing.py's steps, as their open shots
were (ported_shots.py, ak105_shot.py, m16_shot.py, kastov762_shot.py): the Kastov 762's (which the RPK fires too), the
PP-19-01 Vityaz's, PP-19 Bizon's, AK-105's, M16A4's, FN P90's, MP7A1's, Steyr AUG's, Uzi's, FN FAL's, FAMAS F1's,
SIG MCX Virtus's, L85A2's, HK416's, AK-12's, AK-15's and AK-74M's.
The M18 and the Vepr-12 have none, and the Kastov-74u's are left alone.

What the rips get wrong (2026-09-30, as levelled into Assets, counting the SMGs' suppressed events' volume of 0.5):
- How much the suppressor takes off. Against each gun's voiced open shot, by loudness (K-weighted, loudest 100 ms), the
  Kastov 762's was 1.4 dB quieter, the AK-105's 2.7, the Vityaz's 5.7, the Bizon's 6.3, the Uzi's 5.1, the FAL's 5.1,
  the AUG's 6.9, the M16A4's 8.1, the FAMAS's 8.9, the MP7's 9.4 and the P90's 10.6. The Uzi's WAV was louder than its
  open shot's. They were levelled to each other, not to their guns.
- Two sound designs. MWII's (the Kastov, AK-105, Vityaz, Bizon, MP7) are a bright "pew", their first 30 ms centred at
  3.6-6.9 kHz, and a few are clipped to full scale. MW2019's (the P90, AUG, FAL, FAMAS, M16A4's MWII M4 recording) carry
  a designed thump as loud as the rest of the shot: their lows under 150 Hz are within 3 dB of the whole first 100 ms.
- Their tails. The FAMAS's is bone dry (-56 dB 0.2 s after its loudest 100 ms), the AK-105's and FAL's designed
  reverbs are still -26 to -29 dB there.

What a suppressor really does at the shooter's ear: it takes the muzzle blast down by about 25-30 dB (at the muzzle, by
MIL-STD-1474's 1 m left of it), and less at the ear, since the action's noise and, on gas guns, the gas blown back
through it are left: roughly 20-25 dB on rifles and SMGs alike. What's left is the action cycling, a thud from the can
and the echoes, still shaped by the same surroundings. The game's mix squeezes the real gaps between loud things about
0.43 times (foley_voicing.py: 74 dB between a shot and a footstep become 32), so a suppressed shot here sits
SUPPRESSION_DB (10) under its gun's open shot, counting its event's volume.

Each suppressed recording is voiced with its gun's open-shot Voicing, but:
- no pitch change and no presence lift: the blast's crack is what the can takes off;
- a 40 Hz high-pass, and the lows under 130 Hz eased 6 dB after the first 25 ms, which takes MW2019's thumps down;
- the same ground reflection and the same echoes, at the same level under the shot as the open shot's (tail_at_400ms),
  and the open voicing's easing of the rip's own tail (the FAL's, AUG's, Uzi's, M16A4's and Kastov's);
- its loudest 100 ms at the target, through the same soft clipper and limiter.
Each file keeps its name, and the events are unchanged.

The rips are kept in Backups/suppressed_shots_rip/<gun>/, and every run voices from them, backing up any file that has
no copy there yet (one its assets script has just written), so a rerun never voices a file twice. After a re-rip
changes a gun's files, delete its backups first. Each gun's assets script (kastov_sounds.py for the Kastov) calls
voice() after writing its suppressed shots.

  python Tools/suppressed_shots.py <gun>|all            voice the gun's suppressed shots in Assets
  python Tools/suppressed_shots.py <gun>|all --dry-run  measure the voiced shots without writing them
"""
import argparse
import dataclasses
import json
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import shot_voicing

PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT / "Assets"
BACKUP = PROJECT / "Backups" / "suppressed_shots_rip"
SUPPRESSION_DB = 10.0


@dataclass(frozen=True)
class Suppressed:
    folder: str  # the sounds folder, under Assets
    files: str  # the suppressed shots, a glob in the folder
    event: str  # the suppressed event, whose Volume counts
    shot: str  # the voiced open shot's takes, a glob in the folder
    voicing: str  # the open shot's voicing: a ported_shots gun, or a module with VOICING

    def open_voicing(self):
        if self.voicing.endswith("_shot"):
            return __import__(self.voicing).VOICING
        import ported_shots
        return ported_shots.GUNS[self.voicing].voicing

    def suppressed_voicing(self):
        return dataclasses.replace(self.open_voicing(), pitch=1.0, presence_db=0.0, high_pass=40.0, low_split=130.0,
                                   low_cut_db=-6.0, low_hold=0.025, low_ease=0.035)


def smg(gun):
    return Suppressed(f"Weapons/{gun.title() if gun != 'mp7' else 'MP7'}/sounds", f"{gun}_suppressed_shot_0*.wav",
                      f"{gun}.fire_suppressed.sound", f"{gun}_shot_0[1-9].wav", gun)


GUNS = {
    "kastov762": Suppressed("sounds/weapons/kastov", "kastov_shot_sup_0*.wav", "kastov_shot_sup.sound",
                            "kastov_shot_0[1-9].wav", "kastov762_shot"),
    "vityaz": smg("vityaz"),
    "bizon": smg("bizon"),
    "ak105": Suppressed("Weapons/AK105/sounds", "ak105_suppressed_shot_0*.wav", "ak105.fire_suppressed.sound",
                        "ak105_shot_0[1-9].wav", "ak105_shot"),
    "m16": Suppressed("Weapons/M16/sounds", "m16_suppressed_shot_0*.wav", "m16.fire_suppressed.sound",
                      "m16_shot_0[1-9].wav", "m16_shot"),
    "p90": Suppressed("Weapons/P90/sounds", "p90_suppressed_shot_0*.wav", "p90.fire_suppressed.sound",
                      "p90_shot_0[1-9].wav", "p90"),
    "mp7": smg("mp7"),
    "aug": Suppressed("Weapons/AUG/sounds", "aug_suppressed_shot_0*.wav", "aug.fire_suppressed.sound",
                      "aug_shot_0[1-9].wav", "aug"),
    "uzi": smg("uzi"),
    "fal": Suppressed("Weapons/FAL/sounds", "fal_suppressed_shot_0*.wav", "fal.fire_suppressed.sound",
                      "fal_shot_0[1-9].wav", "fal"),
    "famas": Suppressed("Weapons/FAMAS/sounds", "famas_fire_suppressed_0*.wav", "famas.fire_suppressed.sound",
                        "famas_fire_0[1-9].wav", "famas"),
    "mcx": Suppressed("Weapons/MCX/sounds", "mcx_suppressed_shot_0*.wav", "mcx.fire_suppressed.sound",
                      "mcx_shot_0[1-9].wav", "mcx"),
    "l85a2": Suppressed("Weapons/L85A2/sounds", "l85a2_suppressed_shot_0*.wav", "l85a2.fire_suppressed.sound",
                        "l85a2_shot_0[1-9].wav", "l85a2"),
    "hk416": Suppressed("Weapons/HK416/sounds", "hk416_suppressed_shot_0*.wav", "hk416.fire_suppressed.sound",
                        "hk416_shot_0[1-9].wav", "hk416"),
    "ak12": Suppressed("Weapons/AK12/sounds", "ak12_suppressed_shot_0*.wav", "ak12.fire_suppressed.sound",
                       "ak12_shot_0[1-9].wav", "ak12"),
    "ak15": Suppressed("Weapons/AK15/sounds", "ak15_suppressed_shot_0*.wav", "ak15.fire_suppressed.sound",
                       "ak15_shot_0[1-9].wav", "ak15"),
    "ak74m": Suppressed("Weapons/AK74M/sounds", "ak74m_suppressed_shot_0*.wav", "ak74m.fire_suppressed.sound",
                        "ak74m_shot_0[1-9].wav", "ak74m"),
}


def rips(name):
    """The gun's suppressed shots as ripped and levelled, {Assets path: stereo float}: from its backups, backing up
    any file (and the event) that has none yet."""
    gun = GUNS[name]
    folder = ASSETS / gun.folder
    backup = BACKUP / name
    backup.mkdir(parents=True, exist_ok=True)
    for path in [*folder.glob(gun.files), folder / gun.event]:
        if not (backup / path.name).exists():
            shutil.copy2(path, backup / path.name)
    ripped = {path: shot_voicing.read_wav(str(backup / path.name)) for path in sorted(folder.glob(gun.files))}
    assert ripped, f"no suppressed shots for {name}"
    return ripped


def event_volume_db(gun):
    event = json.loads((ASSETS / gun.folder / gun.event).read_text(encoding="utf-8-sig"))
    return 20 * np.log10(float(str(event.get("Volume", "1")).split(",")[0]))


def target(name):
    """The suppressed shots' loudest 100 ms in their WAVs: SUPPRESSION_DB under the open shot, counting the event."""
    gun = GUNS[name]
    shots = sorted((ASSETS / gun.folder).glob(gun.shot))
    assert shots, f"no open shot takes: {gun.folder}/{gun.shot}"
    open_shot = float(np.mean([shot_voicing.loudest(shot_voicing.read_wav(str(p)))[0] for p in shots]))
    return open_shot, open_shot - SUPPRESSION_DB - event_volume_db(gun)


def voice(name, write=True):
    gun = GUNS[name]
    v = gun.suppressed_voicing()
    open_shot, level = target(name)
    ripped = rips(name)
    before = np.mean([shot_voicing.loudest(x)[0] for x in ripped.values()])
    for seed, (path, x) in enumerate(ripped.items(), start=1):
        y = shot_voicing.finish(v, *shot_voicing.voice(v, x, seed), level)
        if write:
            shot_voicing.write_wav(str(path), y)
        shot_voicing.describe(f"  {path.name}", y)
    print(f"{name}: {len(ripped)} files at {level:.1f} dB (were {before:.1f}), with the event's "
          f"{event_volume_db(gun):+.1f} dB {SUPPRESSION_DB:.0f} dB under the open shot's {open_shot:.1f}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gun", choices=[*GUNS, "all"])
    parser.add_argument("--dry-run", action="store_true", help="measure without writing")
    args = parser.parse_args()
    for gun in GUNS if args.gun == "all" else [args.gun]:
        voice(gun, write=not args.dry_run)

"""
The ported guns' reload foley, voiced away from CoD's sound design with foley_voicing.py's steps, as rpk_foley.py does
for the RPK: the Kastov 762's (the RPK's parts use their own copies), the PP-19-01 Vityaz's, PP-19 Bizon's, AK-105's,
Vepr-12's, M16A4's, FN P90's, MP7A1's, Steyr AUG's, Uzi's, FN FAL's, SIG M18's, FAMAS F1's and SIG MCX Virtus's. The
Kastov-74u's are left alone (another session's hand-tuned sounds). Each gun's shot was voiced first (ported_shots.py,
ak105_shot.py, m16_shot.py, kastov762_shot.py), and its voiced takes are what the foley are levelled against.

What the rips get wrong is what foley_voicing's docstring says, on every gun:
- the moves (the gun raised, lowered, tilted or shouldered, an arm or a hand moving, a magazine grabbed from a pouch)
  carry designed subs, and the shoulder returns boom at 45-90 Hz: the FAMAS F1's raise, drop and shoulder returns have
  half their energy under 90 Hz;
- the loudest clacks are limited to full scale, some for tens of ms (the FAMAS's bolt going home is 8.8 dB from its
  peak to its loudest 100 ms);
- the loudest file of every set but the Kastov's (1 dB under) is louder than the gun's voiced shot, by up to 4.4 dB
  (the AK-105's bolt pull, -2.4 dB against -6.8).

The steps are foley_voicing's with its defaults: a 90 Hz high-pass on every file, the moves' lows under 250 Hz eased
6 dB, and one gain for the whole set so its loudest 100 ms sits 16 dB under the gun's shot (the mean of its takes).
The sets came down 15-20.4 dB, and their loudest 100 ms at 40-90 Hz went from 8-27 dB under the shot to 38-56 dB
(2026-09-30).
MOVES says which files are moves, by name. The Kastov 762's and the FAMAS F1's files are only numbered, so theirs are
listed by number, from the addon's own names where it has them (the Kastov's drum and xmag sounds, in its lua) and
otherwise from where the file falls in its clip and what it holds: the first events of a clip are the gun turning, and
the last its return to the shoulder, whose lows match the named `shoulder` files within 0.5 dB.

The rips are kept in Backups/ported_foley_rip/<gun>/, and every run voices from them, backing up any file that has no
copy there yet (one its assets script has just converted), so a rerun never voices a file twice. After a re-rip
changes a gun's files, delete its backups first. Each gun's assets script (kastov_sounds.py and ak47_gunsmith.py for
the Kastov) calls voice() after writing its foley.

  python Tools/ported_foley.py <gun>|all            voice the gun's foley in Assets
  python Tools/ported_foley.py <gun>|all --list     list its foley and which are moves
  python Tools/ported_foley.py <gun>|all --preview out.wav
                                                    the rip's shot and two reloads, then the voiced ones
"""
import argparse
import json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import foley_voicing
import shot_voicing

PROJECT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT / "Assets"
BACKUP = PROJECT / "Backups" / "ported_foley_rip"

# Files in a gun's sounds folder that aren't foley.
NOT_FOLEY = r"_shot_|suppress|_fire_|_sup_"

# The moves, by the rips' own names. `arm` is an arm moving, except the P90's arm_maghit (the magazine slapped in);
# `drop` is the gun lowered, except the FAL's dropmag (the magazine falling out).
MOVES = (r"raise|drop(?!mag)|rattle|mvt|mvmnt|shoulder|_end|arm(?!_maghit)|elbow|lift|lower|shake|tilt|rotate|regrip"
         r"|start|cloth|swing|grab")

# The Kastov 762's numbered files. Its lua names the drum's and xmag's: drum_reload 01/03/05 are mvt1-3, 06 a grab and
# 07 the shoulder; drum_reload_empty 01 and 08 mvt1, 06 the grab and 09 the shoulder; xmag_reload 01 and 04 mvt1-2, 03
# grabmag and 07 the shoulder; xmag_reload_empty 01 and 03 mvt1-2 and 06 the shoulder. The plain reload's have no names:
# reload 01 and reload_empty 01 open their clips (the gun turning), reload_empty 03 and 06 are quiet hand moves (38 and
# 23 dB under full scale), and reload 05 and reload_empty 07 close them on the shoulder.
KASTOV_MOVES = (r"raise|_reload_0[15]$|_reload_empty_0[1367]$|drum_reload_0[13567]_|drum_reload_empty_0[1689]_"
                r"|xmag_reload_0[1347]_|xmag_reload_empty_0[136]_")

# The FAMAS F1's numbered files: each clip's first event is the gun turning, and reload 05 and reload_empty 05 its
# return to the shoulder (-4 and -3 dB under 90 Hz against the whole file, like its raise and drop).
FAMAS_MOVES = r"drop|raise|_reload_0[15]_|_reload_empty_0[15]_|_xmag_01_"


@dataclass(frozen=True)
class Gun:
    folder: str  # the sounds folder, under Assets
    prefix: str  # the gun's files start with this and an underscore
    shot: str  # the voiced shot's takes, a glob in the folder
    moves: str = MOVES
    manifest: str = ""  # the reloads' timed events, for --preview (under Assets)
    only: str = ""  # a regex the foley files' names must also match

    def files(self):
        folder = ASSETS / self.folder
        return sorted(p for p in folder.glob(f"{self.prefix}_*.wav")
                      if not re.search(NOT_FOLEY, p.name) and re.search(self.only, p.stem))

    def shots(self):
        shots = sorted((ASSETS / self.folder).glob(self.shot))
        assert shots, f"no shot takes: {self.folder}/{self.shot}"
        return shots

    @property
    def foley(self):
        return foley_voicing.Foley(moves=self.moves)


GUNS = {
    "kastov762": Gun("sounds/weapons/kastov", "kastov", "kastov_shot_0[1-9].wav", KASTOV_MOVES,
                     "Weapons/Kastov/kastov_attachment_assets.json", r"^kastov_(reload|raise|drum|xmag)"),
    "vityaz": Gun("Weapons/Vityaz/sounds", "vityaz", "vityaz_shot_0[1-9].wav",
                  manifest="Weapons/Vityaz/vityaz_assets.json"),
    "bizon": Gun("Weapons/Bizon/sounds", "bizon", "bizon_shot_0[1-9].wav", manifest="Weapons/Bizon/bizon_assets.json"),
    "ak105": Gun("Weapons/AK105/sounds", "ak105", "ak105_shot_0[1-9].wav", manifest="Weapons/AK105/ak105_assets.json"),
    "vepr12": Gun("Weapons/Vepr12/sounds", "vepr12", "vepr12_shot_0[1-9].wav",
                  manifest="Weapons/Vepr12/vepr12_assets.json"),
    "m16": Gun("Weapons/M16/sounds", "m16", "m16_shot_0[1-9].wav", manifest="Weapons/M16/m16_assets.json"),
    "p90": Gun("Weapons/P90/sounds", "p90", "p90_shot_0[1-9].wav", manifest="Weapons/P90/p90_assets.json"),
    "mp7": Gun("Weapons/MP7/sounds", "mp7", "mp7_shot_0[1-9].wav", manifest="Weapons/MP7/mp7_assets.json"),
    "aug": Gun("Weapons/AUG/sounds", "aug", "aug_shot_0[1-9].wav", manifest="Weapons/AUG/aug_assets.json"),
    "uzi": Gun("Weapons/Uzi/sounds", "uzi", "uzi_shot_0[1-9].wav", manifest="Weapons/Uzi/uzi_assets.json"),
    "fal": Gun("Weapons/FAL/sounds", "fal", "fal_shot_0[1-9].wav", manifest="Weapons/FAL/fal_assets.json"),
    "m18": Gun("Weapons/M18/sounds", "m18", "m18_shot_0[1-9].wav", manifest="Weapons/M18/m18_assets.json"),
    "famas": Gun("Weapons/FAMAS/sounds", "famas", "famas_fire_0[1-9].wav", FAMAS_MOVES,
                 "Weapons/FAMAS/famas_assets.json"),
    "mcx": Gun("Weapons/MCX/sounds", "mcx", "mcx_shot_0[1-9].wav", manifest="Weapons/MCX/mcx_assets.json"),
}

# Where each gun's ripped shot was backed up when it was voiced, for --preview.
RIPPED_SHOTS = {"kastov762": "kastov762_shot_rip", "ak105": "ak105_shot_rip", "m16": "m16_shot_rip"}


def rips(name):
    """The gun's foley as ripped, {Assets path: float}: from its backups, backing up any file that has none yet."""
    backup = BACKUP / name
    backup.mkdir(parents=True, exist_ok=True)
    ripped = {}
    for path in GUNS[name].files():
        saved = backup / path.name
        if not saved.exists():
            shutil.copy2(path, saved)
        ripped[path] = foley_voicing.read(saved)
    assert ripped, f"no foley for {name}"
    return ripped


def voice(name):
    """Voices the gun's foley in Assets from its rips. Returns the gain the set was given (dB)."""
    gun = GUNS[name]
    ripped = rips(name)
    shot = foley_voicing.shot_loudness(gun.shots())
    voiced, gain = foley_voicing.voice(gun.foley, {path.stem: x for path, x in ripped.items()}, shot)
    for path in ripped:
        foley_voicing.write(path, voiced[path.stem])
    loudest = max(ripped, key=lambda path: foley_voicing.loudness(ripped[path]))
    moves = sum(bool(re.search(gun.moves, path.stem)) for path in ripped)
    print(f"{name}: {len(ripped)} files ({moves} moves), {gain:+.1f} dB. The loudest, {loudest.name}: "
          f"{foley_voicing.loudness(ripped[loudest]):.1f} -> {foley_voicing.loudness(voiced[loudest.stem]):.1f} dB, "
          f"the shot {shot:.1f} dB")
    return gain


def listing(name):
    gun = GUNS[name]
    for path in gun.files():
        print(f"  {'move' if re.search(gun.moves, path.stem) else 'part'}  {path.name}")


def stereo(x):
    return x if x.ndim == 2 else np.stack([x, x], axis=1)


def reloads(gun, count=2):
    """The first `count` reload clips of the gun's manifest, each as [(seconds, WAV stem)]."""
    manifest = json.loads((ASSETS / gun.manifest).read_text(encoding="utf-8"))["reloads"]
    clips = sorted(manifest, key=lambda clip: (clip not in ("reload", "reload_empty"), clip))[:count]
    shown = []
    for clip in clips:
        events = []
        for seconds, event in manifest[clip].items():
            sounds = json.loads((ASSETS / event).read_text(encoding="utf-8"))["Sounds"]
            events.append((float(seconds), Path(sounds[0]).stem))
        shown.append(sorted(events))
    return shown


def sequence(shot, clips, files):
    """The shot, then each clip's events at their times, with gaps between."""
    gap = np.zeros((int(0.8 * shot_voicing.SR), 2))
    parts = [stereo(shot), gap]
    for events in clips:
        length = max(seconds * shot_voicing.SR + len(files[stem]) for seconds, stem in events if stem in files)
        track = np.zeros((int(length), 2))
        for seconds, stem in events:
            if stem in files:
                at = int(seconds * shot_voicing.SR)
                track[at:at + len(files[stem])] += stereo(files[stem])
        parts += [track, gap]
    return np.concatenate(parts)


def preview(name, out):
    gun = GUNS[name]
    ripped = {path.stem: x for path, x in rips(name).items()}
    voiced = {path.stem: foley_voicing.read(path) for path in gun.files()}
    old_shot = foley_voicing.read(sorted((PROJECT / "Backups" / RIPPED_SHOTS.get(name, f"ported_shots_rip/{name}"))
                                         .glob("*.wav"))[0])
    new_shot = foley_voicing.read(gun.shots()[0])
    clips = reloads(gun)
    demo = np.concatenate([sequence(old_shot, clips, ripped), np.zeros((int(1.5 * shot_voicing.SR), 2)),
                           sequence(new_shot, clips, voiced)])
    foley_voicing.write(out, demo * min(1.0, shot_voicing.CEILING / np.abs(demo).max()))
    print(f"{name} preview: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("gun", choices=[*GUNS, "all"])
    parser.add_argument("--list", action="store_true", help="list the foley and which are moves")
    parser.add_argument("--preview", help="write the rip's shot and two reloads, then the voiced ones, here")
    args = parser.parse_args()
    for gun in GUNS if args.gun == "all" else [args.gun]:
        if args.list:
            print(gun)
            listing(gun)
        elif args.preview:
            out = Path(args.preview)
            preview(gun, out if args.gun != "all" else out.with_name(f"{out.stem}_{gun}{out.suffix}"))
        else:
            voice(gun)

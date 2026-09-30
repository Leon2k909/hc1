"""
Voicing a ripped Call of Duty reload's foley away from CoD's sound design, towards what the shooter hears from the real
gun's parts. The guns' scripts (rpk_foley.py for the RPK, ported_foley.py for the other ported guns) hold their Foley,
what their rips get wrong and where the rips come from; this holds the steps they share. shot_voicing.py does the same
for shots.

CoD's foley are close recordings of real parts, mastered for a game:
- the hand and gear moves carry a designed sub thump (45-90 Hz), and the gun coming back to the shoulder booms;
- each file is limited to full scale, its loudest clacks clipped flat for tens of ms. The codec has smeared the
  plateaus, as on the M16A4's shot, so they stay;
- the game plays them as loud as the shot: a magazine going in is louder, by loudness, than the rifle firing.

voice() takes one gun's own foley (as its assets script converted it: 44.1 kHz, mono for most guns, stereo for the
Kastov 762's) and:
1. High-passes every file at high_pass (causal, 4th order, as a microphone's roll-off): small steel parts at the ear
   give little under 100 Hz, so the designed subs go and the parts' own knocks stay.
2. Eases the moves' lows (the files `moves` matches: the gun raised, lowered or shouldered, the hands or gear moving)
   move_low_db under move_split: a stock against a shoulder, or cloth, is a dull knock, not a boom.
3. Levels the whole set with one gain, so the rip's balance between the files stays and its loudest 100 ms
   (K-weighted, as shot_voicing measures shots, a mono file counted in both ears) sits under_shot_db under the gun's
   shot.

The level. At the shooter's ear a rifle shot is about 137 dB(A) over its loudest 100 ms (~160 dB peak), the loudest
reload clacks (the magazine seating, the bolt carrier slamming home, ~0.4 m from the ear) about 100, and a walking
footstep about 63. They're rough figures, not measurements. No game mix keeps the 74 dB between the shot and a footstep,
and this one has 32 (world_sounds.py's walk on concrete, event volume included, against the rifles' shots). Squeezed
the same way, the clack sits 16 dB under the shot, and about as far over the footsteps.
"""
import re
import warnings
import wave
from dataclasses import dataclass

import numpy as np
from scipy import signal
from scipy.io import wavfile

import shot_voicing

SR = shot_voicing.SR


@dataclass(frozen=True)
class Foley:
    high_pass: float = 90.0
    # A regex on the file's name: the files that are moves rather than parts meeting.
    moves: str = r"raise|drop|rattle|mvt|shoulder|_end"
    move_split: float = 250.0
    move_low_db: float = -6.0
    under_shot_db: float = 16.0


def read_mono(path):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", wavfile.WavFileWarning)
        sr, x = wavfile.read(str(path))
    assert sr == SR, (path, sr)
    x = x.astype(np.float64) / 32768.0
    return x.mean(axis=1) if x.ndim == 2 else x


def read(path):
    """A WAV as float, mono (1-D) or stereo (samples x 2) as it was written."""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", wavfile.WavFileWarning)
        sr, x = wavfile.read(str(path))
    assert sr == SR, (path, sr)
    return x.astype(np.float64) / 32768.0


def write(path, x):
    """A mono or stereo float signal as 16-bit PCM."""
    pcm = np.round(np.clip(x, -1.0, 32767 / 32768) * 32768).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1 if x.ndim == 1 else x.shape[1])
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def write_mono(path, x):
    pcm = np.round(np.clip(x, -1.0, 32767 / 32768) * 32768).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())


def loudness(x):
    """The loudest 100 ms (K-weighted), a mono file played in both ears; shorter files padded with silence."""
    stereo = x if x.ndim == 2 else np.stack([x, x], axis=1)
    if len(stereo) < int(0.1 * SR):
        stereo = np.pad(stereo, ((0, int(0.1 * SR) - len(stereo)), (0, 0)))
    return shot_voicing.loudest(stereo)[0]


def shape(f, name, x):
    """Steps 1 and 2 on one file (mono or stereo)."""
    x = signal.sosfilt(shot_voicing.sos(4, f.high_pass, "highpass"), x, axis=0)
    if re.search(f.moves, name):
        low = signal.sosfiltfilt(shot_voicing.sos(2, f.move_split, "lowpass"), x, axis=0)
        x = x + (10 ** (f.move_low_db / 20) - 1) * low
    return x


def voice(f, recordings, shot_loudness):
    """The set voiced: recordings is {name: float, mono or stereo}, shot_loudness the gun's shot's loudest 100 ms.
    Returns the voiced set and the gain (dB) step 3 gave it."""
    shaped = {name: shape(f, name, x) for name, x in recordings.items()}
    gain = shot_loudness - f.under_shot_db - max(loudness(x) for x in shaped.values())
    voiced = {name: x * 10 ** (gain / 20) for name, x in shaped.items()}
    top = max(np.abs(x).max() for x in voiced.values())
    assert top <= shot_voicing.CEILING, f"the loudest file peaks at {20 * np.log10(top):.1f} dBFS"
    return voiced, gain


def shot_loudness(paths):
    """The mean loudest 100 ms of a shot's takes."""
    return float(np.mean([shot_voicing.loudest(shot_voicing.read_wav(str(p)))[0] for p in paths]))


def voice_files(f, paths, shot):
    """Voices the WAVs at `paths` (the rip, as converted) in place, against the shot's takes at `shot`. Each file
    keeps its channels."""
    recordings = {p.stem: read(p) for p in paths}
    before = {name: loudness(x) for name, x in recordings.items()}
    voiced, gain = voice(f, recordings, shot_loudness(shot))
    for p in paths:
        write(p, voiced[p.stem])
        print(f"{p.name}: loudest 100 ms {before[p.stem]:6.1f} -> {loudness(voiced[p.stem]):6.1f} dB")
    print(f"{len(paths)} files, {gain:+.1f} dB")

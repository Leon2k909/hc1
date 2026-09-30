"""
The RPK's reload foley, voiced away from Call of Duty's sound design towards what the gunner hears from the real parts.

    python Tools/rpk_foley.py --preview <wav>

rpk_assets.py voices the RPK's own foley with voice() here as it converts it. --preview writes a demo instead of the
assets: a shot and the drum's reload, then a shot and its empty reload, first as ripped (the Kastov 762's shot as it
was) and then voiced, each sound at the viewmodel QC's frame. The ripped foley as it was is in Backups/rpk_foley_rip/.
The steps are foley_voicing.py's.

As ripped (MWII's RPK foley, and the AK's for the 30-round magazine), measured on the files:
- the drum going in and the bolt carrier being charged play louder than the shot: their loudest 100 ms is -1.2 and
  -1.6 dB, the shot's -4.7. The 30-round magazine's click is -7.6;
- the drum's seating is clipped flat for 50 ms at a time, 351 samples at full scale;
- the draw (raise_rattle) and the gun coming back up after the reload (reload_end) boom at 45-90 Hz, within 3 dB of
  their loudest band, and the empty reload's magazine bump has a sub thump within 6 dB of it.
Its voicing, by foley_voicing's steps: a high-pass at 90 Hz (the booms fall 17-20 dB, the bump's 10), the moves' lows
under 250 Hz eased 6 dB, and one gain for the set (-19.5 dB), so the drum seating is 16 dB under the shot and the
cloth and hands keep their place under it.
"""
import argparse
import tempfile
from pathlib import Path

import numpy as np

import foley_voicing
import shot_voicing
from foley_voicing import Foley

FOLEY = Foley()
SHOT = [Path(__file__).resolve().parent.parent / "Assets" / "sounds" / "weapons" / "kastov" / f"kastov_shot_{index:02d}.wav"
        for index in (1, 2, 3, 4)]


def voice(paths):
    """Voices the RPK's own foley WAVs (as rpk_assets converted them) in place."""
    foley_voicing.voice_files(FOLEY, paths, SHOT)


def sequence(shot, clips, wavs):
    """A shot, then each clip's foley at its times, 0.8 s apart."""
    parts = []
    for clip in clips:
        length = max(float(t) + len(wavs[name]) / shot_voicing.SR for t, name in clip.items())
        track = np.zeros(int(length * shot_voicing.SR))
        for t, name in clip.items():
            at = int(float(t) * shot_voicing.SR)
            track[at:at + len(wavs[name])] += wavs[name]
        gap = np.zeros(int(0.8 * shot_voicing.SR))
        parts += [shot.mean(axis=1), gap, track, gap]
    return np.concatenate(parts)


def preview(out):
    import kastov762_shot
    from rpk_assets import convert_own_foley, reload_clips
    clips = reload_clips()
    with tempfile.TemporaryDirectory() as temp:
        paths = convert_own_foley(Path(temp))
        ripped = {name: foley_voicing.read_mono(path) for name, path in paths.items()}
    voiced, gain = foley_voicing.voice(FOLEY, ripped, foley_voicing.shot_loudness(SHOT))
    for name in ripped:
        print(f"{name}: {foley_voicing.loudness(ripped[name]):6.1f} -> {foley_voicing.loudness(voiced[name]):6.1f} dB")
    print(f"gain {gain:+.1f} dB")
    shown = [clips["reload"], clips["reload_empty"]]
    old_shot = kastov762_shot.ripped()[1][0]
    new_shot = shot_voicing.read_wav(str(SHOT[0]))
    demo = np.concatenate([sequence(old_shot, shown, ripped), np.zeros(int(1.5 * shot_voicing.SR)),
                           sequence(new_shot, shown, voiced)])
    foley_voicing.write_mono(out, demo * min(1.0, shot_voicing.CEILING / np.abs(demo).max()))
    print(f"preview: {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", required=True, help="write a before/after demo WAV here")
    preview(parser.parse_args().preview)

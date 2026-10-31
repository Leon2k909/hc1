"""Run one of the smoke grenade v2's scripts with its names changed, rather than rewrite the whole pipeline.

The old incendiary and smoke grenades are the same mesh family, to the thousandth of an inch, so the same build fits. It reads the
frozen snapshot in base/, taken on 2026-10-30, because the live scripts were being edited by their owner and a moving base would change
this model without anyone asking. Each edit must find its text, or this stops: a silent miss would quietly build a smoke grenade.
"""
import os
import re
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SMOKE = os.path.join(HERE, "base")

FOLDER = "Weapons/Throwable/Molotov_Cocktail/incendiary_grenade_v2"


def run(script, edits, script_path, patterns=()):
    """Exec script from the smoke grenade's folder, after edits (plain text) and patterns (regex, spanning lines)."""
    source = open(os.path.join(SMOKE, script), encoding="utf-8").read()
    for old, new in edits:
        if old not in source:
            raise SystemExit(f"{script}: can't find {old!r}. The smoke grenade's script has changed: check this edit.")
        source = source.replace(old, new)
    for pattern, new in patterns:
        source, count = re.subn(pattern, lambda _: new, source, flags=re.S)
        if count != 1:
            raise SystemExit(f"{script}: pattern {pattern!r} matched {count} times.")
    exec(compile(source, script, "exec"), {"__name__": "__main__", "__file__": script_path})

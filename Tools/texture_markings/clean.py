"""Remove the rips' markings from their textures (see markings.py for the spec format).

usage:
  python clean.py <spec.json> [--dry] [--only <vmat stem>] [--force]
      Clean the spec's materials, writing before/after previews to out/<vmat stem>/fix_*.png. --dry writes only the
      previews. A material that's already clean, or changed since, is skipped unless --force.
  python clean.py --all
      Clean every material in specs/ whose maps are the rip's again (a converter was re-run without its hook).
  python clean.py --check
      List the materials in specs/ whose maps aren't as cleaned. Exits 1 if there are any.
"""
from __future__ import annotations

import sys
from pathlib import Path

import markings as M
import texlib as T


def clean_spec(spec: Path, dry: bool, only: str | None, force: bool) -> None:
    for entry in T.read_json(spec):
        if only and Path(entry["vmat"]).stem != only:
            continue
        if not dry and not force:
            states = set(M.map_states(entry["vmat"]).values())
            if states == {"clean"}:
                print(f"{entry['vmat']}: already clean (restore.py it to clean it again)")
                continue
            if "changed" in states:
                print(f"{entry['vmat']}: changed since it was cleaned; look at it, then use --force")
                continue
        M.process(entry, dry)


def clean_all() -> None:
    manifest = M.read_manifest()
    todo, changed, clean = [], [], 0
    # Every state first: a map two materials share is only the rip's until the first of them is cleaned.
    for entry in M.entries().values():
        states = set(M.map_states(entry["vmat"], manifest).values())
        if states == {"clean"}:
            clean += 1
        elif "changed" in states:
            changed.append(entry["vmat"])
        else:
            todo.append(entry)
    for entry in todo:
        M.process(entry, dry=False, previews=False, verbose=False)
    for vmat in changed:
        print(f"{vmat}: changed since it was cleaned; look at it, then clean.py its spec with --force")
    print(f"{len(todo)} cleaned, {clean} already clean, {len(changed)} changed")


def check() -> int:
    manifest = M.read_manifest()
    bad = 0
    for entry in M.entries().values():
        states = M.map_states(entry["vmat"], manifest)
        wrong = {path: state for path, state in states.items() if state != "clean"}
        if wrong:
            bad += 1
            print(entry["vmat"])
            for path, state in wrong.items():
                print(f"  {state:10s} {path}")
    print(f"{bad} of {len(M.entries())} materials not as cleaned"
          + ("" if not bad else ' ("rip": run clean.py --all; "changed": look at it)'))
    return 1 if bad else 0


def main() -> None:
    args = sys.argv[1:]
    if "--check" in args:
        sys.exit(check())
    if "--all" in args:
        clean_all()
        return
    only = args[args.index("--only") + 1] if "--only" in args else None
    clean_spec(Path(args[0]), "--dry" in args, only, "--force" in args)


if __name__ == "__main__":
    main()

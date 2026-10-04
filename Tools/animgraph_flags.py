"""Bool anim parameters as two-option enums, while s&box can't set a bool parameter true.

s&box 26.10.02 (engine commit #5893) builds a true bool parameter from the constant
`BitConverter.Int32BitsToSingle( 1 )`, a denormal float. The JIT folds it through a double, and on the engine's
threads, which treat denormals as zero, it comes out 0. So every `SkinnedModelRenderer.Set( name, true )` reaches the
graph as false: no reloads, no fire kick, no deploy, no hand IK. `GetBool` builds its result the same way when the
parameter isn't a bool. Facepunch fixed it in sbox-public #6000 (2026-10-03), which hadn't shipped when this was
written.

An int gets through, as long as the JIT can't see it as a constant. So each bool parameter here becomes an enum with
the options "false" and "true", in that order, so a bool selector's two children stay where they were:

- the parameter: `CEnumAnimParameter`, its default 0 or 1, auto-reset kept;
- its conditions compare it with 0 and 1 (`m_nType` 2, an enum);
- its selectors go by the enum (`SelectionSource_Enum`).

The game sets and reads them as ints (`AnimBools.SetBool` / `GetFlag`), which works on a bool parameter too.

    python Tools/animgraph_flags.py             convert every graph under Assets
    python Tools/animgraph_flags.py --revert    turn them back into bools, once s&box has #6000
    python Tools/animgraph_flags.py --check     report what would change, writing nothing
    python Tools/animgraph_flags.py FILE ...    only those graphs

It's idempotent. A bool referenced anywhere but its conditions and selectors is left a bool, with a warning. A
selector's stale id in the slot it doesn't read (the M4A1's and USP's graphs have some) is cleared, so a revert leaves
those out.

kastov_animgraph.py converts the graphs it writes while ENABLED is true.

s&box's own viewmodels (the M4A1, MP5, M700, Spaghelli, USP, USP-SD, 1911 and the knives) come from cloud packages,
whose graphs are compiled only. So copies of them, decompiled with Source2Viewer-CLI, are in
Assets/animgraphs/viewmodels/, converted, and those guns' viewmodel prefabs use them (`VIEWMODELS`):

    Source2Viewer-CLI.exe -i <.sbox/cloud copy of v_m4a1.vanmgrph_c> -d -o <dir>    (one per graph, from a copy)
    python Tools/animgraph_flags.py --import <dir>    copy them in, converted, and point the prefabs at them
    python Tools/animgraph_flags.py --unpin           point the prefabs back at the models' own graphs

Once s&box has #6000: `--revert`, then `--unpin` (the copies can then go), and set ENABLED to False.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "Assets"

# Turn this off (and run --revert) once the installed s&box has sbox-public #6000.
ENABLED = True

OPTIONS = ("false", "true")
NONE = "4294967295"

VIEWMODEL_GRAPHS = ASSETS / "animgraphs" / "viewmodels"

# Viewmodel prefab: (its gun's model, the graph copy that model's own graph is decompiled into). The 1911's model uses
# the USP's graph.
VIEWMODELS = {
    "Weapons/M4A1/vm_m4a1.prefab": ("models/weapons/sbox_assault_m4a1/v_m4a1.vmdl", "v_m4a1"),
    "Weapons/MP5/vm_mp5.prefab": ("models/weapons/sbox_smg_mp5/v_mp5.vmdl", "v_mp5"),
    "Weapons/M700/vm_m700.prefab": ("models/weapons/sbox_sniper_m700/v_m700.vmdl", "v_m700"),
    "Weapons/Spaghelli/vm_spaghelli.prefab": ("models/weapons/sbox_shotgun_spaghellim4/v_spaghellim4.vmdl",
                                              "v_spaghellim4"),
    "Weapons/USP/vm_usp.prefab": ("models/weapons/sbox_pistol_usp/v_usp.vmdl", "v_usp"),
    "Weapons/USP_SD/vm_usp_sd.prefab": ("models/weapons/sbox_pistol_usp/v_usp.vmdl", "v_usp"),
    "Weapons/Colt1911/vm_colt1911.prefab": ("models/weapons/sbox_pistol_1911/v_1911.vmdl", "v_usp"),
    "Weapons/Knife/vm_knife.prefab": ("models/weapons/sbox_melee_trenchknife/v_trenchknife.vmdl", "v_trenchknife"),
    "Weapons/Knife_Bayonet/vm_knife_bayonet.prefab": ("models/weapons/sbox_melee_trenchknife/v_trenchknife.vmdl",
                                                      "v_trenchknife"),
}

_ID = re.compile(r"^(\t*)m_id = (\d+)\s*$")
_KEY = re.compile(r"^(\t*)(m_\w+) =\s*$")


def _indent(line: str) -> int:
    return len(line) - len(line.lstrip("\t"))


def _object_bounds(lines: list[str], at: int, depth: int) -> tuple[int, int]:
    """The `{` and `}` lines, at `depth` tabs, of the object holding line `at`."""
    start = at
    while not (_indent(lines[start]) == depth and lines[start].strip() == "{"):
        start -= 1
        if start < 0 or _indent(lines[start]) < depth:
            raise ValueError(f"no object at depth {depth} above line {at + 1}")
    end = at
    while not (_indent(lines[end]) == depth and lines[end].strip() in ("}", "},")):
        end += 1
        if end >= len(lines) or (_indent(lines[end]) < depth and lines[end].strip()):
            raise ValueError(f"no end at depth {depth} below line {at + 1}")
    return start, end


def _field(lines: list[str], start: int, end: int, depth: int, name: str) -> int | None:
    """The line of `name = ...` among an object's own fields (one tab in from its braces)."""
    for i in range(start + 1, end):
        if _indent(lines[i]) == depth + 1 and lines[i].strip().startswith(name + " ="):
            return i
    return None


def _value_id(lines: list[str], key_line: int) -> int:
    """The `m_id = N` line inside a `key = { m_id = N }` field."""
    i = key_line + 1
    while lines[i].strip() != "{":
        i += 1
    if not _ID.match(lines[i + 1]):
        raise ValueError(f"line {key_line + 1}: expected an id under {lines[key_line].strip()}")
    return i + 1


def _parameters(lines: list[str], cls: str) -> dict[str, dict]:
    """Every parameter of class `cls`: its id, name, object bounds and depth."""
    found = {}
    for i, line in enumerate(lines):
        if line.strip() != f'_class = "{cls}"':
            continue
        depth = _indent(line) - 1
        start, end = _object_bounds(lines, i, depth)
        name_line = _field(lines, start, end, depth, "m_name")
        id_key = _field(lines, start, end, depth, "m_id")
        if name_line is None or id_key is None:
            continue
        pid = _ID.match(lines[_value_id(lines, id_key)]).group(2)
        found[pid] = {"name": lines[name_line].split("=", 1)[1].strip().strip('"'), "start": start, "end": end,
                      "depth": depth, "class_line": i}
    return found


def _enum_options(lines: list[str], param: dict) -> list[str]:
    at = _field(lines, param["start"], param["end"], param["depth"], "m_enumOptions")
    if at is None:
        return []
    inline = lines[at].split("=", 1)[1].strip()
    if inline.startswith("["):
        return re.findall(r'"([^"]*)"', inline)
    options = []
    i = at + 2
    while lines[i].strip() not in ("]", "],"):
        options.append(lines[i].strip().rstrip(",").strip('"'))
        i += 1
    return options


def _uses(lines: list[str], pid: str) -> tuple[list, list, list]:
    """Where a parameter's id appears: (conditions, selectors, anything else), as (line, depth) pairs."""
    conditions, selectors, other = [], [], []
    for i, line in enumerate(lines):
        m = _ID.match(line)
        if not m or m.group(2) != pid:
            continue
        key_line = i - 1
        while lines[key_line].strip() == "{":
            key_line -= 1
        key = _KEY.match(lines[key_line])
        name = key.group(2) if key else None
        depth = _indent(lines[key_line]) - 1
        if name == "m_id":
            continue  # its own definition, or the enclosing m_id's value
        if name == "m_paramID":
            start, end = _object_bounds(lines, key_line, depth)
            if _field(lines, start, end, depth, '_class') is not None and \
                    lines[_field(lines, start, end, depth, "_class")].strip() == '_class = "CParameterAnimCondition"':
                conditions.append((key_line, depth))
                continue
        if name in ("m_boolParamID", "m_enumParamID"):
            selectors.append((key_line, depth))
            continue
        other.append((key_line, name))
    return conditions, selectors, other


def convert_text(text: str, revert: bool = False, label: str = "") -> tuple[str, list[str]]:
    """The graph with its bool parameters as enums (or, reverting, back), and a line per parameter changed."""
    lines = text.split("\n")
    report = []
    if revert:
        params = {pid: p for pid, p in _parameters(lines, "CEnumAnimParameter").items()
                  if tuple(_enum_options(lines, p)) == OPTIONS}
    else:
        params = _parameters(lines, "CBoolAnimParameter")

    edits: dict[int, list[str]] = {}  # line -> replacement lines

    for pid, p in params.items():
        conditions, selectors, other = _uses(lines, pid)
        if other:
            where = ", ".join(sorted({name or "?" for _, name in other}))
            print(f"warning: {label}: {p['name']} is also used by {where}; left as it is", file=sys.stderr)
            continue
        d = p["depth"] + 1
        tabs = "\t" * d
        if revert:
            default_line = _field(lines, p["start"], p["end"], p["depth"], "m_defaultValue")
            options_line = _field(lines, p["start"], p["end"], p["depth"], "m_enumOptions")
            default = lines[default_line].split("=", 1)[1].strip() == "1"
            edits[p["class_line"]] = [f'{tabs}_class = "CBoolAnimParameter"']
            edits[default_line] = [f"{tabs}m_bDefaultValue = {'true' if default else 'false'}"]
            end = options_line + 1
            if not lines[options_line].split("=", 1)[1].strip().startswith("["):
                while lines[end].strip() not in ("]", "],"):
                    end += 1
                end += 1
            for i in range(options_line, end):
                edits[i] = []
        else:
            default_line = _field(lines, p["start"], p["end"], p["depth"], "m_bDefaultValue")
            default = lines[default_line].split("=", 1)[1].strip() == "true"
            edits[p["class_line"]] = [f'{tabs}_class = "CEnumAnimParameter"']
            edits[default_line] = [f"{tabs}m_defaultValue = {1 if default else 0}", f"{tabs}m_enumOptions = ",
                                   f"{tabs}["] + [f'{tabs}\t"{option}",' for option in OPTIONS] + [f"{tabs}]"]

        for key_line, depth in conditions:
            start, end = _object_bounds(lines, key_line, depth)
            value_key = _field(lines, start, end, depth, "m_comparisonValue")
            vstart, vend = _object_bounds(lines, value_key + 2, depth + 1)
            type_line = _field(lines, vstart, vend, depth + 1, "m_nType")
            data_line = _field(lines, vstart, vend, depth + 1, "m_data")
            kind = lines[type_line].split("=", 1)[1].strip()
            data = lines[data_line].split("=", 1)[1].strip()
            vt = "\t" * (depth + 2)
            if revert:
                if kind != "2" or data not in ("0", "1"):
                    raise ValueError(f"{label}: {p['name']}'s condition at line {key_line + 1} compares with {kind}/{data}")
                edits[type_line] = [f"{vt}m_nType = 1"]
                edits[data_line] = [f"{vt}m_data = {'true' if data == '1' else 'false'}"]
            else:
                if kind != "1" or data not in ("true", "false"):
                    raise ValueError(f"{label}: {p['name']}'s condition at line {key_line + 1} compares with {kind}/{data}")
                edits[type_line] = [f"{vt}m_nType = 2"]
                edits[data_line] = [f"{vt}m_data = {1 if data == 'true' else 0}"]

        switched = 0
        for start in sorted({_object_bounds(lines, key_line, depth)[0] for key_line, depth in selectors}):
            depth = _indent(lines[start])
            end = _object_bounds(lines, start + 1, depth)[1]
            source = _field(lines, start, end, depth, "m_selectionSource")
            bool_id = _value_id(lines, _field(lines, start, end, depth, "m_boolParamID"))
            enum_id = _value_id(lines, _field(lines, start, end, depth, "m_enumParamID"))
            kind = lines[source].split("=", 1)[1].strip().strip('"')
            st = "\t" * (depth + 1)
            it = "\t" * (depth + 2)
            used = (enum_id if revert else bool_id)
            if kind == ("SelectionSource_Enum" if revert else "SelectionSource_Bool") and \
                    _ID.match(lines[used]).group(2) == pid:
                # Its other slot may hold a stale id from before its source was changed: the switch replaces it.
                switched += 1
                if revert:
                    edits[source] = [f'{st}m_selectionSource = "SelectionSource_Bool"']
                    edits[bool_id] = [f"{it}m_id = {pid}"]
                    edits[enum_id] = [f"{it}m_id = {NONE}"]
                else:
                    edits[source] = [f'{st}m_selectionSource = "SelectionSource_Enum"']
                    edits[bool_id] = [f"{it}m_id = {NONE}"]
                    edits[enum_id] = [f"{it}m_id = {pid}"]
            else:
                # A stale id in a slot the selector doesn't read: it would now name a parameter of the wrong type.
                for slot in (bool_id, enum_id):
                    if _ID.match(lines[slot]).group(2) == pid:
                        edits[slot] = [f"{it}m_id = {NONE}"]

        report.append(f"{p['name']}: {len(conditions)} conditions, {switched} selectors")

    if not edits:
        return text, report
    out = []
    for i, line in enumerate(lines):
        out.extend(edits.get(i, [line]))
    return "\n".join(out), report


def graphs() -> list[Path]:
    return sorted(ASSETS.rglob("*.vanmgrph"))


def set_prefab_graph(text: str, model: str, graph: str | None) -> str:
    """The prefab with the AnimationGraph of the renderer drawing `model` set to `graph` (None: the model's own)."""
    at = text.find(f'"Model": "{model}"')
    if at < 0 or text.find(f'"Model": "{model}"', at + 1) >= 0:
        raise ValueError(f"expected one renderer drawing {model}")
    start = text.rfind('"__type": "Sandbox.SkinnedModelRenderer"', 0, at)
    m = re.compile(r'"AnimationGraph": (null|"[^"]*")').search(text, start, at)
    if start < 0 or not m:
        raise ValueError(f"no AnimationGraph on the renderer drawing {model}")
    value = f'"{graph}"' if graph else "null"
    return text[:m.start()] + f'"AnimationGraph": {value}' + text[m.end():]


def pin_viewmodels(pin: bool, check: bool) -> None:
    for prefab, (model, name) in VIEWMODELS.items():
        path = ASSETS / prefab
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        graph = (VIEWMODEL_GRAPHS / f"{name}.vanmgrph").relative_to(ASSETS).as_posix().lower() if pin else None
        new = set_prefab_graph(text, model, graph)
        if new == text:
            continue
        print(f"{prefab}: {graph or 'the model graph'}")
        if not check:
            bom = raw.startswith(b"\xef\xbb\xbf")
            path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))


PREVIEW_ARMS = "models/first_person/v_first_person_arms_human.vmdl"


def import_viewmodel_graphs(source: Path, check: bool) -> None:
    """Copies the decompiled cloud graphs in `source` into VIEWMODEL_GRAPHS, as editor files, converted."""
    for name in sorted({name for _, name in VIEWMODELS.values()}):
        text = (source / f"{name}.vanmgrph").read_text(encoding="utf-8-sig").replace("\r\n", "\n")
        # Source2Viewer doesn't know the format's name; the version GUID is the editor's animgraph2.
        text = text.replace("format:vrfunknown:", "format:animgraph2:", 1)
        if "format:animgraph2:" not in text.split("\n", 1)[0]:
            raise ValueError(f"{name}: not an animgraph2 file")
        # The editor's preview: Facepunch's arms models and the knife graph's bayonet aren't on this machine, so it
        # previews the gun and arms the game draws.
        model = next(model for model, graph in VIEWMODELS.values() if graph == name)
        text, n = re.subn(r"(\n\tm_previewModels = \n\t\[\n)\t\t\"[^\"]*\",\n", rf'\g<1>\t\t"{model}",\n', text, count=1)
        text, k = re.subn(r"(\n\tm_boneMergeModels = \n\t\[\n).*?(\n\t\])",
                          rf'\g<1>\t\t{{\n\t\t\tm_name = "{PREVIEW_ARMS}"\n\t\t\tm_bEnabled = true\n\t\t}},\g<2>', text,
                          count=1, flags=re.S)
        if n != 1 or k != 1:
            raise ValueError(f"{name}: no preview model list")
        if ENABLED:
            text, _ = convert_text(text, label=name)
        out = VIEWMODEL_GRAPHS / f"{name}.vanmgrph"
        print(f"{out.relative_to(ROOT)}")
        if not check:
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(text.encode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--revert", action="store_true", help="turn the enums back into bools")
    parser.add_argument("--check", action="store_true", help="report what would change, writing nothing")
    parser.add_argument("--import", dest="source", type=Path,
                        help="copy decompiled cloud viewmodel graphs from this folder and point the prefabs at them")
    parser.add_argument("--unpin", action="store_true", help="point the viewmodel prefabs back at their models' graphs")
    args = parser.parse_args()

    if args.source or args.unpin:
        if args.source:
            import_viewmodel_graphs(args.source, args.check)
        pin_viewmodels(not args.unpin, args.check)
        return 0

    changed = 0
    for path in args.files or graphs():
        raw = path.read_bytes()
        text = raw.decode("utf-8-sig")
        crlf = "\r\n" in text
        new, report = convert_text(text.replace("\r\n", "\n"), revert=args.revert, label=path.name)
        if crlf:
            new = new.replace("\n", "\r\n")
        if new == text:
            continue
        changed += 1
        rel = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
        print(f"{rel}: {len(report)} parameters")
        for line in report:
            print(f"    {line}")
        if not args.check:
            bom = raw.startswith(b"\xef\xbb\xbf")
            path.write_bytes((b"\xef\xbb\xbf" if bom else b"") + new.encode("utf-8"))
    print(f"{changed} graphs {'would change' if args.check else 'changed'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

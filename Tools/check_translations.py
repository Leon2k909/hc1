"""
Checks the game's translation tables (Code/Settings/Text/*.cs, see Code/Settings/GameText.cs) against the text the code
shows through Tr( "..." ) / GameText.Get / GameText.Format.

    python Tools/check_translations.py            # problems only
    python Tools/check_translations.py --unused   # also keys no literal Tr call uses (they may be looked up by value)
    python Tools/check_translations.py --keys     # every key and the table it's in
    python Tools/check_translations.py --missing Italian   # the keys Languages/Italian.cs lacks
    python Tools/check_translations.py --todo Italian      # the same as JSON, with the four columns' text for context

It reports text passed to Tr as a literal that no table has (it shows in English), translations left empty,
placeholders ({0}, {1:N0}) missing from a translation, keys in more than one table, and Tr calls with an interpolated
string, which can't be looked up. Text passed by value (Tr( mode.Title )) can't be checked here: in the game,
dev_text_missing lists what was shown in English this session.

The languages after the four columns have a table each in Code/Settings/Text/Languages, which should hold every key
of the column tables. For those it counts the keys each one lacks (--missing lists them), and reports empty
translations, placeholder mismatches, keys in no column table (the English changed, so they're never shown) and keys
given twice.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
CODE = os.path.join(ROOT, "Code")
TABLES = os.path.join(CODE, "Settings", "Text")
LANGUAGES = ("French", "German", "Spanish", "Portuguese")
# The other languages' tables, a file each, named for the language.
LANGUAGE_TABLES = os.path.join(TABLES, "Languages")
# GameText's own code and doc comments mention Tr without being UI.
SKIP_FILES = {"GameText.cs", "GlobalGameNamespace.cs"}

# GameText.Spellings: a key matches the code's English in either spelling.
SPELLINGS = [
    ("colour", "color"), ("colours", "colors"), ("centre", "center"), ("centred", "centered"),
    ("customise", "customize"), ("customised", "customized"), ("customisation", "customization"),
    ("armour", "armor"), ("armoured", "armored"), ("favourite", "favorite"), ("favourites", "favorites"),
    ("grey", "gray"), ("defence", "defense"), ("honour", "honor"), ("behaviour", "behavior"),
    ("personalise", "personalize"), ("optimise", "optimize"), ("organise", "organize"), ("recognise", "recognize"),
    ("metre", "meter"), ("metres", "meters"), ("cancelled", "canceled"), ("travelled", "traveled"),
    ("catalogue", "catalog"), ("analyse", "analyze"), ("minimise", "minimize"), ("maximise", "maximize"),
]
AMERICAN = dict(SPELLINGS)
PLACEHOLDER = re.compile(r"(?<!\{)\{(\d+)(?:[,:][^{}]*)?\}")

# Keys whose Tr call passes more values than the English shows, and how many: a translation may use any of them.
# EndOfMatchScreen gives "{0} PLACE" the English ordinal ("2ND") and the bare number, which other languages use.
EXTRA_ARGUMENTS = {"{0} PLACE": 2}


def placeholders_fit(key, translated):
    """Whether the translation fills the same values as the key, or only values its call is known to pass."""
    used = set(PLACEHOLDER.findall(translated))
    passed = next((count for extra, count in EXTRA_ARGUMENTS.items() if normal(extra) == normal(key)), None)
    if passed:
        return bool(used) and used <= {str(i) for i in range(passed)}
    return used == set(PLACEHOLDER.findall(key))


def read_text(path):
    data = open(path, "rb").read()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        return data.decode("utf-16")
    return data.decode("utf-8-sig", errors="replace")


def normal(text):
    """The key GameText would match: case-insensitive, American spelling."""
    return re.sub(r"[A-Za-z]+", lambda m: AMERICAN.get(m.group(0).lower(), m.group(0).lower()), text)


def read_string(text, i):
    """Decodes the C# string literal starting at text[i]. Returns (value, end, kind) with kind plain/verbatim/interpolated."""
    kind = "plain"
    if text.startswith('$@', i) or text.startswith('@$', i):
        kind, i = "interpolated", i + 2
        verbatim = True
    elif text[i] == '$':
        kind, i, verbatim = "interpolated", i + 1, False
    elif text[i] == '@':
        kind, i, verbatim = "verbatim", i + 1, True
    else:
        verbatim = False
    assert text[i] == '"'
    i += 1
    out = []
    depth = 0  # braces inside an interpolated string, which can hold strings of their own
    while i < len(text):
        c = text[i]
        if kind == "interpolated" and c == '{' and not text.startswith('{{', i):
            depth += 1
        elif kind == "interpolated" and c == '}' and depth:
            depth -= 1
        elif depth and c == '"':
            _, i, _ = read_string(text, i)
            continue
        elif verbatim and c == '"':
            if text.startswith('""', i):
                out.append('"')
                i += 2
                continue
            return "".join(out), i + 1, kind
        elif not verbatim and c == '\\':
            nxt = text[i + 1]
            out.append({'n': '\n', 't': '\t', '0': '\0', 'r': '\r'}.get(nxt, nxt))
            i += 2
            continue
        elif not verbatim and c == '"':
            return "".join(out), i + 1, kind
        out.append(c)
        i += 1
    raise ValueError("unterminated string")


def tokens(text):
    """Strings, words and punctuation of a C# file, without comments."""
    i = 0
    while i < len(text):
        c = text[i]
        if c.isspace():
            i += 1
        elif text.startswith("//", i):
            i = text.find("\n", i) if "\n" in text[i:] else len(text)
        elif text.startswith("/*", i):
            i = text.index("*/", i) + 2
        elif c == '"' or (c in "@$" and i + 1 < len(text) and text[i + 1] in '"@$'):
            value, i, kind = read_string(text, i)
            yield ("str", value, kind)
        elif c == "'":
            end = text.index("'", i + 3 if text[i + 1] == "\\" else i + 2)
            yield ("char", text[i:end + 1], None)
            i = end + 1
        elif c.isalnum() or c == "_":
            j = i
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            yield ("word", text[i:j], None)
            i = j
        elif text.startswith("=>", i):
            yield ("punct", "=>", None)
            i += 2
        else:
            yield ("punct", c, None)
            i += 1


def read_tables():
    """[(table, key, (fr, de, es, pt), file)] for every entry in every table."""
    entries = []
    for name in sorted(os.listdir(TABLES)):
        if not name.endswith(".cs"):
            continue
        path = os.path.join(TABLES, name)
        toks = list(tokens(read_text(path)))
        table = None
        for n, tok in enumerate(toks):
            if tok[:2] == ("word", "TextTable") and n + 1 < len(toks) and toks[n + 1][0] == "word":
                table = toks[n + 1][1]
            window = toks[n:n + 13]
            shape = [t[0] if t[0] == "str" else t[1] for t in window]
            if shape == ["[", "str", "]", "=", "(", "str", ",", "str", ",", "str", ",", "str", ")"]:
                key = window[1][1]
                entries.append((table, key, tuple(window[i][1] for i in (5, 7, 9, 11)), name))
    return entries


def read_language_tables():
    """{language: [(key, text)]} for each table in Code/Settings/Text/Languages (["English"] = "text")."""
    languages = {}
    if not os.path.isdir(LANGUAGE_TABLES):
        return languages
    for name in sorted(os.listdir(LANGUAGE_TABLES)):
        if not name.endswith(".cs"):
            continue
        toks = list(tokens(read_text(os.path.join(LANGUAGE_TABLES, name))))
        pairs = []
        for n in range(len(toks)):
            window = toks[n:n + 5]
            if [t[0] if t[0] == "str" else t[1] for t in window] == ["[", "str", "]", "=", "str"]:
                pairs.append((window[1][1], window[4][1]))
        languages[name[:-3]] = pairs
    return languages


def first_argument(text, i):
    """The first argument of the call whose '(' is at text[i], as source text."""
    depth, j = 0, i + 1
    while j < len(text):
        c = text[j]
        if c == '"' or (c in "@$" and text[j + 1] in '"@$'):
            _, j, _ = read_string(text, j)
            continue
        if c == "'" and j + 2 < len(text) and (text[j + 2] == "'" or text[j + 1] == "\\"):
            j = text.index("'", j + 3 if text[j + 1] == "\\" else j + 2) + 1
            continue
        if c in "([{":
            depth += 1
        elif c in ")]}":
            if depth == 0:
                return text[i + 1:j]
            depth -= 1
        elif c == "," and depth == 0:
            return text[i + 1:j]
        j += 1
    return text[i + 1:]


CALL = re.compile(r"(?<![\w.])(?:Tr|GameText\.Get|GameText\.Format)\s*\(")


def read_calls():
    """[(file, line, text, kind)] for each string literal in the first argument of a Tr call, plus how many calls had none."""
    calls, by_value = [], 0
    for folder, dirs, files in os.walk(CODE):
        dirs[:] = [d for d in dirs if d not in ("obj", "bin")]
        for name in files:
            if not name.endswith((".cs", ".razor")) or name in SKIP_FILES:
                continue
            path = os.path.join(folder, name)
            text = read_text(path)
            for m in CALL.finditer(text):
                line_start = text.rfind("\n", 0, m.start()) + 1
                prefix = text[line_start:m.start()].strip()
                if prefix.startswith(("//", "*", "@*")):
                    continue
                argument = first_argument(text, m.end() - 1)
                line = text.count("\n", 0, m.start()) + 1
                rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
                found = False
                for tok in tokens(argument):
                    if tok[0] == "str":
                        found = True
                        calls.append((rel, line, tok[1], tok[2]))
                if not found:
                    by_value += 1
    return calls, by_value


def main():
    # Translations aren't in the console's code page.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    entries = read_tables()
    calls, by_value = read_calls()
    keys = {}
    for table, key, text, name in entries:
        keys.setdefault(normal(key), []).append((table, key, text))
    languages = read_language_tables()

    if "--keys" in sys.argv:
        for table, key, text, name in entries:
            print(f"{table:14} {key}")
        return

    for flag in ("--missing", "--todo"):
        if flag not in sys.argv:
            continue
        at = sys.argv.index(flag) + 1
        language = sys.argv[at] if at < len(sys.argv) else ""
        if language not in languages:
            print(f"{flag} <language>: one of {', '.join(languages)}")
            return
        have = {normal(key) for key, _ in languages[language]}
        # One entry per key: CommonText's if it has it, as in the game.
        wanted = {}
        for table, key, text, name in entries:
            if normal(key) not in have and (normal(key) not in wanted or table == "CommonText"):
                wanted[normal(key)] = (table, key, text)
        if flag == "--missing":
            for table, key, text in wanted.values():
                print(f"{table:14} {key}")
            print(f"\n{len(wanted)} key(s) missing from Languages/{language}.cs")
        else:
            import json
            print(json.dumps([{"table": table, "key": key, **dict(zip(("fr", "de", "es", "pt"), text))}
                              for table, key, text in wanted.values()], ensure_ascii=False, indent=1))
        return

    problems = 0

    missing = {}
    for rel, line, text, kind in calls:
        if kind == "interpolated":
            print(f"INTERPOLATED  {rel}:{line}  Tr( $\"{text}\" ) can't be looked up; use Tr( \"...{{0}}...\", value )")
            problems += 1
        elif text.strip() and any(ch.isalpha() for ch in text) and normal(text) not in keys:
            missing.setdefault(text, []).append(f"{rel}:{line}")
    for text, where in sorted(missing.items(), key=lambda kv: kv[1][0]):
        print(f"MISSING       {text!r}  ({', '.join(where[:3])}{' ...' if len(where) > 3 else ''})")
    problems += len(missing)

    for norm, found in keys.items():
        if len(found) > 1:
            tables = ", ".join(f"{t} {k!r}" for t, k, _ in found)
            print(f"DUPLICATE     {tables}  (CommonText wins; otherwise the later table)")
            problems += 1
        for table, key, text in found:
            for language, translated in zip(LANGUAGES, text):
                if not translated.strip():
                    print(f"EMPTY         {table} {key!r}: {language}")
                    problems += 1
                elif not placeholders_fit(key, translated):
                    print(f"PLACEHOLDERS  {table} {key!r}: {language} {translated!r}")
                    problems += 1

    coverage = []
    for language, pairs in languages.items():
        seen = set()
        for key, translated in pairs:
            norm = normal(key)
            if norm in seen:
                print(f"DUPLICATE     {language} {key!r}  (given twice; the later one wins)")
                problems += 1
            seen.add(norm)
            if norm not in keys:
                print(f"STALE         {language} {key!r}  (no column table has this English, so it's never shown)")
                problems += 1
            if not translated.strip():
                print(f"EMPTY         {language} {key!r}")
                problems += 1
            elif not placeholders_fit(key, translated):
                print(f"PLACEHOLDERS  {language} {key!r}: {translated!r}")
                problems += 1
        lacking = sum(1 for norm in keys if norm not in seen)
        if lacking:
            print(f"INCOMPLETE    {language}: {lacking} of {len(keys)} keys missing (--missing {language} lists them)")
            problems += 1
        coverage.append(f"{language} {len(keys) - lacking}")

    if "--unused" in sys.argv:
        used = {normal(text) for _, _, text, _ in calls}
        for table, key, text, name in entries:
            if normal(key) not in used:
                print(f"UNUSED?       {table} {key!r}")

    tables = sorted({t for t, _, _, _ in entries})
    print(f"\n{len(entries)} keys in {len(tables)} tables ({', '.join(tables)}); {len(calls)} literal texts in Tr calls, "
          f"{by_value} calls by value; {problems} problem(s).")
    if coverage:
        print(f"Keys translated in Languages/: {', '.join(coverage)} (of {len(keys)}).")


if __name__ == "__main__":
    main()

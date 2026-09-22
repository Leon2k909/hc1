"""Inventory the downloaded MW2022 M4 and dependencies without executing addon Lua."""
import argparse
import collections
import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PACKS = {"2962304029": "Modern Warfare 2022 SWEPs - M4",
         "3529121373": "Modern Warfare 2022 SWEPs - Shared Content",
         "2459720887": "Modern Wokefare Base"}
CATEGORIES = ["Perk", "Underbarrel", "Barrel", "Stock", "Magazine", "RearGrip",
              "Muzzle", "Optic", "Camo", "Laser", "Launcher"]


def uncomment(text):
    text = re.sub(r"--\[\[.*?\]\]", "", text, flags=re.S)
    return re.sub(r"--[^\n]*", "", text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cache", type=Path, default=Path("D:/tmp/hc1-mw22-tools"))
    args = parser.parse_args()
    cache = args.cache.resolve()
    entries, pack_info = {}, []
    for pack_id, title in PACKS.items():
        root = cache / "extracted" / pack_id
        if not root.is_dir():
            raise FileNotFoundError(root)
        archive = cache / "steamcmd/steamapps/workshop/content/4000" / pack_id / "gmpublisher.gma"
        with archive.open("rb") as stream:
            digest = hashlib.file_digest(stream, "sha256").hexdigest()
        counts = collections.Counter(p.suffix for p in root.rglob("*") if p.is_file())
        pack_info.append(dict(id=pack_id, title=title, url=f"https://steamcommunity.com/sharedfiles/filedetails/?id={pack_id}",
                              archive=str(archive), bytes=archive.stat().st_size, sha256=digest,
                              extracted=str(root), file_counts=dict(sorted(counts.items()))))
        for path in root.rglob("*.lua"):
            text = uncomment(path.read_text(encoding="utf-8-sig", errors="replace"))
            if "ATTACHMENT." not in text:
                continue
            matches = re.findall(r'''ATTACHMENT\.(\w+)\s*=\s*(?:Model\s*\(\s*|Material\s*\(\s*)?(?:"((?:\\.|[^"\\])*)"|'((?:\\.|[^'\\])*)')''', text)
            fields = {key: (double or single).replace('\\"', '"').replace("\\'", "'")
                      for key, double, single in matches}
            entries.setdefault(path.stem, dict(fields, lua=str(path), pack=pack_id))

    def inherited(key, visited=None):
        visited = set() if visited is None else visited
        if key in visited or key not in entries:
            return {}
        visited.add(key)
        item = entries[key]
        result = inherited(item.get("Base"), visited)
        result.update(item)
        return result

    customization = cache / "extracted/2962304029/lua/weapons/mg_iw9_mike4/customization.lua"
    text = uncomment(customization.read_text())
    text = text.split("SWEP.Customization =", 1)[1].split('require("mw_utils")', 1)[0]
    groups = re.findall(r"\{([^{}]+)\}", text)
    assert len(groups) == len(CATEGORIES), f"Unexpected customization groups: {len(groups)}"
    attachments = []
    for category, group in zip(CATEGORIES, groups):
        for index, key in enumerate(re.findall(r'"([^"\n]+)"', group)):
            fields = inherited(key)
            model = fields.get("Model", "")
            candidates = [cache / "extracted" / i / model for i in PACKS] if model else []
            found = next((p for p in candidates if p.is_file()), None)
            attachments.append(dict(key=key, category=category, default=index == 0,
                                    name=fields.get("Name", key), model=model,
                                    model_file=str(found) if found else None,
                                    source=entries.get(key), inherited=fields))
    result = dict(packs=pack_info, attachments=attachments,
                  missing_definitions=[x["key"] for x in attachments if x["source"] is None],
                  missing_models=[x["model"] for x in attachments if x["model"] and x["model_file"] is None])
    (HERE / "inventory.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(dict(packs=len(pack_info), entries=len(attachments),
                          model_files=len({x['model_file'] for x in attachments if x['model_file']}),
                          categories=dict(collections.Counter(x['category'] for x in attachments)),
                          missing_definitions=result['missing_definitions'], missing_models=result['missing_models']), indent=2))


if __name__ == "__main__":
    main()

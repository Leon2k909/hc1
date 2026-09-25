"""List the visual MP5 attachments declared by the extracted MW19 addon.

The source packages live outside the project in D:/tmp/hc1-mw22-tools/extracted.
"""

from __future__ import annotations

import re
from pathlib import Path


EXTRACTED = Path(r"D:\tmp\hc1-mw22-tools\extracted")
SMG = EXTRACTED / "2802430252"
BASE = EXTRACTED / "2459720887"
CUSTOMIZATION = SMG / "lua/weapons/mg_mpapa5/customization.lua"


def active_choices() -> list[list[str]]:
    source = CUSTOMIZATION.read_text(encoding="utf-8-sig", errors="replace")
    section = source.split("SWEP.Customization = {", 1)[1].split("-- SWEP.Customization", 1)[0]
    return [re.findall(r'"([^"]+)"', row) for row in re.findall(r"\{([^{}]+)\}", section)]


def attachment_source(key: str) -> tuple[Path | None, str | None, str | None]:
    for root in (SMG, BASE):
        paths = list((root / "lua").rglob(key + ".lua"))
        if paths:
            source = paths[0].read_text(encoding="utf-8-sig", errors="replace")
            name = re.search(r'ATTACHMENT\.Name\s*=\s*"([^"]+)"', source)
            model = re.search(r'ATTACHMENT\.Model\s*=\s*Model\("([^"]+)"\)', source)
            return paths[0], name.group(1) if name else None, model.group(1) if model else None
    for root in (SMG, BASE):
        for path in (root / "lua").rglob("attachments*.lua"):
            source = path.read_text(encoding="utf-8-sig", errors="replace")
            match = re.search(r'MW_ATT_KEYS\["' + re.escape(key) + r'"\]\s*=\s*\{(.+?)\n\}', source, re.DOTALL)
            if match:
                entry = match.group(1)
                name = re.search(r'Name\s*=\s*"([^"]+)"', entry)
                model = re.search(r'Model\s*=\s*Model\("([^"]+)"\)', entry)
                return path, name.group(1) if name else None, model.group(1) if model else None
    return None, None, None


def main() -> None:
    for row in active_choices():
        category = row[0]
        print(f"\n{category}: {len(row) - 1} options")
        for key in row[1:]:
            path, name, model = attachment_source(key)
            model_path = None
            if model:
                for root in (SMG, BASE):
                    candidate = root / model
                    if candidate.is_file():
                        model_path = candidate
                        break
            state = "OK" if model_path else "MISSING" if model else "NO MODEL"
            print(f"  {key:52s} {state:8s} {name or '':32s} {model or ''}")


if __name__ == "__main__":
    main()

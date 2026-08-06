#!/usr/bin/env python3
import os
import re
from pathlib import Path

p = Path("data/config.yaml")
t = p.read_text(encoding="utf-8")
ids = os.environ["SONG_IDS"].strip()
if not re.fullmatch(r"[0-9,\s;]+", ids):
    raise SystemExit("SONG_IDS contains invalid characters")
ids = re.sub(r"[;\s]+", ",", ids)
ids = re.sub(r",+", ",", ids).strip(",")
if not ids:
    raise SystemExit("SONG_IDS empty after normalize")
t2, n = re.subn(
    r'(playids:\n(?:.*\n)*?\s+ids:\s*)""',
    r'\1"' + ids + '"',
    t,
    count=1,
)
if n != 1:
    raise SystemExit("failed to inject playids.ids")

# force secondary empty until fan jar is built
lines = t2.splitlines(True)
out = []
i = 0
while i < len(lines):
    if lines[i].lstrip().startswith("secondary:"):
        indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
        out.append(f"{indent}secondary: []\n")
        i += 1
        while i < len(lines):
            raw = lines[i]
            stripped = raw.strip()
            if stripped.startswith("-"):
                i += 1
                continue
            break
        continue
    out.append(lines[i])
    i += 1

t2 = "".join(out).replace("enableMain: false", "enableMain: true")

# Pin version so AutoUpgrade does not merge remote default title pools
t2 = re.sub(r"(?m)^version:.*$", "version: 1.1.12", t2, count=1)
p.write_text(t2, encoding="utf-8")
print("config prepared (secondary empty; ver 1.1.12; note untouched - Actions uses publish_private_note.py)")

#!/usr/bin/env python3
"""Clone main cookie.json jar and replace MUSIC_U with secondary token."""
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path

sec = (os.environ.get("SEC") or "").strip()
if sec.startswith("MUSIC_U="):
    sec = sec.split("=", 1)[1].strip()
if not sec:
    print("no SEC; skip secondary")
    raise SystemExit(0)

main_path = Path("data/cookie.json")
if not main_path.is_file():
    raise SystemExit("data/cookie.json missing")

raw = json.loads(main_path.read_text(encoding="utf-8"))
fan = deepcopy(raw)
replaced = 0

if isinstance(fan, dict):
    for domain, cookies in fan.items():
        if not isinstance(cookies, dict):
            continue
        for name, ent in list(cookies.items()):
            if not isinstance(ent, dict):
                continue
            if ent.get("Name") == "MUSIC_U" or name == "MUSIC_U":
                ent = dict(ent)
                ent["Value"] = sec
                ent["Name"] = "MUSIC_U"
                cookies[name] = ent
                replaced += 1
    if replaced == 0:
        for domain, cookies in list(fan.items()):
            if not isinstance(cookies, dict):
                continue
            sample = next(iter(cookies.values())) if cookies else {}
            ent = dict(sample) if isinstance(sample, dict) else {}
            ent.update(
                {
                    "Name": "MUSIC_U",
                    "Value": sec,
                    "Path": ent.get("Path") or "/",
                    "Domain": ent.get("Domain") or domain,
                }
            )
            cookies["MUSIC_U"] = ent
            replaced += 1

Path("data/fan1.json").write_text(json.dumps(fan, ensure_ascii=False), encoding="utf-8")
print(
    f"secondary jar built, music_u_fields={replaced}, bytes={Path('data/fan1.json').stat().st_size}"
)

cfg = Path("data/config.yaml")
t = cfg.read_text(encoding="utf-8")
lines = t.splitlines(True)
out = []
i = 0
done = False
while i < len(lines):
    if (not done) and lines[i].lstrip().startswith("secondary:"):
        indent = lines[i][: len(lines[i]) - len(lines[i].lstrip())]
        out.append(f"{indent}secondary:\n")
        out.append(f'{indent}  - "./fan1.json"\n')
        out.append(f'{indent}  - "./cookie.json"\n')
        i += 1
        while i < len(lines):
            raw_line = lines[i]
            stripped = raw_line.strip()
            if stripped.startswith("-"):
                i += 1
                continue
            break
        done = True
        continue
    out.append(lines[i])
    i += 1

t2 = "".join(out).replace("enableMain: false", "enableMain: true")
if '"./fan1.json"' not in t2:
    raise SystemExit("failed to write secondary list into config")
cfg.write_text(t2, encoding="utf-8")
print("config secondary: fan1 + main fallback")

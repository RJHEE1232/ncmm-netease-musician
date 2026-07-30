#!/usr/bin/env python3
import os
import re
import sys

ids = []
for part in re.split(r"[,;\s]+", os.environ.get("SONG_IDS", "")):
    part = part.strip()
    if part.isdigit():
        ids.append(part)
ids.sort(key=len, reverse=True)

title_re = re.compile(r'歌名=(?:"[^"]*"|\\"[^\\"]*\\")')
nick_re = re.compile(r'昵称=(?:"[^"]*"|\\"[^\\"]*\\")')
songid_re = re.compile(r"songId=\S+")
uid_re = re.compile(r"\buid=\d+")

for raw in sys.stdin.buffer:
    try:
        line = raw.decode("utf-8", errors="replace")
    except Exception:
        continue
    line = line.replace("\r", "\n")
    for chunk in line.splitlines(True):
        s = chunk.rstrip("\n\r")
        for i in ids:
            s = s.replace(i, "[song]")
        s = title_re.sub('歌名="[redacted]"', s)
        s = nick_re.sub('昵称="[redacted]"', s)
        s = songid_re.sub("songId=[song]", s)
        s = uid_re.sub("uid=[redacted]", s)
        low = s.lower()
        if any(x in low for x in ("music_u", "authorization", "password=", "cookie=")):
            continue
        sys.stdout.write(s + "\n")
        sys.stdout.flush()

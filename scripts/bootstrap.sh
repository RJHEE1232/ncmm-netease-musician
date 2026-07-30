#!/bin/sh
set -e

echo "[bootstrap] ncmm HF entrypoint"

mkdir -p /data

# 1) 释放默认配置（不覆盖用户已有文件）
if [ ! -f /data/config.yaml ]; then
  echo "[bootstrap] seeding /data/config.yaml"
  cp /opt/ncmm-hf/config.hf.yaml /data/config.yaml
fi
if [ ! -f /data/notify.yaml ]; then
  echo "[bootstrap] seeding /data/notify.yaml"
  cp /opt/ncmm-hf/notify.hf.yaml /data/notify.yaml
fi

# 2) 可选：用 NOTIFY_WEBHOOK_URL 打开 webhook
if [ -n "${NOTIFY_WEBHOOK_URL:-}" ]; then
  echo "[bootstrap] enabling webhook notify from NOTIFY_WEBHOOK_URL"
  if command -v sed >/dev/null 2>&1; then
    # 仅打开 config 里 notify.enabled（第一处 enabled: false 可能不是 notify；用更稳的 python）
    python3 - <<'PY' || true
import os, re, pathlib
p = pathlib.Path("/data/config.yaml")
t = p.read_text(encoding="utf-8")
t2, n = re.subn(
    r"(notify:\n(?:.*\n)*?\s+enabled:\s*)false",
    r"\1true",
    t,
    count=1,
)
if n:
    p.write_text(t2, encoding="utf-8")
url = os.environ.get("NOTIFY_WEBHOOK_URL", "")
np = pathlib.Path("/data/notify.yaml")
nt = np.read_text(encoding="utf-8")
# 重写 webhook 段开关
lines = nt.splitlines()
out = []
i = 0
while i < len(lines):
    if lines[i].startswith("webhook:"):
        out.extend([
            "webhook:",
            "  enabled: true",
            f'  url: "{url}"',
            "  method: POST",
            "  headers: {}",
            '  body_template: ""',
        ])
        i += 1
        while i < len(lines) and (lines[i].startswith(" ") or lines[i].startswith("\t") or lines[i].strip() == ""):
            i += 1
        continue
    out.append(lines[i])
    i += 1
np.write_text("\n".join(out) + "\n", encoding="utf-8")
print("[bootstrap] notify webhook written")
PY
  fi
fi

# 3) Cookie：CookieCloud 优先，否则 MUSIC_U
if [ -n "${COOKIECLOUD_UUID:-}" ] && [ "$COOKIECLOUD_UUID" != "your-uuid" ]; then
  echo "[bootstrap] CookieCloud login"
  ncmm -c /data/config.yaml login cookiecloud \
    -u "$COOKIECLOUD_UUID" \
    -p "${COOKIECLOUD_PASSWORD:-}" \
    -s "${COOKIECLOUD_SERVER:-https://cookiecloud.deyer.cn}" \
    -m || echo "[bootstrap] WARN: CookieCloud failed"
elif [ -n "${MUSIC_U:-}" ] && [ ! -f /data/cookie.json ]; then
  echo "[bootstrap] MUSIC_U -> login cookie"
  case "$MUSIC_U" in
    *MUSIC_U=*) COOKIE_STR="$MUSIC_U" ;;
    *) COOKIE_STR="MUSIC_U=${MUSIC_U}" ;;
  esac
  ncmm -c /data/config.yaml login cookie "$COOKIE_STR" -m || echo "[bootstrap] WARN: cookie login failed"
elif [ -f /data/cookie.json ]; then
  echo "[bootstrap] existing /data/cookie.json"
else
  echo "[bootstrap] WARN: no cookie yet — set MUSIC_U or COOKIECLOUD_* secrets"
fi

# 4) 导出 env 给 cron
mkdir -p /etc/ncmm
printenv | grep -E '^(TZ|PATH|COOKIECLOUD_|MUSIC_U|NOTIFY_)' | sed 's/^/export /' > /etc/ncmm/env.sh || true
echo "export PATH=/usr/local/bin:/usr/bin:/bin" >> /etc/ncmm/env.sh

# 5) 安装 crontab
true > /etc/crontabs/root

add_cron() {
  expr_and_cmd="$1"
  [ -z "$expr_and_cmd" ] && return 0
  set -- $expr_and_cmd
  m=$1; h=$2; dom=$3; mon=$4; dow=$5
  shift 5
  cmd="$*"
  [ -z "$cmd" ] && cmd="task"
  echo "$m $h $dom $mon $dow . /etc/ncmm/env.sh && /usr/local/bin/ncmm -c /data/config.yaml $cmd >> /data/cron.log 2>&1" >> /etc/crontabs/root
  echo "[bootstrap] cron: $m $h $dom $mon $dow -> ncmm $cmd"
}

add_cron "${CRON_1:-30 8 * * * task}"
add_cron "${CRON_2:-0 14 * * * musician}"
[ -n "${CRON_3:-}" ] && add_cron "$CRON_3"

# 6) 起 crond（后台）
if [ -s /etc/crontabs/root ]; then
  echo "[bootstrap] starting crond"
  crond -b -l 8 || crond -b -l 2 || echo "[bootstrap] WARN: crond start failed"
fi

# 7) 可选：启动时立刻跑一次
if [ "${DEBUG_RUN_ON_START:-0}" = "1" ]; then
  echo "[bootstrap] DEBUG_RUN_ON_START musician"
  ncmm -c /data/config.yaml musician || true
fi

# 8) 前台 keep-alive（HF 需要绑定 app_port）
echo "[bootstrap] starting keepalive on ${PORT:-7860}"
exec python3 /opt/ncmm-hf/keepalive.py

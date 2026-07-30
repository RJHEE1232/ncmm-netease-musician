---
title: ncmm-netease-musician
emoji: 🎵
colorFrom: pink
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# ncmm · 网易云音乐人任务（HF 部署）

基于 [3899/ncmm](https://github.com/3899/ncmm) 的 Hugging Face Docker Space 适配层。

自动完成：

- 音乐人日常签到 + 云豆领取
- **月度 VIP 进阶**（发笔记、刷播放量）→ 解锁 / 维持黑胶 VIP
- 云贝 / 会员中心等日常任务（可配置）
- 容器内 cron 定时执行

> 仅供学习交流。账号风险自负。

## 架构

```
HF Space (Docker)
  └─ bootstrap.sh
       ├─ 种子 /data/config.yaml
       ├─ CookieCloud 或 MUSIC_U 登录
       ├─ crond（CRON_1 / CRON_2）
       └─ keepalive.py → :7860 /health
```

业务二进制来自官方镜像 `ghcr.io/3899/ncmm`，本仓库只做 HF 适配。

## 必配 Secrets

Space → **Settings** → **Variables and secrets**

| Name | 类型 | 说明 |
|------|------|------|
| `MUSIC_U` | Secret | 网易云 `MUSIC_U`（与 CookieCloud 二选一） |
| `COOKIECLOUD_SERVER` | Secret | CookieCloud 地址（可选） |
| `COOKIECLOUD_UUID` | Secret | CookieCloud UUID（可选） |
| `COOKIECLOUD_PASSWORD` | Secret | CookieCloud 密码（可选） |
| `NOTIFY_WEBHOOK_URL` | Secret | 失败通知 Webhook（可选） |
| `CRON_1` | Variable | 默认 `30 8 * * * task` |
| `CRON_2` | Variable | 默认 `0 14 * * * musician` |
| `DEBUG_RUN_ON_START` | Variable | `1` = 启动先跑一次 musician；稳定后改 `0` |
| `TZ` | Variable | `Asia/Shanghai` |

## 获取 MUSIC_U

1. 浏览器登录 [music.163.com](https://music.163.com)
2. F12 → Application → Cookies → `music.163.com`
3. 复制 `MUSIC_U` 的值
4. 账号需已入驻**音乐人**

## 默认定时

| Cron | 命令 | 含义 |
|------|------|------|
| `30 8 * * *` | `task` | 日常批量（签到、云贝等） |
| `0 14 * * *` | `musician` | 音乐人日常 + 月度 VIP 进阶 |

## 健康检查

```text
GET /health
```

返回示例：

```json
{
  "service": "ncmm-hf",
  "status": "ok",
  "cookie_present": true,
  "uptime_sec": 120
}
```

## free Space 休眠

免费 Space 休眠后 **cron 不会跑**。任选其一：

1. 付费 **Always On**
2. UptimeRobot 等每 5–10 分钟请求一次 `/health`

## 本地构建

```bash
docker build -t ncmm-hf:local .
docker run --rm -p 7860:7860 -e MUSIC_U="你的token" ncmm-hf:local
curl -s http://127.0.0.1:7860/health
```

## 上游

- https://github.com/3899/ncmm
- 镜像：`ghcr.io/3899/ncmm:latest`

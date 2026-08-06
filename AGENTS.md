# AGENTS.md — 网易云任务适配仓

## 项目定位
GitHub Actions 定时跑 [3899/ncmm](https://github.com/3899/ncmm) 的适配壳：签到、云贝、音乐人任务与播放进阶。Public 仓库，**凭证永不进 git**。

## 怎么跑
- 定时：workflow `on.schedule`（UTC `00:30`=task、`06:00`=musician），另支持 `workflow_dispatch` 手动选 `musician/task/sign/musician-vip/musician-sign/note`
- 必配 Secrets：`MUSIC_U`（主号）、`SONG_IDS`（曲目 ID，逗号分隔）；可选 `SECONDARY_MUSIC_U`（辅助号）
- 本地：`docker build -t ncmm-hf:local . && docker run ...`（Dockerfile + scripts/bootstrap.sh）

## 技术栈与关键约定
- 运行时用官方镜像 `ghcr.io/3899/ncmm:latest`；本仓只做适配
- 配置：`configs/config.gha.yaml`（Actions 用，运行时由 `scripts/inject_songs.py` 注入曲目；Actions 的 `note` 发帖走 `scripts/publish_private_note.py` 发仅自己可见纯文字「1」（可选 --image-url 配图），**不走 ncmm note**（上游默认公开））
- 辅助号：`scripts/build_secondary_jar.py` 克隆主号 cookie 结构换 `MUSIC_U`（上游 `login` 辅助路径会 panic，**不要**改回 `ncmm login` 无 `-m` 方式）
- 日志脱敏：`scripts/redact_logs.py`（曲目 ID/歌名/昵称/uid → 占位符）；**不要在公开层打印 cookie 原文**

## 目录
- `.github/workflows/ncmm-cron.yml` — 唯一入口 workflow（超时 120min）
- `configs/` — 配置模板（gha/hf/notify）
- `scripts/` — inject_songs / build_secondary_jar / redact_logs / bootstrap / keepalive / publish_private_note
- `docs/PUBLIC-PRIVACY.md` — public 隐私纪律

## 当前状态与下一步
- 音乐人签到 ✅、播放进阶 ✅（辅助号 jar 方案已跑通）、笔记任务 30 天窗口已 4/4 ✅、发帖（仅自己可见纯文字「1」）✅（`scripts/publish_private_note.py`，workflow `note` dispatch，privacySetting=1）
- 已知：Actions 机房 IP 发笔记/发帖偶发 `code=250`（风控），失败重试或本机跑即可
- 遗留：旧 Actions run 日志保留行为画像，如需彻底清除需用户手动删除 run（本仓历史已用 filter-repo 清洗并 force-push）

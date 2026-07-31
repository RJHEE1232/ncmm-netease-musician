# 网易云任务适配（GitHub Actions）

基于开源 [3899/ncmm](https://github.com/3899/ncmm) 的定时运行适配层。

> 仅供学习交流。账号风险自负。

## 功能概览

- 日常签到 / 云贝类任务（可配置）
- 音乐人相关任务与进阶播放（可配置）
- Secrets 注入凭证，不把 cookie 写入 git
- 日志脱敏（曲目 / 昵称 / uid 等）

## 隐私要点

- 登录凭证只放在 **Settings → Secrets and variables → Actions**
- 代码与配置模板不含真实 cookie / 曲目 ID
- 跑完清理工作区临时文件
- **Public 仓库无法隐藏「在跑自动化」这一事实**；只需隐藏凭证时保持 Secrets 即可

## 必配 Secrets

| Name | 说明 |
|------|------|
| `MUSIC_U` | 主号 cookie 中的 `MUSIC_U` |
| `SONG_IDS` | 逗号分隔的歌曲数字 ID（可选，用于播放进阶） |
| `SECONDARY_MUSIC_U` | 辅助号 `MUSIC_U`（可选） |

**不要**把上述值写进 README、Issue 或配置文件。

## 可选 Variables

| Name | 说明 |
|------|------|
| 无强制 | 定时在 workflow `on.schedule` 中配置 |

## 获取 `MUSIC_U`

1. 浏览器登录网易云网页版  
2. 开发者工具 → Application → Cookies  
3. 复制 `MUSIC_U` 的值到 Secret（不要发到公开讨论区）

## 运行

1. 配置 Secrets  
2. Actions → 对应 workflow → Run workflow  
3. 查看运行结果（日志已做脱敏）

定时任务见 `.github/workflows/` 内 `schedule` 字段（UTC）。

## 本地 / 容器（可选）

仓库内含 Dockerfile 与脚本，可按需自行构建；默认推荐 Actions 定时。

## 上游

- https://github.com/3899/ncmm

## 说明

本仓库为通用适配示例，不绑定特定个人主页或其它平台账号。

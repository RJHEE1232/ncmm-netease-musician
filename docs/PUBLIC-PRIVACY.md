# Public 仓库隐私保护说明

本仓库 **代码公开**，但 **账号凭证绝不进 git**。

## 会公开的

- Dockerfile / workflow / 配置模板（无账号信息）
- Actions 运行状态（成功/失败、耗时）
- 脱敏后的任务日志（已过滤 cookie / token 关键字）

## 不会公开的（你必须遵守）

| 项 | 做法 |
|----|------|
| `MUSIC_U` | 只放 **Settings → Secrets and variables → Actions** |
| cookie 文件 | workflow 结束 `scrub` 删除；禁止 `actions/upload-artifact` |
| Issue / PR | 禁止粘贴 cookie、手机号、抓包全文 |
| Fork | fork **带不走** 你的 Secrets；别人跑的是他们自己的空 secret |
| 日志 | workflow 已 `::add-mask::` + `scripts/redact_logs.py` 过滤（曲目/歌名/昵称/uid 打码）；仍避免在 `echo` 里拼 secret |

## Secrets 配置

1. 打开仓库 **Settings → Secrets and variables → Actions**
2. **New repository secret**
   - Name: `MUSIC_U`
   - Value: 浏览器 Cookie 里的 `MUSIC_U` 值（可带或不带 `MUSIC_U=` 前缀）
3. 不要写进 `README`、不要写进 `config.yaml`、不要截图发 Issue

## 可选加强

1. **Environment `prod`**：Settings → Environments → 新建 `prod`，加 Secret，workflow `environment: prod`，可要求手动批准
2. **关掉 public fork 的 Actions**（对你自己仓无必要；fork 默认无你的 secret）
3. **仓库名中性**：避免用手机号/艺名当 repo 名
4. **定期轮换 MUSIC_U**：网页重新登录后更新 Secret
5. **通知走私有 Webhook**：若启用 `NOTIFY_WEBHOOK_URL`，也必须用 Secret，且 webhook 对端不要回显正文到公开群

## 风险残留（public 无法 100% 消除）

- GitHub 员工/平台侧理论上能访问运行中的 secret 内存（任意 CI  orth 同理）
- 运行日志若 ncmm 打印了未覆盖的敏感字段，仍可能漏出 → 发现后立刻轮换 cookie 并提 Issue 打码规则
- 共享 runner 出口 IP 为机房段，与「隐私」无关但与风控有关

## 应急

若 `MUSIC_U` 曾粘贴到 Issue/聊天/提交：

1. 网易云网页 **退出所有会话 / 改密（若有）**
2. 重新登录拿新 `MUSIC_U`
3. 更新 GitHub Secret
4. 删除泄露内容

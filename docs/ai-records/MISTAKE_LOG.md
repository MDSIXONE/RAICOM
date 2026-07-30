# 犯错记录

每次开启新对话前阅读此文档。仅记录已经确认、可帮助后续工作避免重复的错误与教训。

## 模板：YYYY-MM-DD｜简短标题

- 现象：
- 原因：
- 防范规则：
- 关联改动：

## 2026-07-30｜GitHub CLI 登录未配置 Git 推送凭据

- 现象：`gh auth status` 显示已登录，但 `git push` 因无法读取 GitHub 用户名而失败。
- 原因：全局 Git Credential Manager 覆盖了 GitHub CLI 的 URL 专用凭据助手。
- 防范规则：首次推送前先运行 `gh auth setup-git` 并验证 Git 凭据助手实际可用；若仍失败，在仓库本地将 `credential.helper` 覆盖为 GitHub CLI 助手后再推送。
- 关联改动：`chore: establish project directory structure`

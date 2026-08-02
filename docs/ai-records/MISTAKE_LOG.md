# 犯错记录

此文档保存已经确认、可帮助后续工作避免重复的错误与教训。

## 模板：YYYY-MM-DD｜简短标题

- 现象：
- 原因：
- 防范规则：
- 关联改动：

读取与写入时机由 `project-memory-records` 技能定义。

## 2026-07-30｜GitHub CLI 登录未配置 Git 推送凭据

- 现象：`gh auth status` 显示已登录，但 `git push` 因无法读取 GitHub 用户名而失败。
- 原因：全局 Git Credential Manager 覆盖了 GitHub CLI 的 URL 专用凭据助手。
- 防范规则：首次推送前先运行 `gh auth setup-git` 并验证 Git 凭据助手实际可用；若仍失败，在仓库本地将 `credential.helper` 覆盖为 GitHub CLI 助手后再推送。
- 关联改动：`chore: establish project directory structure`

## 2026-07-30｜改动记录误写入模板

- 现象：自动化工作流的实施与验证信息被写入改动记录模板，而不是对应日期的改动单元。
- 原因：补丁只匹配了通用字段名，未限定到目标日期标题后的区块。
- 防范规则：修改已有记录时先定位日期标题，并在写入后检查模板与目标单元是否分别保持正确内容。
- 关联改动：`🔧 配置：自动更新项目结构树`

## 2026-07-30｜推送 GitHub Actions 文件缺少 workflow 权限

- 现象：推送 `.github/workflows/` 时，GitHub 拒绝 OAuth 令牌创建或更新工作流。
- 原因：令牌具备 `repo` 权限，但缺少单独的 `workflow` 权限。
- 防范规则：首次提交 GitHub Actions 工作流前，运行 `gh auth refresh -h github.com -s workflow` 并完成授权。
- 关联改动：`🔧 配置：自动更新项目结构树`

## 2026-08-02｜仓库未配置 Git 作者身份

- 现象：执行 `git commit` 时提示无法自动检测作者姓名和邮箱。
- 原因：本仓库及全局 Git 配置均未设置 `user.name` 与 `user.email`。
- 防范规则：首次提交前检查本地 Git 作者配置；缺失时优先复用该仓库最近一次提交的作者身份，并只写入仓库本地配置。
- 关联改动：`📚 文档：归档MAX课程资源`

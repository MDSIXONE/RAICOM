# 代码改动记录

每个改动单元的状态只能使用“进行中”或“改动完成”。

## 模板：YYYY-MM-DD｜改动标题

- 状态：进行中
- 目标：
- 影响文件：
- 实施记录：
- 验证：
- 遗留风险：

读取与写入时机由 `project-memory-records` 技能定义。

## 2026-07-30｜GitHub Actions 自动更新项目结构树

- 状态：改动完成
- 目标：在目录结构变化后自动更新 README 中的项目结构树。
- 影响文件：`.github/workflows/`、`scripts/`、`README.md`、`.gitignore`
- 实施记录：新增 README 结构树生成脚本和 GitHub Actions 工作流；以唯一标记限定更新范围。
- 验证：脚本通过 Python 编译、重复运行幂等性、唯一标记、排除内部目录和 Git 差异检查。
- 遗留风险：仓库 Actions 设置必须允许 `GITHUB_TOKEN` 具有内容写入权限；当前本机 GitHub 登录令牌还需补充 `workflow` 权限才能推送工作流文件。

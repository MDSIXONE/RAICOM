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

## 2026-08-02｜设备源码含硬编码云服务凭据

- 现象：从机器狗上位机导入的三份云语音示例包含相同的硬编码 API 密钥。
- 原因：初始导入筛选只检查配置文件中的凭据字段，未扫描 Python 源码中的凭据字面量。
- 防范规则：导入第三方或设备源码前，除排除配置和密钥文件外，必须扫描全部文本源码中的 API 密钥、令牌和密码字面量；确认后先剔除或脱敏，再写入仓库。
- 关联改动：2026-08-02｜导入机器狗上位机源码

## 2026-08-02｜凭据扫描未覆盖多行与非 API_KEY 命名

- 现象：预推送复核在云语音示例中发现 Coze 令牌、Volcengine 令牌和应用标识；初次正则扫描未命中。
- 原因：初始规则只覆盖单行、特定变量名和长字符串的模式，未覆盖多行赋值及 `token`、`appid` 等命名组合。
- 防范规则：提交外部源码前，扫描必须覆盖多行赋值、服务商常见令牌命名和短应用标识；独立复核通过前不得推送。
- 关联改动：2026-08-02｜创建机器狗全量源码快照

## 2026-08-02｜Docker 29 镜像 ID 校验假设不成立

- 现象：使用 Docker 29 的 containerd 镜像存储时，`docker image inspect .Id` 返回 Registry 清单摘要，而非预期的传统镜像配置 ID，导致已成功拉取的 ARM64 ROS 镜像被误判为失败。
- 原因：沿用了旧版 Docker 对 `.Id` 含义的校验假设，未考虑 Docker 29 的 containerd snapshotter 行为。
- 防范规则：对新 Docker 版本校验镜像时，同时检查 `RepoDigests`、`Architecture`、运行时 `ROS_DISTRO` 和目标软件包版本；不要仅依赖 `.Id`。
- 关联改动：机器狗 Docker 与 ROS Noetic 容器部署

## 2026-08-02｜ROS Noetic 初始化脚本不兼容 Bash nounset

- 现象：以 `set -u` 执行 `source /opt/ros/noetic/setup.bash` 时，初始化脚本读取未设置的 `ROS_MASTER_URI` 并立即退出。
- 原因：Noetic 的 `roslaunch` shell 钩子假定未设置的环境变量可按空值读取，与 Bash `nounset` 语义不兼容。
- 防范规则：执行 ROS 环境初始化时不要启用 `set -u`；如需严格变量检查，应在 `source` 完成后对自有脚本范围启用。
- 关联改动：机器狗 ROS 功能包创建

## 2026-08-02｜ROS 基础镜像不提供 roslaunch-check

- 现象：在 `ros:noetic-ros-base-focal` 容器中执行 `roslaunch-check` 时提示命令不存在，尽管功能包已构建且实际 launch 测试成功。
- 原因：该校验工具不属于 ROS 基础镜像提供的命令集；此前将其误作 ROS Noetic 的通用内置命令。
- 防范规则：验证基础镜像中的 launch 文件时，优先执行实际的 `roslaunch` 和话题收发测试；若确需静态校验工具，先确认其所属软件包并显式安装或在开发镜像中使用。
- 关联改动：机器狗 ROS 功能包创建

## 2026-08-02｜ROS 工作区校验遗漏容器边界

- 现象：首次复验直接在 Debian 宿主机执行 ROS 初始化与 `rospack`，得到“`/opt/ros/noetic/setup.bash` 不存在”和命令不存在的结果。
- 原因：ROS Noetic 仅部署在 `ros-noetic` 容器中，宿主机只保存被挂载的工作区源码；验证命令遗漏了 `docker exec ros-noetic`。
- 防范规则：涉及 ROS 命令、`/opt/ros` 或 Catkin 构建产物的验证，先确认目标在宿主机还是容器；本设备应在容器内先 source ROS 基础环境和工作区 `devel/setup.bash`。
- 关联改动：机器狗 ROS 功能包创建

## 2026-08-02｜Catkin 链接不自动提供头文件路径

- 现象：雷达节点链接了 `${catkin_LIBRARIES}`，但编译时仍找不到 `ros/ros.h`。
- 原因：Catkin 的库变量不等同于编译目标的头文件搜索路径；节点目标遗漏了 `${catkin_INCLUDE_DIRS}`。
- 防范规则：为每个使用 ROS C++ 头文件的目标显式设置 `${catkin_INCLUDE_DIRS}`，并以实际 `catkin_make` 编译验证，而不是只审查链接声明。
- 关联改动：2026-08-02｜机器狗雷达启动探测

## 2026-08-02｜YDLIDAR SDK 命名空间与示例不一致

- 现象：按常见 API 写成 `ydlidar::CYdLidar` 和 `ydlidar::LaserScan` 后，设备随附 SDK 编译报类型不存在。
- 原因：当前 SDK 版本只将部分辅助函数置于 `ydlidar` 命名空间，核心类、扫描类型和参数枚举实际处于全局命名空间；厂商示例以 `using namespace ydlidar` 掩盖了这一差异。
- 防范规则：集成供应商 SDK 时以当前头文件和编译结果为准，不根据示例中的命名空间导入推断类型的完整限定名。
- 关联改动：2026-08-02｜机器狗雷达启动探测

## 2026-08-02｜雷达测试缺少端口与时间硬边界

- 现象：静态复核发现 launch 参数可把雷达端口改为底盘 `ttyAMA0`，且 10 秒限时使用 ROS 仿真时间时可能不会推进。
- 原因：将硬件安全边界设计成可覆盖的普通参数，并错误地把 ROS 时间当作物理测试时钟。
- 防范规则：对物理设备节点硬编码或严格白名单设备路径；限时硬件测试必须使用墙钟，并拒绝无效的负持续时间。
- 关联改动：2026-08-02｜机器狗雷达启动探测

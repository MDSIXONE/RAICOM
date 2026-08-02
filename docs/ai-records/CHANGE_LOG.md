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
- 验证：脚本通过 Python 编译、重复运行幂等性、唯一标记、排除内部目录和 Git 差异检查；GitHub Actions 首次运行成功。
- 遗留风险：仓库 Actions 设置必须持续允许 `GITHUB_TOKEN` 具有内容写入权限，自动提交才可在结构变化后推送。

## 2026-08-02｜导入机器狗上位机源码

- 状态：改动完成
- 目标：从机器狗上位机识别并导入可公开保存的源码到本仓库对应目录。
- 影响文件：`archive/preliminary-code/xgo-cm5/`、`archive/preliminary-code/oumax-xgo/`、`archive/preliminary-code/README.md`。
- 实施记录：从 `/home/pi/RaspberryPi-CM5/common/`、`robots/Dog_LM/` 与 `/home/pi/oumax-xgo/` 导入并复核；未导入 ROS 工作区，因为设备未安装 ROS 且远程不存在 ROS 包。初次筛选与预推送复核共剔除六份含硬编码云服务凭据的语音示例，并移除 IDE、打包和模型产物；最终快照为 274 个文件、约 2.9 MiB。
- 验证：逐文件大小校验和 Python 语法检查完成；二次凭据扫描无命中；未保留虚拟环境、构建目录、模型、密钥文件或长凭据字面量。
- 遗留风险：快照依赖设备上的专有运行时、模型与硬件接口，不能在当前 Windows 环境或未安装 ROS 的设备上直接构建运行。

## 2026-08-02｜创建机器狗全量源码快照

- 状态：改动完成
- 目标：在独立目录中保存机器狗的全部非系统用户/厂商/服务源码。
- 影响文件：`archive/full-device-source/`、`archive/full-device-source/SHA256SUMS.tsv`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：从 `/home/pi/` 导入所有可识别的应用与厂商源码，并导入 7 份引用这些程序的自定义 systemd 服务定义；经预推送复核后，完整筛选快照为 590 文件、6,529,017 字节。
- 验证：590 个清单条目的文件大小和 SHA-256 摘要全部一致；二次凭据字面量与敏感文件名扫描无命中；Python 源码语法解析通过。
- 遗留风险：自动剔除了 27 份含凭据的源码/配置、8 个超过 5 MiB 的文件、3,699 个非源码运行文件，以及打包元数据和模型文件。该目录不是整个 Debian 根文件系统，且依赖专有运行时、模型与硬件，不能在当前 Windows 环境直接运行。

## 2026-08-02｜创建机器狗 ROS 功能包

- 状态：改动完成
- 目标：在机器狗的 ROS Noetic Docker 工作区创建可构建的最小功能包，并同步至本仓库。
- 影响文件：`catkin_ws/src/CMakeLists.txt`、`catkin_ws/src/robot_dog_bringup/`、`robot-information/actual-hardware-observations.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：在机器狗的 `ros-noetic` 容器工作区创建 `robot_dog_bringup`，实现只读系统状态发布节点、launch 文件、构建规则、许可证与使用说明；将 6 个包源码文件按 SHA-256 一致性校验同步到本仓库。为本地检出提供可用的 Catkin 顶层 `CMakeLists.txt`，避免复制只能在容器内解析的绝对符号链接；同时更新部署后的存储、Docker、ROS 和功能包实机信息。
- 验证：容器内 `catkin_make` 构建成功；功能包依赖可解析；`roslaunch robot_dog_bringup robot_dog_bringup.launch` 已启动节点并在 `/robot_dog_bringup/status` 收到主机名、内核与 ROS 发行版状态消息；同步前后 6 个包源码文件的 SHA-256 摘要一致。
- 遗留风险：ROS Noetic 已结束常规支持，镜像基于 Ubuntu Focal；容器使用宿主网络与 IPC，后续接入不受信任的 ROS 节点前应限制 ROS 网络边界。功能包当前不含任何硬件控制逻辑。

## 2026-08-02｜机器狗雷达启动探测

- 状态：改动完成
- 目标：在不发送底盘、舵机或串口控制命令的前提下，为已确认的雷达驱动提供 ROS 启动与 `/scan` 数据验证入口。
- 影响文件：`catkin_ws/src/robot_dog_lidar/`、`robot-information/actual-hardware-observations.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：通过机器随附 SDK、CP2102 的 USB ID、厂商程序配置和设备返回信息确认 YDLIDAR Tmini Plus；新增 `robot_dog_lidar` C++ 节点，使用随附 SDK 的 Unix 源码在 Noetic 容器内构建，发布 `/scan`。容器仅映射当前雷达节点为 `/dev/ydlidar`，并只读挂载 SDK 源码；节点硬编码该容器路径，未映射或访问底盘 `ttyAMA0`，默认以墙钟限时 10 秒且退出时关闭雷达。
- 验证：容器内 `catkin_make` 成功构建供应商 SDK 静态库和节点；独立代码复核确认端口不可被 launch 覆盖、限时不受仿真时间影响；实机启动后收到有效 `sensor_msgs/LaserScan`，设备返回 Tmini Plus、230400、10 Hz，并在限时结束后记录“scanning has stopped”；测试结束后未发现残留 ROS 或雷达进程。
- 遗留风险：容器设备映射的宿主来源是当前 `/dev/ttyUSB0`；如 USB 枚举变化，节点会安全失败，但需在重新启动前重新确认稳定枚举名与映射。供应商 SDK 编译存在既有格式和宏重定义警告，当前构建与实测不受影响。

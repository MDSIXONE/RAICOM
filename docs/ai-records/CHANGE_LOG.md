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

## 2026-08-04｜带断链停止的连续键盘控制

- 状态：改动完成
- 目标：新增独立连续键盘模式：按住方向键持续刷新原厂幅值的前后/转向请求，停止刷新、节点异常或断链时自动停止；保留单点动模式。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_continuous.py,launch/physical_keyboard_continuous.launch,host/launch_physical_keyboard_continuous.sh,host/install_host_handover.sh,CMakeLists.txt,README.md}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：基于机器既有 `oumax-manual.service` UDP `gamepad` 接口（仅本机 `127.0.0.1:8766`）实现；该服务已提供 0.35 秒 UDP 看门狗。连续节点维持原厂默认前后 `17`、yaw `55`，以最多 10 Hz 的终端重复键刷新；本地无刷新 0.25 秒即连续发送三帧零命令，并保留 `u→y` 确认、空格/x/Ctrl-C 锁定停止和唯一串口服务切换。
- 验证：目标环境 Python 模拟验证前后归一化 `17/25=0.68`、yaw 归一化 `55/80=0.6875`、同方向 0.10 秒内限流、方向切换与三帧零停止；Python 语法、launch XML、宿主启动脚本语法、Git 空白检查、WSL `rospack find` 与 `roslaunch --nodes ... enable_motion:=false` 均通过。两次 WSL `catkin_make` 均卡在既有 CMake 构建系统检查并在 55 秒上限内超时，未进入本包编译；未连接、上传或启动机器狗。
- 遗留风险：普通 SSH 终端没有 key-up 事件；方向键释放后依赖客户端停止自动重复，少数终端可能在初始重复延迟期间动作不连续。若需要可靠“松键即停”，应另行采用宿主机 evdev 原始输入。连续控制会真实运动，部署后不得自动启动；首次必须在净空场地验证停止、本地超时、UDP 断链超时和实体急停。

## 2026-08-04｜键盘自动重复脉冲锁定

- 状态：改动完成
- 目标：防止终端键盘自动重复把单次 0.20 秒点动串联为连续运动；每次成功物理点动后自动重新锁定，下一次动作须再次 `u`、`y` 确认。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_teleop.py,README.md}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：实机日志显示按住 `w` 产生了多次约间隔 0.20 秒的 accepted pulse，现有计时器会被后续重复键取消，无法实现单次点动的预期边界。
- 验证：本地模拟覆盖 `u→y→w→重复 w`，确认仅一次运动请求和一次超时停止；模拟请求失败后确认程序锁定、发送停止且重复键不重试。Python 语法、WSL Catkin 构建和 Git 空白检查通过。用户要求部署后，机器端脚本已更新并在容器内重新构建、Python 语法和节点解析通过；上一版备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-single-pulse-lock`。未重启当时的旧键盘进程或发送新的运动命令。
- 遗留风险：当前运行中的旧键盘程序不具备自动重复锁定，须由用户 Ctrl-C 退出后才会加载新版本；重启后每次动作都需要 `u`、`y`、方向键，且首次强度为原厂默认幅值，必须在净空场地单次验证。

## 2026-08-04｜键盘原地转向独立标定

- 状态：改动完成
- 目标：将真实键盘控制的前后与原地转向强度分离，并复用原厂 Dog_LM 摇杆默认强度：前后 XGO 值 `17`、`a/d` XGO 值 `55`，参数上限保持在原厂摇杆范围（前后 `25`、yaw `70`），脉冲仍不超过 `0.20 s`。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_teleop.py,launch/physical_keyboard_teleop.launch,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：实机日志已确认 `a/d` 的 HTTP 请求正常到达 OUMAX 服务；随后按用户要求读取原厂 `dog_Joystick.py`：默认 `step_control=70`，前后映射为约 `17`，yaw 映射为约 `55`（上限 `100`）。原先的保守 yaw `16` 方案已弃用；新方案保留键盘程序的脉冲超时、急停和同进程确认保护。
- 验证：本地 Python 语法、launch XML、WSL Catkin 构建和物理 launch 节点解析通过；用户要求部署后，机器端脚本、launch 和说明已更新，上一版物理键盘脚本/launch 备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-original-values`，容器内 Catkin 构建、Python 语法和节点解析通过。未重启或改变当时运行中的旧实控进程，未发送新的运动命令。
- 遗留风险：新参数会使首次 `a/d` 实际转向更明显；当前运行中的旧实控进程不会热加载新参数，须由用户主动退出并重新启动。重启后必须在净空场地单次验证方向；前后/yaw 值只是复刻原厂默认幅值，不是完整复刻原厂持续摇杆的时间行为，也不是 m/s 或 rad/s。

## 2026-08-04｜手控服务就绪等待修复

- 状态：改动完成
- 目标：修复控制权接管脚本在 OUMAX 服务刚被 systemd 启动时立即探测健康接口、误判服务失败并回滚的问题；只增加有限就绪等待，不改变运动接口。
- 影响文件：`catkin_ws/src/robot_dog_teleop/host/raicom-control-handover`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：实机复现显示 `oumax-manual.service` 从启动到监听 `127.0.0.1:8765` 存在约 1 秒初始化窗口；当前脚本在 systemd active 后立即 `curl`，触发安全回滚。新增总时限约 5 秒、每 0.2 秒一次的只读 `/health` 重试，并校验 `ok`、串口和端口身份；超时/服务退出时先停止手控服务、等待串口释放，才恢复原厂 UI。回滚后原厂 UI 已恢复、OUMAX 服务已停止、未发送运动命令。
- 验证：Bash 语法与 Git 空白检查通过；mock `systemctl`、`fuser`、`curl` 验证前五次健康检查失败、第六次返回正确身份时仍能获得控制权，并在 release 后恢复原厂 UI。用户授权修复后，已上传至机器工作区和 `/usr/local/sbin/raicom-control-handover`，旧帮助程序备份为 `/usr/local/sbin/raicom-control-handover.20260804-readiness.bak`；实机只读回归成功完成“原厂 UI 停止 → OUMAX 服务监听并返回正确 `/health` → 原厂 UI 恢复”，两端服务状态均正确，未启动键盘节点、未调用 `/command` 或发送运动命令。
- 遗留风险：不得在修复验证时启动物理键盘节点或调用 `/command`；仅允许检查 `/health`。

## 2026-08-03｜机器狗键盘控制权自动切换

- 状态：改动完成
- 目标：在宿主机上将原厂 `common/main.py` 迁移为可控服务；真实键盘控制启动时临时停止原厂程序并启用 OUMAX 手动服务，退出时恢复原厂程序。当前只在本地编写，不上传、不运行。
- 影响文件：`catkin_ws/src/robot_dog_teleop/host/`、`catkin_ws/src/robot_dog_teleop/README.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：开始前已确认现机原厂程序由 `/etc/rc.local` 启动且持有 `/dev/ttyAMA0`；OUMAX 服务已收紧为仅本机监听。新增可控的原厂 UI systemd 单元、控制权 acquire/release 帮助程序、交互键盘启动包装器和显式 `--cutover` 安装脚本。它只替换经精确核验的 `rc.local` 原厂启动行并保留备份，拒绝 raw/其他手控服务并在任一接管失败时恢复原厂 UI；不会重新执行包含网络清理逻辑的整个 `rc.local`。
- 验证：三个 Bash 脚本的 `bash -n` 通过；在 WSL 以 mock `systemctl`、`fuser`、`curl` 验证 acquire 后原厂服务变为停止且 OUMAX 服务变为运行、release 后顺序反转；Git 空白检查通过。用户要求上传后，新包已同步到机器 `/home/pi/ros_ws/src/robot_dog_teleop`，旧版已备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-control-handover`；容器内 Catkin 构建、两个键盘 launch 节点解析、Python/launch XML 和三个宿主机脚本语法检查通过。未执行安装脚本、未停止原厂程序、未启动实控节点或发送运动命令。
- 遗留风险：部署前必须复核 `rc.local` 启动行仍与安装脚本一致，并确认没有外部路径重启 `common/main.py`。真实串口接管与首次点动仍须在用户确认电量、急停和场地条件后进行。

## 2026-08-03｜机器狗官方手动控制桥接

- 状态：改动完成
- 目标：在不抢占底盘串口的前提下，将已确认的键盘请求话题受控转发给机器现有的 OUMAX 手动控制服务，实现真实键盘点动的可部署实现；默认禁止实际运动。
- 影响文件：`catkin_ws/src/robot_dog_teleop/`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`；机器端 `ros-noetic` 容器与既有 `oumax-manual.service`。
- 实施记录：开始前确认宿主机 `oumax-manual.service` 正在独占 `/dev/ttyAMA0`，并在 `127.0.0.1:8765` 提供 `/health` 与 `/command` 接口；容器可访问健康接口。最终实现为同一进程内的 `physical_keyboard_teleop.py`：它不打开串口、也不订阅 ROS 速度话题，仅在键盘本地 `u`、`y` 双确认后调用该唯一服务。仅允许前后和原地转向，XGO 指令值硬限为 `1..8`、脉冲硬限为 `0.05..0.20 s`；零命令、超时、异常和退出均请求停止。取消了会被 ROS 话题绕过的独立 bridge，并以脉冲 ID 消除旧定时器对新命令的竞态。
- 验证：本地 WSL Catkin 构建、Python 语法、launch XML 和物理 launch 节点解析通过；机器容器内 `catkin_make`、包解析、物理 launch 节点解析、Python 语法和 XML 解析通过。新包已上传，上一版保留在 `/home/pi/ros_ws/backups/robot_dog_teleop-20260803-physical-keyboard`；在用户授权后，机器端手动服务源码已备份为 `/home/pi/oumax-xgo/manual_control_server.py.20260803-localhost.bak`，并收紧为仅监听 `127.0.0.1:8765/8766`，LAN 地址探测失败、容器健康探测成功；未启动物理控制 launch、未发送 HTTP 控制请求、未发送底盘命令。
- 遗留风险：首次真实运动尚未获现场安全确认。`/etc/rc.local` 自动启动的原厂 `common/main.py` 当前仍持有 `/dev/ttyAMA0`，不能与 OUMAX 手动服务并行使用；且应用日志显示电量为 9，须先充电。未经用户明确同意停止/替换原厂主程序、确认唯一串口持有者、急停/断电可达、站稳姿态，以及在 1 m 净空内验证首次单脉冲方向与停止行为，不得启动物理控制。

## 2026-08-03｜机器狗投影尺寸与键盘点动控制

- 状态：改动完成
- 目标：将 RViz 矩形替身及规划足迹调整为长 0.27 m、宽 0.16 m；新增默认锁定、明确确认后才可发出短时速度脉冲的键盘控制程序。实现阶段不部署或移动；后续已在机器开机后完成上传与静态核验。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`catkin_ws/src/robot_dog_teleop/`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：矩形 Marker 与 footprint 已同步为长 0.27 m、宽 0.16 m；新增独立 `robot_dog_teleop` 包，默认只发布 `/robot_dog_teleop/requested_cmd`，不发布 `/cmd_vel`、不访问串口。程序默认锁定，按 `u` 后 5 秒内按 `y` 才解锁；`w/s/a/d` 每次仅请求 0.20 秒脉冲，空格、`x`、Ctrl-C 和退出均归零并锁定。
- 验证：WSL Catkin 构建通过并识别 `robot_dog_teleop`；Python、launch XML、Bash 和 Git 空白检查通过；本地离线节点实测 Marker 是 `base_link` 下的 CUBE，`scale.x=0.27`、`scale.y=0.16`，局部 costmap 已发布；从 `(-0.70, 1.00)` 到 `(0.40, -0.75)` 的全局路径服务仍能到达目标点。机器开机后已同步到 `/home/pi/ros_ws/src/`，容器内 Catkin 编译、包解析、launch 节点解析、Python 语法和 0.27×0.16 足迹/隔离话题检查通过；未启动节点、未解锁、未发送任何硬件命令。
- 遗留风险：当前没有经确认的 ROS 底盘 bridge；键盘程序仅完成干运行请求链路。实机底盘速度接口及安全现场条件尚未验证；不得在未经用户再次确认、机器固定检查和紧急停止准备前部署或解锁运动。

## 2026-08-03｜实机 ROS 导航可视化部署

- 状态：进行中
- 目标：将 RICAM 地图与导航可视化包部署至机器狗 ROS Noetic 容器，使本地 RViz 可显示正确起点、0.30 m × 0.25 m 矩形、全局/1 m × 1 m 局部代价地图和实时雷达点云；不发送底盘速度指令。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/start_robot_rviz.sh`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`；机器端 `/home/pi/ros_ws/src/robot_dog_navigation/` 与 `ros-noetic` 容器。
- 实施记录：全局和局部 costmap 参数已独立，膨胀半径均为 0.10 m；局部窗口改为 1 m × 1 m、0.01 m。新增从真实 `/scan` 实时转换 `/lidar_points` 和矩形 Marker 的只读节点、实机 launch 及本地 RViz 连接脚本；`move_base` 的速度输出重映射到无订阅者的隔离话题。机器端旧导航包已备份至 `/home/pi/ros_ws/backups/robot_dog_navigation-20260803-ricam-visualization`，新包已上传并在容器内构建；容器 Ubuntu 源切换至阿里云 ports 镜像，已安装 navigation、map-server 和 tf2-ros。
- 验证：机器端实测 RICAM 地图为 300 × 250、0.01 m、原点 `(-1.5, -1.25)`；起点 TF 为 `(-0.70, 1.00)`；Marker 为 `0.30 m × 0.25 m`；全局/局部膨胀均为 0.1，局部宽高均为 1.0；真实 `/scan` 与 `/lidar_points` 均约 10 Hz，两个 costmap 话题均已发布，隔离速度话题没有订阅者。机器端已看见本机 RViz 注册为地图、点云和两张代价地图的订阅者。
- 遗留风险：已确认机器狗无法连接本机 WSL 的 RViz 动态 TCPROS/XMLRPC 端口，当前无法完成实际数据传输与目标点回传；Windows 防火墙规则创建需要管理员权限。绝不启动底盘控制节点。

## 2026-08-03｜离线定点任务切换至 RICAM 场地地图

- 状态：改动完成
- 目标：将最新版仿真 `ricam_arena` 的 3.0 m × 2.5 m 栅格地图作为本地 `robot_dog_navigation` 定点任务的默认地图；暂不上传机器狗。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/{setup_offline_navigation,start_local_rosmaster,start_offline_navigation,verify_offline_navigation}.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：将 `ricam_arena.pgm` 复制到导航包内并新增配套 YAML，默认 launch 切换至该地图；规划 footprint 统一为长 0.30 m、宽 0.25 m，附加 0.01 m 边界；安全起点设为 `(-0.70, 1.00)`，模拟雷达保留给 RViz 显示但不参与障碍层。
- 验证：地图源与导航包副本 SHA-256 均为 `F0336D936FA407548130CC6E3EBE253D7B10AD91438DEF02D57B171C6BB31488`；本地 launch 实测 `/map` 为 300 × 250、0.01 m、原点 `(-1.5, -1.25)`，全局代价地图分辨率为 0.01 m、障碍层为 `false`；`move_base/make_plan` 从 `(-0.70, 1.00)` 到 `(0.40, -0.75)` 成功生成并精确结束于目标点；YAML、launch XML、Python 和全部 WSL Bash 脚本语法检查，以及 Git 空白检查均通过。
- 遗留风险：场地地图仅用于当前离线定点验证，尚未与真实雷达、机器人坐标系或实际安全边界标定；本次没有连接或上传机器狗。

## 2026-08-03｜RViz 矩形机器狗替身

- 状态：改动完成
- 目标：在本地离线 RViz 中以长 0.30 m、宽 0.25 m 的矩形可视化标记代替缺失的机器狗 URDF 模型。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：模拟雷达节点新增本地 `visualization_msgs/Marker` 发布器，在 `base_link` 下发布蓝色 `CUBE` 作为机器人矩形替身；默认长 0.30 m、宽 0.25 m、高 0.10 m，均可由 launch 参数调整。RViz 默认配置新增 Marker 显示，自动验证增加 Marker 话题与长宽断言；全程未修改或访问机器狗硬件。
- 验证：本机 Noetic 已解析 `visualization_msgs`；节点语法、Bash 语法与 Git 空白检查通过。已重启本地离线 launch，实测 `/robot_body_marker` 为 `visualization_msgs/Marker`，`base_link`、`CUBE`、`scale.x=0.3`、`scale.y=0.25`、`scale.z=0.1` 均正确，且 `/rviz` 已订阅该话题。
- 遗留风险：尺寸按用户给出的长 30、宽 25 解释为常用机器人单位厘米，即 0.30 m × 0.25 m；当前规划 `footprint` 比视觉矩形宽，后续接入真实机器人前应单独依据实测尺寸统一规划碰撞边界。

## 2026-08-03｜本地离线全局规划与 RViz 场景

- 状态：改动完成
- 目标：在本机 WSL 的独立 ROS Noetic Master 中接入官方 `global_planner/GlobalPlanner`，提供离线地图、模拟雷达点云、全局代价地图和 RViz 默认视图；不连接或改动机器狗的 ROS Master。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`blender-maps/`、`wsl-simulation/`、`README.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：新增离线导航功能包，使用官方 `move_base + global_planner/GlobalPlanner`、`map_server`、模拟 `/scan` 与 `/lidar_points`、静态 `map → odom → base_link → laser_frame` TF 和默认 RViz 配置；新增匹配的 `PGM + YAML` 栅格地图及可再生成的 Blender 场景脚本。WSL 脚本在 `~/raicom_ws` 的 ext4 文件系统构建，并固定 `ROS_MASTER_URI`、`ROS_IP` 和 `ROS_LOCALHOST_ONLY` 为回环地址；实机 `robot_dog_lidar` 包在本地构建中被黑名单排除。
- 验证：`catkin_make -DCATKIN_BLACKLIST_PACKAGES=robot_dog_lidar` 构建成功；无界面验证确认 `/map`、`/scan`、`/lidar_points`、`/move_base/global_costmap/costmap` 和官方全局路径均可收到；`RAICOM_VERIFY_RVIZ=1 bash wsl-simulation/verify_offline_navigation.sh` 进一步确认 WSLg RViz 配置可随离线 launch 启动。
- 遗留风险：D 盘剩余空间约 9.8 GiB；当前未找到 Blender 可执行文件，仓库保存的是可生成 `.blend` 的脚本而非二进制场景。地图、TF 和雷达数据均为离线模拟，接入真实传感器、定位或底盘前仍需单独设计安全边界与验证。

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

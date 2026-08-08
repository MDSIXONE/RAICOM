# 犯错记录

此文档保存已经确认、可帮助后续工作避免重复的错误与教训。

## 2026-08-08｜gmapping 用 tf1 不读 /tf_static，静态 TF 发布者导致建图只有首图

- 现象：实机 gmapping 启动后 /map 只有一张首图（latching 重放）且从不更新；DEBUG 日志每帧 `Message ready ... processing scan` 后紧跟 `cannot process scan`（addScan 返回 false，无任何 WARN）。
- 原因：`base_link→laser_frame` 用 `static_transform_publisher` 发布到 `/tf_static`；**gmapping 使用 tf1（tf::TransformListener）不订阅 /tf_static**（nav 栈 move_base/costmap 用 tf2 所以正常）→ initMapper 的 laser 变换查询失败 → got_first_scan_ 恒 false → 每帧 addScan 失败。本地对照实验（静态 TF → extrapolation 报错；改为动态 TF 后 processing/cannot=156/122 且 "Updated the map" 持续出现）实锤。
- 防范规则：给 gmapping 供 TF 必须用动态发布（本项目 `laser_frame_tf.py` 每 10Hz 发 /tf）；排查"有数据源但不出图"时先确认数据消费方的 TF 机制（tf1 vs tf2）；其余次要因素：scan.header.stamp 需回拨（如 now-0.2s）避免 extrapolation；静止不触发 openslam 运动阈值（linearUpdate/angularUpdate），建图必须移动。
- 关联改动：2026-08-08｜gmapping 键盘建图与实机地图切换

## 2026-08-08｜simple_odom 位移限幅按低速设计，foot 步速超限导致位置静默不更新

- 现象：rviz 车体原地旋转但位置不动（用户：现实中机器动了）；odom x/y 恒为初始值。
- 原因：`d_max=0.02m/帧` 按 ≤0.2m/s 设计（0.02 ÷ 0.1s），foot 实际步速 0.3~0.8m/s × 0.1s = 0.03~0.08m/帧 → 每帧位移超限被清零；yaw 走 IMU 直读不受影响 → 只转不走。
- 防范规则：位移/速度限幅必须按实测运动能力设计（本次 0.02→0.10，上限 1.0m/s @ 10Hz）；"位置不动但朝向在动"优先怀疑 x/y 通道被滤波/限幅清零。
- 关联改动：2026-08-08｜gmapping 键盘建图与实机地图切换

## 2026-08-08｜ros-noetic-slam-gmapping 是空 wrapper，可执行文件在 gmapping 包

- 现象：roslaunch 报 `cannot launch node of type [slam_gmapping/slam_gmapping]`。
- 原因：`ros-noetic-slam-gmapping` 只含 package.xml；可执行文件在 `/opt/ros/noetic/lib/gmapping/slam_gmapping`（`dpkg -L ros-noetic-gmapping` 确认）。
- 防范规则：launch 节点必须写 `pkg="gmapping" type="slam_gmapping"`；报 "cannot launch node of type" 时用 `dpkg -L` 查可执行文件实际所在包。
- 关联改动：2026-08-08｜gmapping 键盘建图与实机地图切换

## 2026-08-08｜WSLg 窗口 COPY MODE：fstab 自动挂载是概率性方案

- 现象：本地 rviz 窗口在 Windows 桌面不可见（标题带 `[WARN:COPY MODE]`）；`/mnt/wslg/weston.log` 出现 `rdp_allocate_shared_memory: Failed to open "/mnt/shared_memory/{GUID}" with error: Input/output error`。
- 原因：WSL 2.7.11 / WSLg 1.0.73.2 回归（microsoft/wslg #1456），weston 启动时 `/mnt/shared_memory` 挂载未就绪；用户发行版 `/etc/fstab` 的 automount 与 WSLg 启动存在竞态——即使 `mount` 显示 tmpfs 已挂载，weston 仍可能在竞态窗口内打开失败（首次修复成功，WSL 重启后复发）。
- 防范规则：改用 `/etc/wsl.conf [boot] command=/root/fix_shm.sh`（root 早期执行 `mkdir -p /mnt/shared_memory; mountpoint -q /mnt/shared_memory || mount -t tmpfs tmpfs /mnt/shared_memory`）确定性预挂载；WSL 重启后必须检查 `grep -c "rdp_allocate_shared_memory: Failed" /mnt/wslg/weston.log` 为 0（`enable_copy_warning_title` 标记残留无碍，以 allocate 失败计数为准）。
- 关联改动：2026-08-08｜主流程集成（本地控制台与 rviz 显示）

## 2026-08-08｜pkill -f 会匹配到 SSH 会话自身的命令行

- 现象：通过 SSH 执行 `pkill -f roslaunch` 后后续命令全部未执行（会话被自己杀掉），表现为 docker exec -d 启动失败、无输出。
- 原因：SSH 会话的 `bash -c` 命令行本身包含 "roslaunch" 字样，`pkill -f` 按完整命令行匹配，杀死了自己。
- 防范规则：对通过 SSH/容器远程执行的进程做 pkill 时使用方括号技巧（`pkill -f "roslaunch[ ]robot_dog_main"`、`pkill -f "[m]ove_base"`）；`pkill -x` 对 python 进程无效（comm 是 python3）。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜C++ 节点不自动重连 master，且重复 roslaunch 造成双实例

- 现象：本地 master 重启后，容器内 C++ 节点（move_base 等）停留在等待/注册态，话题仍在列表但无发布者；再次执行 roslaunch 后容器内出现多个 move_base 进程（实测 2~3 个），新旧实例抢占订阅。
- 原因：ROS 1 C++ 节点 master 掉线后不会自动重连（python 节点可能重连）；roslaunch 无 respawn，进程残留；未先清理旧 roslaunch 就再启动。
- 防范规则：master 重启后必须重启实机 roslaunch；重启前先 `pkill -f "roslaunch[ ]robot_dog_main"` 并确认 `ps aux | grep [m]ove_base | wc -l` 为 0；用 XMLRPC `getSystemState` 而非 `rostopic list` 判断节点是否在线（话题注册 ≠ 有发布者）。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜导航 goal 超出地图边界导致规划永远失败

- 现象：move_base 收到 goal 后无任何执行（日志 `The goal sent to the global planner is off the global costmap. Planning will always fail to this goal.`）；容器内/本地发 goal 只看到旧 goal 的 status 4（ABORTED）重播。
- 原因：ricam_arena 地图范围 x∈[-1.5,1.5]、y∈[-1.25,1.25]，测试 goal (-0.70,1.30)/(-0.70,1.50) 的 y 超出地图上界 1.25 → 全局规划永远失败。
- 防范规则：发 goal 前确认目标点在地图边界内；区分新旧 goal 看 status 时以 goal_id 为准（move_base 会给新订阅者重播旧 goal 的最终状态）。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜雷达遮挡滤波不要凭猜测改方向，先实测遮挡范围

- 现象：用户判断"雷达可能装反了"，把 scan_circle_filter 圆心改到后方（center_x=-0.15）后滤波无效果；实测 /scan 数据才知机械臂实际位于雷达正前方 ±18°、r=0.08-0.10 m（雷达并未装反）。
- 原因：凭视觉猜测滤波方向，未先分析真实 /scan 的距离-角度分布。
- 防范规则：滤波/标定类参数改动前，先 dump 实际 /scan 数据（按 range/angle 统计）定位遮挡体位置；当前有效方案为扇形滤波 `sector_center_deg=0`、`sector_half_width_deg=20`、`sector_max_range=1.0`。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜WSL 局域网 IP 由 DHCP 动态分配，跨机器 ROS 联调须先确认

- 现象：WSL/Windows（mirrored 模式共享 IP）重启后 IP 从 192.168.137.41 变为 192.168.137.232，master 进程存活但 `rostopic list` 报 `Unable to communicate with master!`。
- 原因：DHCP 重新分配；本地脚本与实机 launch 中硬编码旧 IP。
- 防范规则：跨机器联调前先确认当前 IP；start_local_control.sh 支持 `RAICOM_LOCAL_IP` 覆盖；实机启动命令的 `ROS_MASTER_URI` 同步更新（当前 192.168.137.232:11311）。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜XGO 固件运动步进死区：yaw 小于 12 的动作不执行

- 现象：桥接持续刷新 yaw=10 时机器完全不转向（delta 0°），而 curl 单发 yaw=30/1.0s 转向 31.62°。
- 原因：XGO 固件 VYAW/VX 是"动作触发"命令且存在步进死区（<12 不动）；runtime=0 的瞬时命令≈不动；turn(value, runtime>0) 的服务端 sleep 导致请求响应 ~0.26s 超过桥接 timeout 0.25s。
- 防范规则：桥接步进必须避开死区（`_scale_step` 线性映射 min_step=15）；服务端改用 Timer 看门狗（命令立即返回，runtime 后自动发停）替代 sleep；运动参数标定一律用持续刷新 + IMU yaw 实测验证。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜机器驱动布局不对称：仅左侧两轮有驱动，wheel 模式转向打滑不可用

- 现象：wheel4 模式（麦克纳姆/差速公式）转向均无效（1-3°/s 打滑），机器表现为平移而非旋转；逐轮驱动诊断 wheel0(lf)=+0.85°、wheel1(rf)=0°、wheel2(lr)=+14.26°、wheel3(rr)=0°——只有左侧两轮（lf、lr）可驱动，右侧 rf/rr 是无刷被动轮。
- 原因：默认假设麦克纳姆四轮对称驱动；实际该机型轮足款直驱轮无滚子，右侧两轮无驱动电机，任何四轮混合公式在直轮+非对称驱动下都退化为打滑平移。
- 防范规则：运动模式标定前先逐轮单驱诊断（kind=wheel speeds=[s,0,0,0] 逐个测 IMU delta）；wheel 模式不可用时切换 foot（dog）模式——站立、行走、转身可用（yaw=15→21°/s、30→36°/s），机器人导航走 foot 模式。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-08｜容器内 C++ 节点 __log 日志文件缺失

- 现象：`/root/.ros/log/<run_id>/` 只有 python 节点的日志，move_base-9.log / map_server-1.log 等 C++ 节点日志文件不存在。
- 原因：疑似 log4cxx 日志文件创建失败（不影响节点功能，move_base 正常运行）。
- 防范规则：排障 C++ 节点时不要依赖 __log 文件，改用 roslaunch 的 stdout 重定向（/tmp/main_launch.log，中文乱码用 `grep -a` + `sed "s/\x1b\[[0-9;]*m//g"` 剥 ANSI）或 XMLRPC/rosnode info 直接诊断。
- 关联改动：2026-08-08｜主流程集成

## 2026-08-07｜数据集通配符包含诊断图片

- 现象：第一次生成 YOLO 数据集时按 `*.jpg` 扫描，结果把本次生成的诊断拼图也当成第 601 张原始图片。
- 原因：诊断文件与采集图片位于同一目录，且文件名没有使用原始采集文件的 `capture_` 前缀约束。
- 防范规则：处理采集数据时使用精确文件名模式（本次为 `capture_*.jpg`），并在生成前后校验原始文件数量与命名集合。
- 关联改动：2026-08-07｜RICAM 红蓝绿球 YOLO 数据集

## 2026-08-05｜raw 模式下 Ctrl-C 不产生 SIGINT

- 现象：`tty.setraw()` 的键盘控制进程按 Ctrl-C 只停止运动，进程无法从键盘退出，用户只能另开终端 kill。
- 原因：raw 模式关闭 ISIG，Ctrl-C 不再产生 SIGINT，而是作为字节 `\x03` 进入输入流；`\x03` 分支只做了锁定停止，主循环没有退出路径。
- 防范规则：使用 `tty.setraw()` 的交互程序必须显式处理 `\x03` 并设计退出路径（本仓库约定：第一次 Ctrl-C 急停锁定、第二次退出）；不要把“停止运动”当作“退出进程”。
- 关联改动：2026-08-05｜键盘 Ctrl-C 双次退出修复

## 2026-08-05｜PowerShell 远程部署命令的变量转义不能依赖嵌套引号

- 现象：部署时用于移动机器端旧导航包的远程备份命令因 PowerShell、SSH 与 Bash 的多层变量转义失败，备份没有执行，但后续上传已覆盖目标目录。
- 原因：在 PowerShell 双引号字符串中传递 Bash 的 `$backup` 变量，产生了不完整的远程 shell 语法；未把“备份成功”作为上传前的独立确认点。
- 防范规则：远程部署应把备份、上传和验证拆成独立命令；使用已解析的固定绝对路径或单引号传递远程 Bash，且只有确认备份目录存在后才允许覆盖上传。
- 关联改动：2026-08-05｜接入独立发布版 CymPlanner 局部规划器

## 2026-08-05｜新增 Catkin 包目录遗漏 src 层级

- 现象：首次创建的 `robot_dog_yolo_dataset` 位于 `catkin_ws/`，不会被 Catkin 顶层工作空间扫描。
- 原因：创建文件时未遵循仓库规定的 `catkin_ws/src/` 功能包根目录。
- 防范规则：新增 ROS 功能包前先确认 Catkin 顶层 `src/CMakeLists.txt` 与仓库目录约定，并仅在 `catkin_ws/src/` 下创建包目录。
- 关联改动：2026-08-05｜YOLO 相机训练集采集功能包

## 模板：YYYY-MM-DD｜简短标题

- 现象：
- 原因：
- 防范规则：
- 关联改动：

读取与写入时机由 `project-memory-records` 技能定义。

## 2026-08-04｜普通 SSH 终端不能直接报告按键松开

- 现象：连续键盘控制若把“松键”视为可直接捕获的事件，会承诺一个普通 SSH 终端实际无法提供的停止信号。
- 原因：标准终端输入只传递字符流；按住键产生的自动重复与松开后停止重复由客户端系统决定，不含 key-up 事件。
- 防范规则：连续控制须明确表述为“重复键刷新 + 短超时停止”，限流刷新频率，且独立发送多帧零命令；如需可靠 key-up 语义，后续应采用宿主机 evdev 等原始输入方案。
- 关联改动：2026-08-04｜带断链停止的连续键盘控制

## 2026-08-04｜前后与原地转向不能共用未经标定的 XGO 强度

- 现象：实机日志确认键盘 `a/d` 已发送并被 OUMAX 服务以 HTTP 200 接收，但在 XGO 值 `8`、0.20 秒脉冲下没有可见原地转向；厂商示例的四足转向通常使用约 `16–18`。
- 原因：将低速前后点动的保守值直接复用于 yaw，忽略四足转向所需的独立幅值与时间标定。
- 防范规则：前后与 yaw 必须采用独立且受上限保护的参数；首次调整只在净空场地进行单次转向点动，确认方向和停止行为后再设为默认值。
- 关联改动：2026-08-03｜机器狗官方手动控制桥接

## 2026-08-04｜systemd active 不代表控制服务已经可连接

- 现象：控制权切换中，`oumax-manual.service` 已显示 active，但本机 `127.0.0.1:8765/health` 尚未监听，立即健康检查失败并触发安全回滚。
- 原因：Python 服务进程与 systemd active 状态先于 socket bind；此前将进程存在误当作应用层已经就绪。
- 防范规则：接管控制权后，对只读健康接口执行有上限的就绪重试，并验证返回身份；超时后先停止新服务并确认串口释放，才恢复旧控制程序。
- 关联改动：2026-08-04｜手控服务就绪等待修复

## 2026-08-03｜监听控制端口不等于拥有底盘串口

- 现象：`oumax-manual.service` 虽已正常监听本机控制端口，但 `/dev/ttyAMA0` 实际被 `/etc/rc.local` 自动启动的原厂 `common/main.py` 持有。
- 原因：手动服务延迟打开 XGO 串口；仅检查服务状态或 HTTP 健康响应，无法证明其拥有唯一底盘控制权。
- 防范规则：首次真实控制前必须同时检查控制服务监听、`fuser /dev/ttyAMA0` 的唯一进程、自动启动链路和当前电量；发现原厂进程占用时，先取得停止/替换该进程的明确授权并设计可恢复的启动方式。
- 关联改动：2026-08-03｜机器狗官方手动控制桥接

## 2026-08-03｜ROS 速度话题不能作为真实运动授权边界

- 现象：独立 bridge 即使要求键盘 `u`、`y` 解锁，任何接入同一 ROS Master 的节点仍可向它订阅的话题发布速度消息，绕过该确认；另有先设停止定时器、后发送 HTTP 运动请求的竞态，网络延迟时可能形成“先停止、后运动”。
- 原因：ROS 1 话题没有发布者身份验证，且异步网络请求与计时器未按服务端确认顺序串联。
- 防范规则：真实键盘点动的授权和硬件转发应位于同一进程，不通过公共 ROS 速度话题传递；只有在运动服务确认请求后才启动本地停止计时器，并以脉冲 ID 使过期计时器失效。
- 关联改动：2026-08-03｜机器狗官方手动控制桥接

## 2026-08-03｜未验证的底盘接口不能接收键盘速度

- 现象：导航 launch 已将 `/cmd_vel` 隔离，设备归档中仅找到会直接访问 `ttyAMA0` 的非 ROS 控制代码，未找到经验证的 ROS 底盘 bridge。
- 原因：把“能发布 `Twist`”误当作“已知安全的机器狗运动接口”，会绕过底盘协议、唯一控制权和紧急停止验证。
- 防范规则：键盘控制在确认官方/现有底盘接口、设备协议、单一控制权和现场急停前，只能发布隔离的 dry-run 请求话题；不得重映射到 `/cmd_vel` 或串口。
- 关联改动：2026-08-03｜机器狗投影尺寸与键盘点动控制

## 2026-08-03｜ROS 1 跨机器可视化不能只开放 Master 端口

- 现象：机器狗 Master 已显示本机 RViz 的订阅注册，但机器狗无法连接 WSL RViz 的动态 TCP 端口，地图、点云和本机发布的目标点都不能实际传输。
- 原因：ROS 1 的 XMLRPC/TCPROS 节点使用动态回连端口；仅连通 `11311` 或完成注册不足以建立发布者与订阅者的数据连接，Windows 防火墙拦截了机器人到 WSL 的入站 TCP。
- 防范规则：跨机器运行 ROS 1 前，从远端实际测试本地 RViz/节点监听端口；仅为机器人 IP 和 WSL 局域网 IP 添加 TCP 入站允许规则，随后以实时话题与定点路径双向验证。
- 关联改动：2026-08-03｜实机 ROS 导航可视化部署

## 2026-08-03｜WSL 启动脚本必须使用 LF 换行

- 现象：`verify_offline_navigation.sh` 在 WSL 中执行 `bash -n` 时，在函数定义处报 `$'\r'` 语法错误。
- 原因：脚本以 Windows CRLF 保存，Bash 将行尾回车作为语法字符处理。
- 防范规则：新增或编辑供 WSL 执行的 `.sh` 文件后，统一转换为 LF，并在 WSL 内运行 `bash -n` 覆盖全部启动与验证脚本。
- 关联改动：2026-08-03｜离线定点任务切换至 RICAM 场地地图

## 2026-08-03｜RViz Marker 显示使用专用话题字段

- 现象：矩形 Marker 已在 `/robot_body_marker` 发布，但 RViz 没有订阅该话题，因而不显示模型。
- 原因：将通用显示项的 `Topic` 字段用于 `rviz/Marker`；该显示项实际读取的是 `Marker Topic`。
- 防范规则：修改 RViz 配置后，除验证话题发布外，还要运行 `rostopic info` 确认 `/rviz` 已成为预期话题的订阅者。
- 关联改动：2026-08-03｜RViz 矩形机器狗替身

## 2026-08-03｜PowerShell 管道向 WSL 传入 Bash 脚本携带 CRLF

- 现象：通过 PowerShell 多行字符串管道传给 `wsl ... bash -s` 时，脚本路径末尾携带 `\r`，Bash 报 `No such file or directory`，尽管文件实际存在。
- 原因：PowerShell 文本管道按 Windows CRLF 传输，Linux Bash 将回车保留在未做规范化的命令参数中。
- 防范规则：WSL 验证优先直接执行仓库中的 Bash 文件（`wsl ... bash -lc "... && bash script.sh"`）；只有明确转换为 LF 后才向 `bash -s` 传送多行文本。
- 关联改动：2026-08-03｜本地离线全局规划与 RViz 场景

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

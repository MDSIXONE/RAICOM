# 项目黑话词典（project-lingo）

用户常以口语化短句下达操作指令。本文件存放词条正文；触发入口与维护规则见
`.agents/skills/project-lingo/SKILL.md`。

## 高频索引

| 黑话 | 一句话含义 | 词条 |
| --- | --- | --- |
| 机器IP / IP未变 | 机器狗当前 WiFi 下的 IP 与访问入口（192.168.137.157） | [#机器IP](#机器IP) |
| 驱动左后轮转动 N 秒 | 对左后轮通道（索引 3）发送持续单轮轮控命令，并在时长结束后归零 | [#驱动左后轮转动-n-秒](#驱动左后轮转动-n-秒) |
| 同时驱动 4 个轮子 | 四个轮子同时同速转动指定时长，用于验证四轮驱动/前进能力 | [#同时驱动-4-个轮子](#同时驱动-4-个轮子) |
| 轮子依次转 / 四轮依次转 | 左前→右前→右后→左后各转 N 秒（默认 7s）的轮控诊断 | [#轮子依次转](#轮子依次转) |
| 小臂减才是前伸 / 机械臂关节 | XGO mini3W 机械臂关节方向标定：51 爪、52 小臂（负=前伸）、53 大臂（正=前抬）；arm_polar 不可靠，用 motor 直控 | [#机械臂关节](#机械臂关节) |
| 低趴 | 已确认的完整抓取准备姿态：车体低趴、后肢抬高与机械臂到位 | [#低趴](#低趴) |
| 放球 | 抓球的逆操作：低趴后机械臂安全伸出（爪保持闭合持球）、张爪让球落下、再安全收臂 | [#机械臂关节](#机械臂关节) |
| 抓完掉头放球 / 旋转180度 | 一键编排 `ball_grab_release.py`：抓球程序 → rotate.py 旋转 180° → 放球程序 | [#抓完掉头放球](#抓完掉头放球) |
| 主流程 / 跑主流程 | 上电后全自动：定点巡航 5 点 → 抓球放球（导航与球编排全部容器内 catkin 执行） | [#主流程](#主流程) |
| 主流程2 / 直接巡线 | 备选主流程：停占串口/相机的服务后直接进入黑线巡线（跳过导航） | [#主流程2](#主流程2) |
| 第一个右转 / 雷达后方定位 | 巡线中第一次 rear 从>2m变<1m 判定第一个右转开启；rear 依次≥0.75m、≥1.5m 时各右转90°→停2s→左转90°回正继续巡线 | [#第一个右转雷达后方定位](#第一个右转雷达后方定位) |
| 巡线 / 跑巡线 / 巡线（黑线） | 实机黑线跟随：厂商 `follow_line.py`（HSV 黑线 + PID），**启动由用户手动执行** | [#巡线](#巡线) |
| 放 catkin / 代码存放地 | 本次比赛任务代码统一写入 `robot-src/catkin_ws/src/`（原厂程序不删、不入 catkin） | [#放-catkin](#放-catkin) |

## 机器IP

- **等价说法**：机器IP、狗子IP、狗IP、机器狗的IP、IP未变、连机器
- **含义**：机器狗（OUMAX XGO mini3W，树莓派 CM5）在 WiFi 网络下的 IP 与访问方式；
  "IP未变"表示仍是 192.168.137.157。
- **前置条件**：机器已开机且 WiFi 已连上；手控服务需先取得串口控制权（默认被
  raicom-original-main.service 占用，须切换）。
- **精确动作**：
  1. 连通性：`ping 192.168.137.157`（当前 WiFi 网可达，2026-08-13 实测 80ms）。
  2. SSH：`pi@192.168.137.157:22`，用户 pi / 密码 pi。
  3. 手控服务 HTTP：`http://192.168.137.157:8765`（`/health`、`/command`；服务默认
     监听 0.0.0.0:8765，UDP 游戏手柄口 8766）。
  4. 串口控制权切换：停 `raicom-original-main.service` → 起 `oumax-manual.service`
     （或用 `/usr/local/sbin/raicom-control-handover`），切换后健康检查通过再发命令。
  5. 备用 IP：10.181.117.161（另一网络，2026-08-13 实测当前不可达）。
- **不是**：WSL 的 IP（192.168.137.232，DHCP 会变，ROS master 跑在 WSL 侧，与机器 IP
  不同）；`192.168.137.157` 不等于控制服务一定在跑（8765 未监听时须先切换服务）。
- **权威来源**：`docs/message_for_my_dog.md`（ip1/ip2）、`docs/local-rviz-navigation-quickstart.md`
  （实机 192.168.137.157 部署）、`docs/ai-records/CHANGE_LOG.md`（2026-08-08 条目：
  WSL IP 迁移至 192.168.137.232，与机器 IP 区分）。

## 驱动左后轮转动 N 秒

- **等价说法**：驱动左后轮转动 N 秒、左后轮转 N 秒、让左后轮动 N 秒
- **含义**：以单轮轮控方式驱动物理左后轮指定时长，用于现场动作或诊断。
- **前置条件**：机器已开机、场地净空且可随时断电；`/health` 返回正常，手控服务已取得
  串口控制权。
- **精确动作**：
  1. 向 `http://192.168.137.157:8765/command` 发送
     `{"kind":"wheel","enabled":true,"speeds":[0,0,0,1.2]}`，其中通道顺序为
     `[左前,右前,右后,左后]`。
  2. 在指定时长内持续刷新命令；结束或出错时必须发送
     `{"kind":"wheel","enabled":true,"speeds":[0,0,0,0]}` 停止。
- **不是**：不是左后腿舵机；不是左前轮（通道 0）；HTTP ACK 不等于该轮实际转动，必须现场观察。
- **权威来源**：`robot-src/host-services/oumax-xgo/manual_control_server.py`（`handle_wheel` 与
  `send_wheel_control`）、`docs/ai-records/mistakes/2026-08-13.md`。

## 同时驱动 4 个轮子

- **等价说法**：四个轮子一起转、四轮同驱、四轮全转、同时驱动4个轮子
- **含义**：以轮控方式让四个轮子同时同速转动指定时长，用于验证四轮驱动/直线前进能力。
- **前置条件**：机器已开机、场地净空（四轮同驱机器会整体前进，注意防跑走）；`/health`
  返回正常，手控服务已取得串口控制权。
- **精确动作**：
  1. 向 `http://192.168.137.157:8765/command` 发送
     `{"kind":"wheel","enabled":true,"speeds":[1.0,1.0,1.0,1.0]}`，通道顺序为
     `[左前,右前,右后,左后]`。
  2. 在指定时长内 10Hz 持续刷新；结束或出错时必须发送
     `{"kind":"wheel","enabled":true,"speeds":[0,0,0,0]}` 停止。
- **不是**：不是 foot（dog）行走模式；不是单轮驱动；命令 ACK 不等于四轮均实际转动
  （2026-08-13 实测左后轮不转），须现场观察。
- **权威来源**：`robot-src/host-services/oumax-xgo/manual_control_server.py`（`handle_wheel` 与
  `send_wheel_control`）、`docs/ai-records/mistakes/2026-08-13.md`、2026-08-13 四轮同驱实测。

## 轮子依次转

- **等价说法**：轮子依次转、四轮依次转、依次转 7 秒、让轮子一个一个转
- **含义**：按左前→右前→右后→左后顺序，每轮单独轮控指定时长（默认 7 秒），用于逐轮诊断。
- **前置条件**：机器已开机、场地净空可随时断电；`/health` 正常；`oumax-manual` 占串口。
- **精确动作**：
  1. 机器端（推荐）：`python3 /home/pi/oumax-xgo/drive_wheels_sequential.py`（默认每轮 7s、速度 1.2）。
  2. 开发机仓库根：`python3 tmp/drive_wheels_sequential.py 7 1.2`。
  3. 首次需部署：`scp tmp/drive_wheels_sequential.py pi@192.168.137.157:/home/pi/oumax-xgo/`。
  4. 仅左后（开发机）：`python3 tmp/drive_left_rear_wheel.py 7 1.2`。
  5. 现场目视每轮是否真转；结束确认零速。
- **不是**：不是在 `pi` 家目录下跑 `tmp/...`（该路径只存在于开发机仓库）；不是四轮同时转；不是 foot 行走；ACK 不等于转动（左后通道 3 可能硬件失效）。
- **权威来源**：`docs/launch-commands.md` §7、`tmp/drive_wheels_sequential.py`。

## 机械臂关节

- **等价说法**：小臂减才是前伸、机械臂关节、大臂/小臂方向、arm_polar 不可靠、抓球关节参数
- **含义**：OUMAX XGO mini3W（树莓派 CM5）机械臂三舵机的方向标定与可靠控制方式。
  `arm_polar(theta, r)` 极坐标命令（固件 0x76/0x77）在固件 M-7.0.0b8 上**不可靠**（命令帧发出
  但固件经常不执行），必须用 `dog.motor(id, angle)` 关节直控（0x50 MOTOR_ANGLE）。
- **关节方向标定**（2026-08-13 现场逐步实测确认）：
  - `51` = 爪子：正（+）= 收紧，负（-）= 张开
  - `52` = 小臂（肘）：**负（-）= 前伸**，正（+）= 后收（会把爪子抬向摄像头方向，危险）
  - `53` = 大臂（肩）：正（+）= 前抬，负（-）= 后倒；当前厂商 `xgomini` 运行库限幅为
    `[-75,90]`，因此 `+120` 会被库钳制为实际的 `+90`（编码 `0xFF`），
    +40 左右大臂前抬可能顶到摄像头
- **安全顺序**：
  - **硬性前置**：无论目标姿态为何，先把小臂（52）移动到安全抬起/避让位置，**才能**驱动大臂（53）；禁止直接驱动大臂。
  - 伸出：先动小臂（负值前伸，避开摄像头路径）→ 再大臂前抬 → 小臂继续前伸到位
  - 收回：**先收大臂（53→0）→ 再收小臂（52→0）**，顺序反了爪子会扫摄像头
  - **低趴接球姿态**：先发送车体低趴 `translation('z', 10)`、`attitude('p', 15)`，
    再完整重发机械臂接球序列；低趴车体指令会使已保持的机械臂姿态复位，不能反过来执行。
    行走的 `slow_trot` 步态同样会接管车体并恢复站姿；因此自动抓球必须在停止行走后、合爪前再次发送
    低趴、后肢抬高与完整机械臂准备序列，不能只在程序起始时设置一次。
  - **自动抓球时机**：先选定 `slow_trot` 步态，再下发低趴，接近与转向脉冲不得重复切换步态（否则会复位高度）；检测框达到抓取门槛、停止行走后，才抬高后肢并执行完整机械臂准备序列再合爪。
  - **抬高后部**：左右后小腿分别为 31（右后）和 41（左后）；从抓球趴伏基准
    `31=21°、41=20°` 同步增大角度会抬高后部。2026-08-14 已验证
    `31=26°、41=25°` 可实现小幅抬高，且机械臂不受影响。`dog.motor([31, 41], [26, 25])`
    能去除显式等待、快速依次下发，但机器实际 `xgolib` 会拆成两条单舵机帧，**不是真正同步**；
    不能据此保证无横移。
  - **已确认的抓取准备姿态（2026-08-14）**：先低趴
    `translation('z', 10)`、`attitude('p', 15)`，再将后肢设为
    `31=26°、41=25°`；机械臂按安全顺序
    `52=-50° → 53=90° → 52=-45°`。现场确认该姿态与位置可用。
- **抓球可用序列**（ball_green.py catch_arm，2026-08-13 实机验证可调参）：
  爪子最大张开(51:-65) → 小臂前伸(52:-50) → 大臂前抬(53:+90) → 小臂前伸到位(52:-45) →
  爪子闭合(51:+40) → 收大臂(53:0) → 收小臂(52:0)
- **放球可用序列**（`robot_dog_ball_grab/scripts/ball_release.py`，2026-08-15，
  抓球末端状态的逆操作，含视觉跟踪对齐）：
  低趴(z=10、p=15，接近阶段不加 yaw 补偿) → **视觉跟踪对齐**（YOLO 球模型暂代：|dx|>25 转向、
  半径<28 前进脉冲，与抓球接近阶段一致，达标输出 `action=align-complete`；60s 超时输出
  `action=align-timeout` 后仍继续放球）→ 重新低趴(z=10、p=15、y=-3 放球瞬间补偿) →
  抬后肢(31=26、41=25) → 小臂前伸(52:-50) → 大臂前抬(53:+90) → 小臂前伸到位(52:-45) →
  张爪放球(51:-65，默认等待 1s) → 收大臂(53:0) → 收小臂(52:0) → yaw 复原(y=0)
- **YOLO 抓球程序的车体 yaw 补偿**（`ball_yolo_grab.py`，2026-08-14/15 实机修正）：
  补偿只在**抓球瞬间**（grab）使用 `y=-3`（原 -6 调小），接近阶段（prepare_approach_pose）
  不加补偿，否则车体会向右偏斜；夹球序列收臂完成后补 `attitude('y', 0)` 复原。
  放球程序放球瞬间同款 `y=-3`（--drop-yaw 可调）。
- **不是**：不是 arm_polar 参数可盲调（极坐标黑盒无文档）；52 的正值不是前伸；
  `x_distance.txt`（默认 22）决定抓取触发距离，距离不够时先看爪子前伸量再看它。
- **权威来源**：`/home/pi/RaspberryPi-CM5/robots/Mini3W_W/demos/ball.py`（厂商示例）、
  机器实际 `xgolib_dog.py`（`xgomini` 的 MOTOR_LIMIT：51=[-65,65] 52=[-85,50] 53=[-75,90]）、
  2026-08-13 至 2026-08-14 现场逐步标定与抓球实机调试。

## 低趴

- **等价说法**：趴下、摆低趴姿态、恢复低趴、抓取准备姿态。
- **含义**：已验证的完整抓取准备姿态，而不只是车体降低。
- **前置条件**：场地净空；控制程序已取得底盘/舵机串口控制权。
- **精确动作**：
  1. 车体低趴：`translation('z', 10)`、`attitude('p', 15)`。
  2. 抬高后肢：`31=26°`、`41=25°`。
  3. 机械臂依安全顺序：`52=-50° → 53=90° → 52=-45°`。
- **不是**：不是仅下发 `translation('z', 10)` 与 `attitude('p', 15)`；如只要车体压低，明确说“车体低趴”。
- **权威来源**：本文件「机械臂关节」的 2026-08-14 实机确认姿态。

## 放 catkin

- **等价说法**：把 XX 程序放到 catkin 里、代码写到 catkin、代码存放地。
- **含义**：用户确认的项目约定——`robot-src/catkin_ws/src/` 是本次比赛任务的代码存放地，
  本次任务的代码都要写入其中；厂商原厂程序不得删除或移走。
- **前置条件**：无。
- **精确动作**：
  1. 目标代码复制/移动到 `robot-src/catkin_ws/src/` 下的既有包或新建独立功能包
     （`robot_dog_*` 命名，标准 package.xml + CMakeLists.txt + README.md）。
  2. 原厂程序（如 `robot-src/host-services/oumax-xgo/` 下的脚本）保留不动，
     catkin 里放归档副本并在 README 注明两处副本的同步关系。
  3. 厂商示例统一入 `robot_dog_demos` 包（零代码改动副本，剔除
     follow_line/YDLidar-SDK/xiaozhi_test/云服务子项目）。
  4. 运行形态统一：程序在机器端 `ros-noetic` Docker 容器内运行（容器挂载
     `/home/pi` + 设备直通，详见 `docs/technical/2026-08-16-docker-runtime-unification.md`），
     不再宿主机/容器割裂；容器运行用各包 `host/run_*_in_docker.sh` 封装。
  5. 同步更新项目索引（`.agents/skills/project-index/INDEX.md`）与 AI 工作记录。
- **不是**：不是把原厂程序从 host-services 删除；不是只在宿主机部署（机器部署路径仍按
  各自文档，如 `/home/pi/oumax-xgo/`，但执行统一走容器）。
- **权威来源**：2026-08-14 用户指令确认 + 2026-08-16 容器化统一约定；落地样例
  `robot-src/catkin_ws/src/robot_dog_ball_grab/`、`robot_dog_demos/`。

## 抓完掉头放球

- **等价说法**：抓完掉头放球、旋转180度、夹球程序完后旋转180度运行放球程序、掉头放球。
- **含义**：一键编排程序 `ball_grab_release.py`：顺序运行抓球程序（ball_yolo_grab.py）→
  旋转程序（rotate.py，turn 脉冲掉头 180°，默认速度 -15、时长 9s）→ 放球程序（ball_release.py）。
- **前置条件**：机器端 `/home/pi/oumax-xgo/` 下已部署 `ball_grab_release.py`、`rotate.py`、
  `ball_release.py`、`ball_yolo_grab.py` 四个脚本（编排按同目录解析）。
- **精确动作**：`python3 ball_grab_release.py --enable-motion`；日志按
  `stage=1/3`…`action=grabrelease-complete` 输出。
- **不是**：不是让抓球程序内部掉头（抓球/放球程序本体未被修改）；180° 掉头用
  `dog.turn` 转向脉冲实现（`dog.attitude("y", 180)` 大角度命令实机不生效，已弃用），
  时长按实机标定（当前 9s）。
- **权威来源**：`robot-src/catkin_ws/src/robot_dog_ball_grab/scripts/ball_grab_release.py`。

## 主流程

- **等价说法**：跑主流程、主流程、上电后全自动、定点巡航抓球放球。
- **含义**：比赛全自动主流程脚本 `robot_dog_navigation/scripts/main_flow.py`：
  以当前位姿为起点，依次定点 5 个点（前方 2.3 m 右转 90° → 右方 0.5 m → 右方
  1.65 m → 左方 0.575 m 回撤，朝向 180° → 前进 1 m 朝向与第一点相同），全部
  到达后运行抓球放球一键编排 `ball_grab_release.py`（抓球 → 掉头 180° → 放球）。
  导航在容器 `ros-noetic` 内、球编排在球容器 `ros-noetic-ball` 内执行 catkin 包
  程序，**不再使用宿主机程序**（2026-08-17 起；ssh 仅用于停服务与 docker exec 编排）。
- **前置条件**：`robot_dog_main.launch` 已用 AMCL 定点模式启动（`use_amcl:=true
  map_file:=ricam_arena_mapped.yaml init_x:=0.0 init_y:=0.0 init_yaw:=0.0`），
  机器在出发区与地图原点对齐摆放；球容器 `ros-noetic-ball` 已由
  `robot_dog_ball_grab/host/setup_ball_container.sh` 配置（ballenv + udevd + 设备挂载）；
  主流程脚本与球编排部署于机器 catkin_ws（`/home/pi/ros_ws/src/`，容器内
  `/root/catkin_ws/src/`）；容器→宿主机 ssh 免密。
- **精确动作**：机器终端执行 `bash /home/pi/run_main_flow.sh` 或仓库版
  `robot_dog_navigation/host/run_main_flow_in_docker.sh`（一键：导航容器内跑导航 5 点
  → ssh 本机停 oumax-camera+oumax-manual 释放相机/串口 → ssh 本机 `docker exec
  ros-noetic-ball run_ball_in_container.sh --enable-motion` 跑球编排）。不带
  `--enable-motion` 时只导航不抓球（与球编排门禁一致）。路径距离/角度全部参数化
  （`--forward-m`/`--side-distances`/`--final-forward-m`/`--turn-deg`），
  实机标定时方向反了把对应参数取负。
- **不是**：不是只跑定点（单点用 RViz 2D Nav Goal 或直接发 goal）；不是让
  球编排脚本自己导航（主流程负责导航，球程序只负责视觉抓/放）；右侧距离
  当前按地图已知区临时收缩为 `0.5,0.25,-0.575`，补扫地图右下角后恢复
  `0.5,1.65,-0.575`。
- **权威来源**：`robot-src/catkin_ws/src/robot_dog_navigation/scripts/main_flow.py`。
  启动命令见 `docs/launch-commands.md` §1。

## 巡线

- **等价说法**：跑巡线、巡线（黑线）、黑线跟随、跑一遍巡线
- **含义**：在机器上运行厂商巡线程序 `follow_line.py`（`robot_dog_follow_line` 包，原厂示例零改动）：Picamera2 视觉 HSV 黑掩码（[0,0,0]-[180,255,30]，画面上半部分清空）提取黑线 → 最大轮廓圆心横坐标作偏差 → PID（P=50、D=30）控制，|z_pid|<8 直行 move_x(18)、≥8 转向+前进、未检测到线停止；启动即进入 tracking 巡线状态（板载按钮 A 巡线 / C color / D init，B 退出）。
- **前置条件**：机器已开机连 WiFi（192.168.137.157）；场地铺好黑线；已停 `raicom-original-main.service`（占串口）与 `oumax-camera.service`（占相机）；脚本已部署 `/home/pi/oumax-xgo/follow_line.py`。
- **精确动作**（**启动由用户手动执行，AI 不得自动启动巡线**）：
  1. AI 只做：部署脚本（scp 至 `/home/pi/oumax-xgo/`）、确认服务已停、跑完确认进程清理与服务恢复、分析日志。
  2. 用户手动启动（宿主机 xgovenv 直跑；容器 `ros-noetic` 未直通 ttyAMA0 不可用）：
     `/home/pi/RaspberryPi-CM5/xgovenv/bin/python /home/pi/oumax-xgo/follow_line.py`
  3. 观察日志：相机初始化成功 + 转向角/运动决策输出即正常；乱走/异常时 Ctrl-C 或 `kill <pid>` 停止。
  4. 停止后恢复：`sudo systemctl start raicom-original-main.service oumax-camera.service`。
- **不是**：不是导航定点巡航（主流程）；不是抓球放球；HSV 掩码与 PID 阈值是原厂默认未标定；2026-08-16 实机首跑**乱走**（全程转向角 ≥8 饱和、未见直行段），需现场调参后再用。
- **权威来源**：`robot-src/catkin_ws/src/robot_dog_follow_line/README.md`、2026-08-16 实机首跑记录（`docs/ai-records/CHANGE_LOG.md`）。调试/启动见 `docs/launch-commands.md` §3。

## 主流程2

- **等价说法**：主流程2、直接巡线、开始任务后直接巡线、主流程跑不通直接巡线
- **含义**：备选主流程一键脚本 `robot_dog_follow_line/host/run_main_flow2.sh`：
  开始任务后**跳过定点巡航导航**，自动完成"停占串口/相机的服务
  （raicom-original-main + oumax-camera）→ **自动拉起雷达后方桥**
  （run_lidar_rear_bridge.sh，容器内 roscore+雷达+HTTP :8767）→ 宿主机
  xgovenv 前台运行巡线程序 `follow_line.py"（启动即 tracking 巡线，带雷达后方
  第一个右转定位，B 键退出）。主流程1（导航 5 点 → 抓球放球）行不通时使用。
- **前置条件**：机器已开机连 WiFi（192.168.137.157）；场地铺好黑线；`follow_line.py`、
  `run_main_flow2.sh`、`run_lidar_rear_bridge.sh` 已部署 `/home/pi/oumax-xgo/`；
  容器 `ros-noetic` 运行中（雷达桥 docker exec 依赖）。
- **精确动作**（**启动由用户手动执行，AI 不得自动启动**）：机器端一条指令
  `bash /home/pi/oumax-xgo/run_main_flow2.sh`；脚本前台运行，退出后不自动恢复
  已停服务（与主流程1一致），后续需要再手动 `systemctl start`。雷达桥失败（容器
  未起等）→ 脚本中止（full exposure）。解释器/脚本路径可用环境变量
  `RAICOM_XGO_PYTHON`、`RAICOM_FOLLOW_LINE`、`RAICOM_REAR_BRIDGE` 覆盖。
- **不是**：不是定点巡航抓球放球（那是主流程1）；不是"停服务 + 跑巡线"之外
  的编排（无导航、无抓球，雷达桥只是辅助定位转弯）；巡线参数仍是原厂默认未标定，
  2026-08-16 实机首跑**乱走**，使用前须先完成巡线调参。
- **权威来源**：`robot-src/catkin_ws/src/robot_dog_follow_line/host/run_main_flow2.sh`、
  `docs/ai-records/CHANGE_LOG.md`。启动命令见 `docs/launch-commands.md` §2。

## 第一个右转（雷达后方定位）

- **等价说法**：第一个右转、雷达后方0.75m/1.5m右转90度、转一次90度停2s再转回来、
  rear 从2m变1m、雷达后方定位开启
- **含义**：`follow_line.py` 巡线中的雷达后方定位功能（默认开启，替代旧
  armed+rising 逻辑）：正常巡线中**第一次 rear 从 >2m 变为 <1m** 判定为
  "第一个右转"并开启功能（只一次）；此后 rear **依次增大到 ≥0.75m、≥1.5m**
  各执行一次转向序列：**右转 90° → 停 2s → 左转 90° 回正 → 继续巡线**（IMU yaw
  闭环，全部完成不再触发）。**第1次触发前要求相对阶段1时刻 yaw 已转过 ≥80°**
  （`rear_yaw_min_deg`，防刚转角就触发），第2次起不要求。
- **前置条件**：雷达桥 `run_lidar_rear_bridge.sh` 常开（:8767 返回 rear_m）；
  起点后方须 >2m；第一个右转处车尾须贴近障碍 <1m 才能开启。
- **精确动作**：
  1. 阶段1：`check_rear_trigger()` 曾见 rear>2.0m 后首次 rear<1.0m → 记录
     此刻 yaw0，`_rear_dip_done=True` 打日志"第一个右转".
  2. 阶段2：按 `rear_turn_at_steps_m` 依次（默认 [0.75, 1.5]）触发
     `start_rear_turn_seq()` 右转90°（speed -16）→ sleep 2s → 左转90°
     （speed +16）→ PID 重置继续巡线；**第1次前校验 |yaw-yaw0| ≥
     rear_yaw_min_deg**（未满足打"等 yaw"，满足打"yaw 验证通过"）；每阈值一次。
  3. 参数可写 `follow_line_config.json`：`rear_dip_from_m`/`rear_dip_to_m`/
     `rear_turn_at_steps_m`/`rear_yaw_min_deg`/`rear_turn_deg`/`rear_hold_s`。
- **不是**：不是旧 armed（rear<2.8m）→ rising（rear≥3.0m）右转90°；不是线宽突变
  （默认关）；不是视觉拐角/丢线探测转弯；转向序列阻塞约 5-7s 期间不巡线。
- **权威来源**：`robot-src/catkin_ws/src/robot_dog_follow_line/scripts/follow_line.py`
  （`check_rear_trigger`/`start_rear_turn_seq`）、`docs/launch-commands.md` §3.2。

## 抓取准备姿态下的球像素基准

- **采样时间**：2026-08-14。
- **姿态**：低趴（`z=10`、`p=15`）、后肢抬高（`31=26°`、`41=25°`）；本次采样未发送 51/52/53 的机械臂指令。
- **画面与检测**：320×240 RGB 画面，项目 YOLO 模型连续 10/10 帧识别为 green，置信度中位数 `0.916`。
- **球像素**：中心中位数 `x=144.0px`、`y=179.3px`；检测框半径中位数 `32.1px`。十帧中心范围为 `x=143.8–144.5px`、`y=179.3–179.6px`。
- **用途**：这是当前“已可夹球”摆位的观测基准；画面水平中心为 `x=160px`，该球相对中心偏左约 `16px`。

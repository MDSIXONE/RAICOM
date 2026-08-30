# robot_dog_teleop

键盘点动请求包。当前默认只向隔离的
`/robot_dog_teleop/requested_cmd` 发布 `Twist` 请求，**不会**向 `/cmd_vel`、串口或
底盘发送任何命令。因为当前尚未验证机器狗的 ROS 底盘驱动与控制权，它不能使机器狗
运动；开机后必须先单独确认官方控制接口。

程序默认锁定，不会因启动而运动：先按 `u`，在 5 秒内再按 `y` 才解锁。解锁前会提示
确认场地净空、人员远离和急停可达。`w`、`s`、
`a`、`d` 分别是前进、后退、左转、右转；每次仅发出 0.20 秒脉冲，随后自动发出零速度。
空格、`x` 或 Ctrl-C 会立即发送零速度并重新锁定。

默认线速度为 0.05 m/s，角速度为 0.20 rad/s；启动参数严格限制在线速度
0.01–0.05 m/s、角速度 0.05–0.20 rad/s、脉冲 0.05–0.50 秒内。

```bash
source /opt/ros/noetic/setup.bash
source /root/catkin_ws/devel/setup.bash
roslaunch robot_dog_teleop keyboard_teleop.launch
```

不要将请求话题直接重映射到 `/cmd_vel`，也不要与当前
`robot_visualization.launch` 的隔离速度话题混淆。

## 进入 ROS Docker 容器

机器狗的 ROS Noetic 安装在名为 `ros-noetic` 的 Docker 容器中；SSH 登录后的
`pi@pi` 提示符仍是**宿主机**，不能直接执行 `source /opt/ros/noetic/setup.bash`。

```bash
# 宿主机：先确认容器正在运行
docker ps --format 'table {{.Names}}\t{{.Status}}'

# 宿主机：进入 ROS 容器（终端提示符会变为 root@...）
docker exec -it ros-noetic bash

# 容器内：加载 ROS 与当前工作区
source /opt/ros/noetic/setup.bash
source /root/catkin_ws/devel/setup.bash
```

容器内源码路径是 `/root/catkin_ws/src/robot_dog_teleop`，它对应宿主机的
`/home/pi/ros_ws/src/robot_dog_teleop`。输入 `exit` 返回宿主机。

`sudo /usr/local/sbin/raicom-launch-physical-keyboard` 和
`sudo /usr/local/sbin/raicom-launch-physical-keyboard-continuous` 必须在**宿主机**运行，
不能在容器内运行；这两个启动器负责在启动 ROS 节点前安全切换原厂程序与手控服务。

## 真实控制桥接

机器上已有的 `oumax-manual.service` 独占 `/dev/ttyAMA0`，并在本机
`127.0.0.1:8765` 提供 OUMAX 控制服务。`physical_keyboard_teleop.py` 只调用该服务，
不会从 ROS 容器直接打开串口，也不订阅 ROS 速度话题；只接受本进程键盘的前后和原地
转向。默认值复用原厂 Dog_LM 摇杆的普通档位：前后 XGO 值 `17`，原地转向 XGO 值
`55`（分别允许范围 `1–25`、`1–70`）；键盘控制仍将每次动作限制为最长 0.20 秒。
为防止按住键盘产生自动重复，成功点动后程序会立即重新锁定；每次新的物理动作都须再次
按 `u`、再按 `y`。零命令、超时、异常和退出都会请求停止。

真实控制 launch 必须显式给出 `enable_motion:=true`，并且键盘端仍需按 `u`、再按 `y`
才会发出每次点动：

```bash
roslaunch robot_dog_teleop physical_keyboard_teleop.launch enable_motion:=true
```

首次物理测试前，确认机器已站稳、四周至少留出 1 m 净空、无人位于运动方向、可立即按
机器实体急停或断电，并只进行一次短脉冲。禁止同时启动其他手柄、APP、raw-XGO 或串口
控制程序；`oumax-manual.service` 是唯一允许持有串口的程序。

导航栈使用的 `oumax_cmd_vel_bridge.py`（cmd_vel → 手控服务桥）已于 2026-08-17 迁至
底层运动控制包 `robot_dog_control`，启动入口不变（仍由 robot_dog_bringup 的
robot_dog_main.launch 启动）。

## 自动切换原厂程序（部署后使用）

`host/` 内包含宿主机脚本，解决原厂 `common/main.py` 与 OUMAX 手控服务不能同时占用
`/dev/ttyAMA0` 的问题。安装后，原厂程序会从 `rc.local` 的单次启动迁移为
`raicom-original-main.service`；键盘控制启动和退出时的控制权顺序如下：

```text
原厂 UI 运行
  → 停止原厂 UI，确认串口释放
  → 启动仅本机监听的 OUMAX 服务并检查健康状态
  → 交互式物理键盘控制
  → 停止 OUMAX 服务，确认串口释放
  → 恢复原厂 UI
```

`install_host_handover.sh --install-only` 只安装单位和脚本，不改变当前运行的原厂程序；
`--cutover` 才会进行一次可回退的切换。安装脚本只会替换已核验的 `rc.local` 原厂启动行，
会先备份到 `/etc/rc.local.raicom-pre-handover`，不会重新执行整个 `rc.local`。

完成迁移后，通过宿主机终端启动真实键盘控制：

```bash
sudo /usr/local/sbin/raicom-launch-physical-keyboard
```

该命令在 `roslaunch` 退出、Ctrl-C、终端关闭信号时都会尝试恢复原厂 UI。若终端或机器异常
断电，物理键盘节点自身的 0.20 秒停止保护仍会生效；恢复供电后由 systemd 启动原厂 UI。
任何实际部署和首次点动前，均须确认已充电、急停或断电可达、周围至少 1 m 净空。

## 连续键盘控制（部署后使用）

单点动模式保留为默认安全入口；如需按住方向键连续移动，使用独立的连续模式。它复用原厂
摇杆默认幅值（前后 `17`、yaw `55`），通过 OUMAX 的本机 UDP 手柄接口刷新命令。普通 SSH
终端不能直接读取按键松开事件：按住方向键时终端会产生重复键以刷新命令，停止重复后，本地会
在最多 0.25 秒内连续发送三帧零命令；节点/终端故障时宿主服务还会在约 0.35 秒内看门狗停止。
它不是 m/s 或 rad/s，且只能在原厂 UI 已由接管器停止时运行。

```bash
sudo /usr/local/sbin/raicom-launch-physical-keyboard-continuous
```

出现 `CONTINUOUS keyboard teleop is LOCKED` 后，先按 `u`、再按 `y`；按住 `w/s` 前后移动，
按住 `a/d` 原地转向。方向键的重复键会最多以 10 Hz 刷新，松键后重复键停止，随即触发上述
超时停止；少数终端的重复键延迟可能让动作不连续。空格、`x`、Ctrl-C 始终立即停止并锁定。
首次使用只在净空场地短暂轻按每个方向，确认停止、方向和实体急停后再连续控制。

## 机械臂键盘控制（部署后使用）

机械臂控制通过 OUMAX 手控服务的 `kind=arm` 接口完成，与运动键盘控制共用
`u`、`y` 双确认安全模式。机械臂接口接收 0–255 的笛卡尔目标点（`x` 前后、`z` 升降），
每次按键只移动一个有界步长，机械臂保持最近一次目标点；不存在持续运动，也不需要看门狗。

```bash
sudo /usr/local/sbin/raicom-launch-arm-keyboard
```

出现 `ARM keyboard teleop is LOCKED` 后，先按 `u`、再按 `y`：

| 按键 | 动作 |
| --- | --- |
| `w` / `s` | 机械臂 `x` 前伸 / 收回一个步长 |
| `a` / `d` | 机械臂 `z` 降低 / 升高一个步长 |
| `q` / `e` | 夹爪张开 / 合拢一个步长 |
| `m` | 机械臂回到中间位置（默认 x=80、z=60） |
| 空格 / `x` | 锁定（机械臂保持当前姿态，不再接收新目标） |
| Ctrl-C | 第一次锁定，第二次退出程序 |

默认步长为 10（范围 1–20），夹爪步长 10（范围 1–40），均可在 launch 时用
`arm_step`、`claw_step` 覆盖；`home_x`、`home_z` 可覆盖中间位置。键盘端会在 0–255 内
钳制目标值，本地记录当前姿态作为步进基准；若机械臂曾被其他程序移动，先按 `m` 回中再
步进。首次实机测试须净空 1 m、确认急停可达，并且只按 `m` 验证一次回中行为。

## 车体姿态键盘控制（部署后使用）

姿态控制通过 OUMAX 手控服务的 `kind=motor` 接口完成，逐舵机控制 15 个关节
（`j1`–`j15`）：`j1`–`j12` 为四条腿（j1/j2/j3 左前、j4/j5/j6 右前、j7/j8/j9 右后、
j10/j11/j12 左后，分别为小腿/大腿/髋），`j13` 为机械爪，`j14` 为小臂，`j15` 为大臂。
每个关节有独立的舵机角度范围，按键只移动一个有界步长，舵机保持最近一次目标角；不存
在持续运动，也不需要看门狗。沿用 `u`、`y` 双确认安全模式。完整指令、关节映射、控制
范围与记录格式见 [`pose_keyboard_control.md`](pose_keyboard_control.md)。

```bash
sudo /usr/local/sbin/raicom-launch-pose-keyboard
```

出现 `POSE keyboard teleop is LOCKED` 后，先按 `u`、再按 `y`：

| 按键 | 动作 |
| --- | --- |
| `[` / `]` | 循环选择当前关节（j1–j15） |
| `w` / `s` | 当前关节细步 +1° / -1° |
| `q` / `e` | 当前关节粗步 +10° / -10° |
| `m` | 全部关节回中（默认姿态：腿 0、爪 0、小臂 70、大臂 -85） |
| `r` | 记录当前姿态到文件（追加一行，含时间戳） |
| 空格 / `x` | 锁定（舵机保持当前角度，不再接收新目标） |
| `h` | 显示按键帮助 |
| Ctrl-C | 第一次锁定，第二次退出程序 |

终端底部固定两行实时显示：第一行为当前关节与步长，第二、三行为完整姿态
（`j1 0, j2 0, j3 0, ... j15 -85` 分两行展示，方便直接抄录）。细步默认 1°、粗步默认
10°，可在 launch 时用 `fine_step`、`coarse_step` 覆盖；记录文件默认
`/tmp/xgo_poses.log`，可用 `record_file` 覆盖。键盘端会在各关节范围内钳制目标值并本地
跟踪当前姿态作为步进基准；若舵机曾被其他程序移动，先按 `m` 回中再步进。首次实机测试
须净空 1 m、确认急停可达，并且只按 `m` 验证一次回中行为，随后用 `w`/`s` 以最小细步
验证单个关节方向。

## 自动对准夹球（部署后使用）

自动流程：趴下姿态（只动腿 `j1`–`j12`，机械臂不动）→ 视觉对准球心（髋关节
`j3`/`j6`/`j9`/`j12` 同步调整）→ 放臂夹球（爪子张开到最大 → 臂到位 → 闭合）。完整
流程、参数与安全清单见 [`ball_align_grab.md`](ball_align_grab.md)。

```bash
sudo /usr/local/sbin/raicom-launch-ball-align-grab
```

首次使用前先用姿态键盘程序回中并目视核对髋关节方向；球放在机器前方视野内，垂直偏差
过大时程序只提示、不自动移动。

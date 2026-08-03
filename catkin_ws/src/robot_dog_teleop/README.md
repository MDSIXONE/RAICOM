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

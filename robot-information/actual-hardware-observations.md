# 实机硬件观测记录

> 观测日期：2026-07-30
> 适用对象：当前接入的蓝色 XGO 系列轮足机器狗。
> 目的：记录已实测事实，区分已确认信息、合理推断与待确认项。本文不保存 Wi-Fi 密码、登录凭据或其他敏感信息。

## 1. 已确认事实

### 1.0 上位机系统与资源（SSH 只读采集）

> 采集日期：2026-08-02。以下结果来自上位机 SSH 会话中的只读命令；不包含 IP、密码、机器 ID 等敏感接入信息。

| 项目 | 已确认信息 |
| --- | --- |
| 设备型号 | Raspberry Pi Compute Module 5 Lite Rev 1.0 |
| 主机名 | `pi` |
| 操作系统 | Debian GNU/Linux 12（bookworm） |
| 内核 | `6.6.62+rpt-rpi-2712`，`aarch64` |
| CPU | 4 核 ARM Cortex-A76；频率范围 1.5–2.4 GHz；L2 缓存 2 MiB，L3 缓存 2 MiB |
| 内存 | 4.0 GiB（更新采集时已用 890 MiB、可用 3.1 GiB） |
| Swap | 199 MiB（采集时未使用） |
| 系统存储 | `mmcblk0`，总容量约 59.5 GiB（64 GB 存储卡）；根分区为 ext4，已扩展至 58 GiB |
| 根分区空间 | 已用 28 GiB、可用约 29 GiB、使用率 50% |
| 启动分区 | `/boot/firmware`，FAT32，511 MiB；可用约 435 MiB |
| 原生 ROS | 未安装：宿主机的 `rosversion` 不存在、`/opt/ros/` 为空；ROS 通过下列 Docker 容器提供 |

更换并扩展存储卡后，根分区使用率已从约 89% 降至 50%。在下载模型或保存数据集前仍应检查占用，建议为系统更新和容器运行至少保留 10 GiB 可用空间。

### 1.0.1 Docker 与 ROS Noetic 部署（2026-08-02）

| 项目 | 已确认信息 |
| --- | --- |
| Docker Engine | `29.7.1` |
| Docker Compose | `v5.3.1` |
| ROS 运行环境 | ARM64 的 ROS 1 Noetic；容器内 `ROS_DISTRO=noetic` |
| 容器 | `ros-noetic`，运行中；重启策略为 `unless-stopped` |
| 工作区映射 | 宿主机 `/home/pi/ros_ws` 挂载为容器 `/root/catkin_ws` |
| 网络与进程间通信 | 使用宿主网络与 IPC；未授予特权模式 |
| Docker 占用 | 镜像约 2.841 GB；运行容器约 86 KiB（不含工作区源码与构建产物） |
| 已创建功能包 | `robot_dog_bringup` 发布只读系统状态；`robot_dog_lidar` 只发布 `/scan`，不订阅底盘控制话题 |

该功能包依赖 `rospy`、`roscpp` 与 `std_msgs`，已在容器工作区通过 `catkin_make` 构建，并完成 `roslaunch` 启动与状态话题发布验证。手动运行时，需先在容器中依次执行 `source /opt/ros/noetic/setup.bash` 和 `source /root/catkin_ws/devel/setup.bash`，再运行对应 ROS 命令。

### 1.0.2 USB 设备与拓扑（SSH 只读采集）

已发现的非根集线器 USB 外设如下；其余条目均为 Linux 主机控制器的根 Hub。

| 拓扑位置 | 设备 | USB ID | 速率 | Linux 驱动 |
| --- | --- | --- | --- | --- |
| Bus 5 / Port 1 | Terminus Technology USB 2.0 Hub | `1a40:0101` | 480 Mb/s | `hub/4p` |
| Bus 5 / Port 1.1 | Silicon Labs CP2102 USB-to-UART Bridge Controller（已确认用于 YDLIDAR） | `10c4:ea60` | 12 Mb/s | `cp210x` |

USB 根 Hub 情况：

- Bus 1、Bus 3：`xhci-hcd` USB 2.0 根 Hub，最高 480 Mb/s。
- Bus 2、Bus 4：`xhci-hcd` USB 3.0 根 Hub，最高 5 Gb/s。
- Bus 5：`dwc2` USB 2.0 根 Hub，最高 480 Mb/s；当前 Hub 和 CP2102 串口桥均挂载在此总线上。

该 CP2102 已通过机器随附的 YDLIDAR 程序与 ROS 扫描测试确认是二维雷达接口：宿主机设备节点为 `/dev/ttyUSB0`，稳定枚举名为 `/dev/serial/by-id/usb-Silicon_Labs_CP2102_USB_to_UART_Bridge_Controller_0001-if00-port0`。ROS 容器只将该节点映射为 `/dev/ydlidar`；底盘使用的 `ttyAMA0` 未映射，也不能作为雷达端口。

### 1.0.3 实机二维雷达验证（2026-08-02）

| 项目 | 已确认信息 |
| --- | --- |
| 厂商与型号 | YDLIDAR Tmini Plus（由设备启动时返回的型号信息确认） |
| 接口与参数 | CP2102 → `/dev/ttyUSB0`；230400 baud；三角测距协议；10 Hz |
| ROS 话题 | `/scan`，消息类型 `sensor_msgs/LaserScan`，坐标系 `laser_frame` |
| 验证结果 | 已收到有效范围与强度数组；扫描后设备日志确认已停止 |
| 安全边界 | 节点端口硬编码为容器内 `/dev/ydlidar`，不能由 launch 参数替换；默认只运行 10 秒并在退出时调用 `turnOff()`、`disconnecting()` |

ROS 容器显式映射当前雷达节点，并以只读方式挂载机器随附的 YDLIDAR SDK 源码。该映射不会自动启动雷达；只有手动启动 `robot_dog_lidar` 的 launch 时才会扫描。若 USB 枚举变化导致宿主机不再提供当前节点，容器中的雷达设备不存在，节点会初始化失败而不会回退到其他串口。

### 1.1 外观与网络

- 机头 AI 模组带彩色屏幕、前置摄像头和 XGO 标识。
- 屏幕可显示机器狗自身 Wi-Fi 热点信息及本地管理地址 `10.42.0.1`。
- Windows 主机连接该热点后，`ping 10.42.0.1` 4 次均成功，往返时间为 1–6 ms。
- 访问 `http://10.42.0.1` 返回 `ERR_CONNECTION_REFUSED`，说明该地址没有开放 HTTP 80 端口服务。
- Telnet 23 端口连接失败。SSH 22 端口探测未在本次会话中得到明确结果，不应据此判断 SSH 是否可用。

### 1.2 Type-C 串口链路

- 将一根 Type-C 数据线接入 Windows 后，系统枚举出 `USB-SERIAL CH340 (COM3)`。
- 设备标识：`USB\\VID_1A86&PID_7523`，对应 WCH CH340 USB 转串口桥。
- 以 **115200、8N1、无流控** 对 `COM3` 进行 5 秒只读监听，成功收到 508 字节启动日志。
- 该 Type-C 链路通向 ESP32 固件日志；它不是已确认的 Linux 上位机 USB 接口。

### 1.3 ESP32 启动日志摘要

```text
rst:0x1 (POWERON_RESET),boot:0x17 (SPI_FAST_FLASH_BOOT)
mode:DIO, clock div:1
entry 0x400805e4
-----init20
get chip id ICM20948: 234
get chip id QMI8658C: 0
```

结论：

- ESP32 已从 SPI Flash 正常启动。
- `ICM20948` 的返回值为 234（十六进制 `0xEA`），表明该 IMU 可被当前固件识别。
- `QMI8658C` 返回 0；当前固件没有识别到该 IMU，不能据此断言故障，因为该机型可能本就未装该器件。
- `esp_core_dump_flash: No core dump partition found!` 表示固件未配置崩溃转储分区，不等同于当前崩溃。

## 2. 相机与计算分工

XGO CM4/CM5 系列的官方架构将屏幕、5MP 摄像头和 AI 识别放在树莓派计算模组，将 ESP32 用作舵机、供电和步态控制下位机，二者通过串口通信。[XGO2 Architecture](https://wiki.elecfreaks.com/en/pico/cm4-xgo-robot-kit/xgo2-overview/)

当前实机的屏幕和前置摄像头外观与该架构一致，但尚未通过系统启动画面或主板标签确认具体上位机型号。因此：

- **已确认**：`COM3` 是 ESP32 下位机的调试日志通道。
- **高概率推断**：前置摄像头接入机头 AI 模组，而非 `COM3` 对应的 ESP32。
- **尚未确认**：AI 模组究竟是树莓派 CM4、CM5、地平线 X 系列，还是其他定制板；相机的确切型号、接口和驱动也未确认。

不要向 `COM3` 随意发送字节、AT 命令或刷写 ESP32-CAM 固件。这样可能覆盖步态/舵机控制程序，且不能证明能访问前置摄像头。

## 3. 当前可用调试入口

| 入口 | 状态 | 用途 | 限制 |
| --- | --- | --- | --- |
| Wi-Fi 热点 → `10.42.0.1` | 已连通 | 设备控制网络、可能的移动端控制 | 无 HTTP 80 服务；SSH 未确认 |
| Type-C → `COM3` | 已连通 | ESP32 启动日志、下位机调试 | 不要发送未知命令或刷写固件 |
| ROS Docker → `/scan` | 已验证 | 获取 YDLIDAR Tmini Plus 二维扫描 | 仅手动启动；默认限时 10 秒；不映射或访问底盘 `ttyAMA0` |
| HDMI | 待接显示器验证 | 识别并访问可能的上位机桌面/终端 | HDMI 只输出视频，不能代替键盘、鼠标或串口 |

## 4. 下一步（按风险从低到高）

1. 将 HDMI 接入外部显示器或电视（不要接笔记本 HDMI 输出口），记录启动画面与系统标识。
2. 找到机头 AI 模组的独立 USB 数据口，接入键盘/鼠标；不要误用下位机 Type-C 或充电口。
3. 在上位机终端执行只读识别命令：

   ```bash
   cat /proc/device-tree/model 2>/dev/null
   uname -a
   ls -l /dev/serial* /dev/ttyAMA* /dev/ttyUSB* /dev/ttyACM* 2>/dev/null
   ```

4. 仅在确认上位机和相机接口后，再测试相机采集与向电脑传输图片。

## 5. 现场操作安全规则

- 读取 `COM3` 日志前将机器狗架空或固定，串口打开可能导致控制器短暂复位。
- 调试过程中不接充电器进行步态、机械臂或舵机动作测试。
- 不将热点密码、SSH 密码或其他凭据写入版本库。
- 未取得原厂固件和刷写流程前，不对 ESP32 执行擦除、烧录或恢复出厂设置。

# 机器狗设备信息

> 最后实测：2026-08-02。只记录当前开发需要的已确认信息；不保存 IP、密码、设备序列号或其他接入凭据。

## 当前硬件与系统

| 项目 | 已确认信息 |
| --- | --- |
| 机器人 | 蓝色 XGO 系列轮足机器狗 |
| 上位机 | Raspberry Pi Compute Module 5 Lite Rev 1.0，主机名 `pi` |
| 系统 | Debian GNU/Linux 12（bookworm），内核 `6.6.62+rpt-rpi-2712`，`aarch64` |
| 内存 | 4 GiB；最近一次采集可用约 3.1 GiB |
| 存储 | 64 GB 存储卡；根分区 ext4 58 GiB，最近一次采集可用约 29 GiB（50% 已用） |
| 启动分区 | `/boot/firmware`，FAT32，511 MiB |

## ROS 与 Docker

| 项目 | 已确认信息 |
| --- | --- |
| 原生 ROS | 未安装；ROS 仅在 Docker 中运行 |
| Docker | Engine `29.7.1`，Compose `v5.3.1` |
| ROS | ARM64 ROS 1 Noetic，容器名 `ros-noetic`，重启策略 `unless-stopped` |
| 工作区 | 宿主机 `/home/pi/ros_ws` → 容器 `/root/catkin_ws` |
| 功能包 | `robot_dog_bringup`（只读系统状态）、`robot_dog_lidar`（二维雷达 `/scan`） |
| 自动行为 | 容器不会自动启动雷达；雷达必须由手动 launch 触发 |

进入 ROS 容器后，先加载环境：

```bash
source /opt/ros/noetic/setup.bash
source /root/catkin_ws/devel/setup.bash
```

## 二维雷达

| 项目 | 已确认信息 |
| --- | --- |
| 型号 | YDLIDAR Tmini Plus |
| 接口 | CP2102 USB 串口桥（`10c4:ea60`） |
| 宿主机设备 | `/dev/ttyUSB0`；稳定枚举名位于 `/dev/serial/by-id/` |
| 容器设备 | 仅映射为 `/dev/ydlidar` |
| 参数 | 230400 baud、360°、10 Hz |
| ROS 输出 | `/scan`，类型 `sensor_msgs/LaserScan`，坐标系 `laser_frame` |
| 验证 | 已收到有效扫描数据；限时测试结束后设备确认停止扫描 |

启动一次默认 10 秒的扫描测试：

```bash
roslaunch robot_dog_lidar lidar.launch
rostopic echo -n 1 /scan
```

安全边界：`robot_dog_lidar` 将端口固定为 `/dev/ydlidar`，不订阅 `/cmd_vel`，不访问底盘使用的 `ttyAMA0`；退出时调用 `turnOff()` 和 `disconnecting()` 关闭雷达。

## 操作约束

- 不将密码、IP、令牌或设备序列号写入仓库。
- 雷达工作时不拆盖、不手拨顶部、不遮挡侧面扫描窗口。
- 未确认串口用途前，不向串口发送控制字节；尤其不要访问底盘 `ttyAMA0`。
- 存储空间低于 10 GiB 时，先清理或扩容，再下载镜像、模型或数据集。

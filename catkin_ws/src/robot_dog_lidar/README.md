# robot_dog_lidar

此包使用机器狗随附的 YDLIDAR SDK 发布 `sensor_msgs/LaserScan` 到 `/scan`。它不订阅 `/cmd_vel`，不访问底盘使用的 `ttyAMA0`，且将端口硬性限制为容器内映射的 `/dev/ydlidar`；launch 参数不能将它替换为其他串口。

默认 launch 只运行 10 秒；节点退出时会调用 SDK 的 `turnOff()` 和 `disconnecting()`。开始前应固定机器狗，并确认没有其他进程占用雷达串口。

容器需将已确认的供应商 SDK 源码挂载到 `/opt/ydlidar-sdk-src`，并将当前 CP2102 设备映射为 `/dev/ydlidar`。构建与启动：

```bash
source /opt/ros/noetic/setup.bash
cd /root/catkin_ws
catkin_make
source devel/setup.bash
roslaunch robot_dog_lidar lidar.launch
```

验证一条扫描：

```bash
rostopic echo -n 1 /scan
```

若初始化失败、连续三次读不到数据、出现异常噪声或机器狗出现任何异常，应立即停止节点；节点会关闭雷达。限时依据真实墙钟，不受 ROS 仿真时间影响。仅在确认需要持续扫描时，才将 `test_duration_sec` 设为 `0`；负值会被拒绝。

# robot_dog_control

机器人底层运动控制包,目前唯一节点 `oumax_cmd_vel_bridge` 把导航栈 `/cmd_vel`
(geometry_msgs/Twist)桥接为对机器本机 OUMAX 手控服务(127.0.0.1:8765)的运动脉冲调用。

## 节点:oumax_cmd_vel_bridge

订阅 `/cmd_vel` 与 `~stop_cmd`(std_msgs/Bool,True 暂停并立即停车);10 Hz 刷新循环
持续补发当前命令,服务端 runtime 作为看门狗;cmd_vel 超 `~watchdog_sec` 未更新或收到
零速度则停车;`enable_motion:=true` 门禁,启动时校验手控服务身份
(serial_port=/dev/ttyAMA0、manual_port=8765)。

### 参数

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| cmd_vel_topic | /cmd_vel | 导航栈速度输入话题 |
| drive_mode | dog | 运动模式:dog(脉冲步进)/ wheel4(手柄接口) |
| linear_motion_value | 17.0 | 前后 XGO 脉冲幅值(1–25) |
| yaw_motion_value | 55.0 | 原地转向 XGO 脉冲幅值(1–70) |
| x_scale_ref | 4.0 | 线速度满步长映射参考值 |
| yaw_scale_ref | 2.0 | 角速度满步长映射参考值 |
| x_min_step | 5.0 | 线速度最小步长下限(1–25) |
| yaw_min_step | 10.0 | 角速度最小步长下限(1–70) |
| dead_zone_vx | 0.02 | 线速度死区 |
| dead_zone_wz | 0.05 | 角速度死区 |
| pulse_duration_sec | 0.25 | 单次运动脉冲时长(服务端 runtime 看门狗) |
| watchdog_sec | 0.35 | cmd_vel 未更新超时停车阈值 |
| rate_hz | 10.0 | 刷新循环频率 |
| enable_motion | false | 运动门禁,须显式 true 才允许实机运动 |

## 启动方式

该节点由 `robot_dog_bringup` 的 `robot_dog_main.launch` 统一启动,无需单独启动;实机
参数(如 x_scale_ref=0.2、x_min_step=15)在 launch 中调优,与 XGO 固件死区(~12)有关。

## 迁移说明

本包 2026-08-17 从 robot_dog_teleop 迁入,迁移为纯包归属变更,节点行为零变化。
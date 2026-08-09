# robot_dog_bringup

机器狗 ROS Noetic 功能包。当前仅发布只读系统状态，不发送舵机、串口或相机控制命令。

## 运行

```bash
roslaunch robot_dog_bringup robot_dog_bringup.launch
rostopic echo /robot_dog_bringup/status
```

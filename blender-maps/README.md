# Blender 与地图资产

`ricam_arena/` 保存赛场地图的可编辑源文件和对外发布的地图数据：

- `blender/ricam_arena.blend`：Blender 场景源文件。
- `gazebo/`：Gazebo world、OBJ/MTL 导出模型和场地预览图。
- `navigation/`：`map_server` 栅格图、YAML 元数据，以及 10 cm 网格的顶点编号 PNG/JSON。

仿真运行时使用的同一份导出副本位于 `wsl-simulation/src/ricam_arena_sim/`，以保证 WSL Catkin 工作区可独立启动。修改 Blender 场景后，请同步导出 OBJ/MTL、world 和导航栅格图至这两个位置。

## 本地离线导航演示地图

`offline_navigation_arena.py` 是用于本地 `robot_dog_navigation` 演示的独立、可再生成
Blender 场景源；对应的 ROS 占据栅格图位于
`robot-src/catkin_ws/src/robot_dog_navigation/maps/offline_navigation_arena.pgm`。该演示与赛场
`ricam_arena/` 资产互不替代，也不会连接机器狗或 ROS Master。

如需生成该演示的二进制 `.blend`，在安装 Blender 后执行：

```powershell
& 'C:\Program Files\Blender Foundation\Blender\blender.exe' --background --python .\blender-maps\offline_navigation_arena.py
```

# Blender 与地图资产

`ricam_arena/` 保存赛场地图的可编辑源文件和对外发布的地图数据：

- `blender/ricam_arena.blend`：Blender 场景源文件。
- `gazebo/`：Gazebo world、OBJ/MTL 导出模型和场地预览图。
- `navigation/`：`map_server` 栅格图、YAML 元数据，以及 10 cm 网格的顶点编号 PNG/JSON。

仿真运行时使用的同一份导出副本位于 `wsl-simulation/src/ricam_arena_sim/`，以保证 WSL Catkin 工作区可独立启动。修改 Blender 场景后，请同步导出 OBJ/MTL、world 和导航栅格图至这两个位置。

# RICAM Arena Simulation

该包依据足式组规则 PDF 的图 4-2/4-3 建立 3.0 m × 2.5 m 独立仿真场地。规则只给出部分尺寸，因此区域中心坐标按图示比例固定在生成脚本中，便于后续实测后统一调整。

日常启动、硬件加速检查和停止方法见 [QUICK_START.md](QUICK_START.md)。

```bash
roslaunch ricam_arena_sim simulation.launch
```

在 WSLg 中使用 NVIDIA/D3D12 硬件渲染时，启动前显式清除软件渲染开关并选择 D3D12 驱动：

```bash
unset LIBGL_ALWAYS_SOFTWARE
export GALLIUM_DRIVER=d3d12
export MESA_D3D12_DEFAULT_ADAPTER_NAME=NVIDIA
roslaunch ricam_arena_sim simulation.launch
```

可用 `grep 'GL_RENDERER' ~/.gazebo/ogre.log` 核对实际渲染器；RTX 4060 环境应显示 `D3D12 (NVIDIA GeForce RTX 4060)`，不得显示 `llvmpipe`。

- 起点：`(-1.30, 1.00, 0 rad)`，机器狗头部沿世界坐标 `+X` 轴水平向右，并按 Mini2 包围盒向场内留出墙距。
- 识别区：右侧两块 0.8 m × 0.5 m 灰区，上下净间距为 0.30 m；区域和 0.3 m 立方箱的水平位置按最新 Blender 人工布局固化到共享几何常量。
- 抓取区：位于左下方，水平中线与识别区2重合；位置及两个红球、两个蓝球的间距按最新 Blender 人工布局生成。
- 侧边箱体：从用户 Blender 编辑模式几何中恢复为独立 `manual_side_box`，并作为 Gazebo/RViz 实体障碍同步。
- 投递区：A/B/C/D 四个目标区。
- `meshes/ricam_arena.blend` 是可继续修改的 Blender 源文件。
- `maps/ricam_arena.yaml` 与 Gazebo 的碰撞墙/箱子共用同一组尺寸常量。
- `maps/ricam_arena_10cm_full_grid_all_numbered.png/json` 把整张 3.0 m × 2.5 m 地图划分为 30 × 25 个 10 cm 正方形，并按从左上到右下的逐行顺序标出 806 个唯一顶点；JSON 同时提供点列表、分组顶点、编号到 `map` 世界坐标的直接映射和 750 个方格的四顶点编号。可用 `rosrun ricam_arena_sim generate_numbered_grid.py` 重新生成。
- 默认启动 `move_base`，RViz 同时叠加 `/move_base/global_costmap/costmap` 和 `/move_base/local_costmap/costmap`；全局层使用静态地图与激光障碍，局部层使用 2 m × 2 m 滚动窗口和实时激光障碍。
- `move_base` 默认使用 `cym_planner/CymPlanner` 局部规划器；参考包原始参数保留在 `cym_planner` 中，当前仿真通过 `cym_planner_sim.yaml` 把最高线速度限制为 0.40 m/s、角速度限制为 1.00 rad/s。可用 `local_planner:=dwa_local_planner/DWAPlannerROS` 临时回退 DWA。
- 编号航点任务由 `numbered_waypoint_route.launch` 单独启动；主路线为 `91(1.30,1.05) → 711(1.30,-0.95) → 694(-0.40,-0.95)`，实际安全展开为 `91 → 400(1.20,0.05) → 392(0.40,0.05) → 640(0.40,-0.75) → 711 → 741(1.20,-1.05) → 708(1.00,-0.95) → 702(0.40,-0.95) → 694`。前半段绕开下方识别箱与东墙之间的窄通道，后半段先沿右侧向下转身，再上移到 `y=-0.95 m` 横向通道，避开底墙膨胀层；三个主航点顺序不变。节点启动前强制核对全局规划器为 `navfn/NavfnROS`、局部规划器为 `cym_planner/CymPlanner`，使用 `/move_base/make_plan` 返回的真实末端位姿连续预检每一段。除最终点外均为位置通过点：贴墙主点使用 0.12 m 容差，普通引导点使用 0.06 m；Mini2 在底墙转身点 741 单独使用 0.11 m 容差，避免前向较长的 footprint 在墙角原地转向。最终 694 必须由 move_base action 完整成功。RViz 的 `Numbered Waypoint Route` 图层显示完整展开路线。
- Gazebo planar 插件发布 `/odom` 和 `odom -> base_footprint`，与固定的 `map -> odom` 组成完整导航 TF；接入真实定位后应由定位系统接管 `map -> odom`。
- 物理步长为 0.001 s、更新率为 300 Hz，目标实时因子约为 0.3。
- 仿真加载 `mini2_description/urdf/mini2_sim.urdf`。该文件由随机器提供的原始 `mini2_description.urdf` 确定性生成，保留真实 STL 外观与机械拓扑，移除固定世界关节，并把高模碰撞替换为简化包围盒；原始 URDF 不修改。
- Mini2 零位外观包络约为 300.2 × 148.7 × 221.4 mm，位于 350 mm 立方体内，头部方向为模型 `+X`。
- 随包模型没有 transmission、关节控制器、步态控制器和可靠动力学参数，因此当前阶段锁定所有腿部及前部机构关节，并将基座设为 kinematic，以固定站姿配合 Gazebo planar 插件完成导航，避免墙角接触力把导航代理掀翻。它验证地图、感知接口和导航链路，不代表真实四足步态或碰撞动力学；接入真实步态前必须补齐关节限位、质量惯性、足端接触、低层控制与状态估计，并移除 kinematic/planar 代理。

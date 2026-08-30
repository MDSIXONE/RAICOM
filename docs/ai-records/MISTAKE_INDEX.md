# 犯错记录索引

错误条目的完整内容在 `mistakes/YYYY-MM-DD.md`，本文件只做索引。读取/写入时机由 `project-memory-records` 技能定义。

## 主题索引

- ROS TF/坐标变换（tf1 vs tf2）：2026-08-08.md
- 运动限幅与运动标定：2026-08-08.md、2026-08-04.md
- ROS 包管理与 launch 节点解析：2026-08-08.md
- WSLg 显示/共享内存：2026-08-08.md
- 进程管理（pkill/重连/双实例）：2026-08-08.md、2026-08-14.md、2026-08-16.md、2026-08-17.md
- 导航与代价地图边界：2026-08-08.md
- 雷达滤波/遮挡标定：2026-08-08.md
- WSL 网络 IP/跨机器联调：2026-08-08.md、2026-08-03.md
- ROS 日志排障（__log/ANSI）：2026-08-08.md
- 数据集生成与文件名模式：2026-08-07.md
- 终端交互（raw 模式/SSH 按键）：2026-08-05.md、2026-08-04.md
- 跨 Shell 转义/CRLF：2026-08-05.md、2026-08-03.md、2026-08-15.md、2026-08-16.md
- Catkin 工程结构/头文件路径：2026-08-05.md、2026-08-02.md
- 串口控制权/systemd 就绪：2026-08-04.md、2026-08-03.md
- ROS 安全边界与授权：2026-08-03.md
- RViz 配置：2026-08-03.md
- Git/GitHub 配置与凭据：2026-07-30.md、2026-08-02.md
- 凭据扫描：2026-08-02.md
- Docker 镜像校验：2026-08-02.md
- ROS 环境初始化/容器边界：2026-08-02.md
- 供应商 SDK 集成：2026-08-02.md
- 硬件安全边界（端口/时间）：2026-08-02.md
- 轮毂电机驱动诊断：2026-08-08.md、2026-08-11.md、2026-08-13.md
- HTTP 轮控刷新频率：2026-08-13.md
- Python OpenCV 运行时依赖：2026-08-13.md
- 机械臂姿态/车体低趴顺序：2026-08-14.md
- 机械臂安全动作顺序：2026-08-14.md
- XGO 机械臂运行时限幅：2026-08-14.md
- xgolib 关节反馈读取：2026-08-14.md
- SSH 长时进程/stdout 管道：2026-08-14.md
- XGO 多舵机同步/串口发包：2026-08-14.md
- XGO 固件模式残留/测试脚本状态恢复：2026-08-16.md
- launch env 覆盖/roslaunch auto-master：2026-08-15.md
- 部署丢可执行权限：2026-08-15.md
- WSL 后台进程生命周期：2026-08-15.md
- CRLF 污染脚本：2026-08-15.md（另见 2026-08-03）
- IMU 绝对 yaw 当坐标基准：2026-08-15.md
- 激光扫描点转换符号与标准约定相反：2026-08-15.md
- XGO 运动步进死区/cmd_vel 桥映射：2026-08-08.md、2026-08-15.md
- 桥 yaw 优先分支/速度映射实测：2026-08-15.md
- 导航规划失败/地图未知区排查：2026-08-08.md、2026-08-15.md
- Codex 终端进程权限：2026-08-16.md
- odom/里程计方案（foot 步态无编码器、打滑）：2026-08-16.md、2026-08-17.md
- IMU 跳变过滤阈值/传感器特性：2026-08-17.md
- TF 死锁/发布时序环：2026-08-17.md
- 容器重建（设备直通/apt 包丢失）：2026-08-17.md
- libcamera 容器枚举/udevd 依赖：2026-08-17.md
- 树莓派硬件库容器检测绕过：2026-08-17.md
- Python venv 包安装形态（editable/system-site）：2026-08-17.md
- xgolib IMU 批量读协议（0x65）与固件版本不匹配：2026-08-17.md
- ROS Noetic arm64 无 cartographer 预编译包：2026-08-17.md
- 部署遗漏（改版后未重新部署容器旧版运行）：2026-08-17.md
- 第三方节点参数传递方式（gflags vs ROS param）：2026-08-17.md

## 按日期

### 2026-07-30

- GitHub CLI 登录未配置 Git 推送凭据
- 改动记录误写入模板
- 推送 GitHub Actions 文件缺少 workflow 权限

### 2026-08-02

- 仓库未配置 Git 作者身份
- 设备源码含硬编码云服务凭据
- 凭据扫描未覆盖多行与非 API_KEY 命名
- Docker 29 镜像 ID 校验假设不成立
- ROS Noetic 初始化脚本不兼容 Bash nounset
- ROS 基础镜像不提供 roslaunch-check
- ROS 工作区校验遗漏容器边界
- Catkin 链接不自动提供头文件路径
- YDLIDAR SDK 命名空间与示例不一致
- 雷达测试缺少端口与时间硬边界

### 2026-08-03

- 监听控制端口不等于拥有底盘串口
- ROS 速度话题不能作为真实运动授权边界
- 未验证的底盘接口不能接收键盘速度
- ROS 1 跨机器可视化不能只开放 Master 端口
- WSL 启动脚本必须使用 LF 换行
- RViz Marker 显示使用专用话题字段
- PowerShell 管道向 WSL 传入 Bash 脚本携带 CRLF

### 2026-08-04

- 普通 SSH 终端不能直接报告按键松开
- 前后与原地转向不能共用未经标定的 XGO 强度
- systemd active 不代表控制服务已经可连接

### 2026-08-05

- raw 模式下 Ctrl-C 不产生 SIGINT
- PowerShell 远程部署命令的变量转义不能依赖嵌套引号
- 新增 Catkin 包目录遗漏 src 层级

### 2026-08-07

- 数据集通配符包含诊断图片

### 2026-08-08

- gmapping 用 tf1 不读 /tf_static，静态 TF 发布者导致建图只有首图
- simple_odom 位移限幅按低速设计，foot 步速超限导致位置静默不更新
- ros-noetic-slam-gmapping 是空 wrapper，可执行文件在 gmapping 包
- WSLg 窗口 COPY MODE：fstab 自动挂载是概率性方案
- pkill -f 会匹配到 SSH 会话自身的命令行
- C++ 节点不自动重连 master，且重复 roslaunch 造成双实例
- 导航 goal 超出地图边界导致规划永远失败
- 雷达遮挡滤波不要凭猜测改方向，先实测遮挡范围
- WSL 局域网 IP 由 DHCP 动态分配，跨机器 ROS 联调须先确认
- XGO 固件运动步进死区：yaw 小于 12 的动作不执行
- 机器驱动布局不对称：仅左侧两轮有驱动，wheel 模式转向打滑不可用
- 容器内 C++ 节点 __log 日志文件缺失

### 2026-08-11

- XGO-mini3W 右侧轮误判为被动轮

### 2026-08-13

- 左后轮当前无法驱动，与 2026-08-11 四轮均可驱动结论冲突
- curl 单请求循环未达到 10Hz 轮控刷新
- ball_green.py 缺少 Python cv2 依赖

### 2026-08-14

- 低趴车体指令会复位机械臂接球姿态
- 大臂 53 的 +120 指令被 xgolib 钳制到 +90
- 大臂动作前必须先抬小臂
- xgomini 运行库 read_motor 无法解析 15 个舵机反馈
- SSH stdout BrokenPipeError 终止长时抓球程序
- xgolib motor 列表接口不是原子多舵机同步

### 2026-08-15

- launch env 硬编码 local_master_ip 覆盖命令行 export
- scp/docker cp 覆盖部署丢可执行权限
- WSL 后台进程随 wsl.exe 返回被清理
- CRLF 污染仓库 shell/Python 脚本
- simple_odom 用 IMU 绝对 yaw 当基准导致机器朝向斜
- cmd_vel 桥 x 步长死区 + yaw 优先分支导致实机"只转不走"
- 实机建图未扫全：右下角未知区导致 navfn 规划失败

### 2026-08-16

- Codex 工作区命令 CreateProcessAsUserW 错误 5
- CRLF 污染 scp 部署的 Python 脚本：shebang `python3\r` 使 roslaunch 启动失败（复现 2026-08-15 同类）
- 测试脚本修改 XGO 固件模式（enable_wheel_control）后未恢复，导致后续 move_x 全部失效
- ssh 远程一键命令里 pkill -f 匹配到远程 shell 自身命令行，命令中断无输出（复现 2026-08-08 同类）

### 2026-08-17

- simple_odom yaw_jump_limit=0.4 丢弃脉冲式真实转向：odom 方向漂移 (4.88,2.49) vs 实际 (2.03,-0.19)
- TF 发布者与消费者互相等待死锁（odom_from_amcl 等 amcl_pose、AMCL 等 laser→odom TF）
- foot 步态机器人用 cmd_vel 积分 odom 不可信（无编码器打滑，架构级教训）
- Docker update 不支持 --device-add：设备变更必须重建容器
- 容器重建丢失容器内 apt 安装的包（cv_bridge），需重装
- libcamera 容器内枚举相机依赖 udevd（/run/udev/data 数据库），缺之静默为空
- rpi-lgpio 硬件检测容器内失败，用 RPI_LGPIO_REVISION 环境变量绕过
- 厂商 venv 是 system-site-packages 且 uiutils 为 editable install：extra.pth 兜底不处理内层 .pth，需直接加 src 路径
- pkill -f roslaunch 匹配 docker exec 自身命令行（复现 2026-08-08/16 同类）
- xgolib read_imu() 0x65 批量读在 M-7.0.0b8 固件返回固件版本串（无 accel/gyro，需源码验证协议）
- ROS Noetic 官方 apt 无 arm64 cartographer 预编译包（需源码编译）
- 脚本改版后漏部署真机/容器导致实机跑旧版（imu_bridge fetch failed: 'accel'）
- cartographer_node 1.0.0 用 gflags 命令行参数不读 ROS param（launch 需用 node args）

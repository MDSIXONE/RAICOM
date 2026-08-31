# robot_dog_follow_line

本次睿抗巡线（黑线跟随）任务的代码存放包。脚本为厂商原版示例（仅调整 shebang 位置），
统一在机器端 `ros-noetic` Docker 容器内运行（与导航同一容器，不再宿主机/容器割裂）：

| 程序 | 说明 |
| --- | --- |
| `follow_line.py` | 巡线程序：Picamera2 视觉识别黑色巡线 → PID 控制转向/前进 |

## 运行环境

程序统一在机器端 `ros-noetic` Docker 容器内运行（容器挂载 `/home/pi` 后厂商
`xgovenv` 同路径可用），依赖：

- `picamera2`、`cv2`、`numpy`
- `uiutils`、`xgolib`、`xgoscreen`（厂商库）

容器需挂载 `/home/pi` 并直通 `/dev/ttyAMA0`（串口）与 `/dev/video0`（相机），
详见 `docs/technical/2026-08-16-docker-runtime-unification.md`。厂商 `xgovenv`
为唯一可用运行时；系统 Python 缺少 `uiutils`/`xgolib`，不可用。

## 脚本行为要点

- HSV 黑色掩码 `[0,0,0]`~`[180,255,30]` 提取黑线，画面上半部分清空
  （`img[0:5*height/8, :] = 0`），掩码范围需按光照条件调节。
- **左右裁剪**：只保留 `crop=[left_x, right_x]`（绝对像素 0~319）区间内的线，
  区间外置零——多线场地只跟中间一条，避免误跟到旁边的线；默认全宽 `[0,319]`。
- **默认低趴姿态**（`translation z=10`、`attitude p=15`，与抓球接近姿态一致）：
  站立姿态（z=75）视角太远，低趴后相机俯视近处地面，黑线更清晰。
- 找最大轮廓 → 最小外接矩形/最小外接圆，取圆心横坐标作为偏差。
- 偏差送入 PID（P=50、I=0、D=30）计算转向量 `z_pid`：
  - `abs(z_pid) < 8`：直行 `move_x(18)`；
  - `abs(z_pid) >= 8`：按偏差方向 `turn()` 转向 + `move_x(15)`，并按偏差调整时长；
  - 未检测到线条（丢线）：**立即停止**（`dog.stop()`），重新看到线后自动恢复
    巡线（PID 重置全新启动；2026-08-30 修复：原厂代码丢线时误判为线在最左侧
    而转向+前进，实机表现为乱走；后按用户决策由"原地转圈寻找"改为"丢线即停"）。
- XGO 初始化自动识别机型（`read_firmware()` 读固件首字符，`M` → xgomini，否则 xgolite）。
- 板载按钮切换状态：A 巡线 / C color / D init；B 退出程序。
- **足式转向=一次一个动作**：xgolib 源码确认 move_x 发 VX、turn 发 VYAW，固件后发
  覆盖先发——原厂 turn+move_x 连发会被吞掉转向（实机只前进不转向）。已改为
  `turn → sleep → turn(0) → move_x(短) → stop` 分步执行。
- **轮式/足式切换**：`m` 键。wheel 模式 `enable_wheel_control(1)` + 四通道差速
  `wheel_control([LF,RF,RR,LR])`（128=停、>128 前进；base=145，差速 clamp ±40）；
  丢线/退出按模式停轮（128）。
- **转向序列锁轮（2026-09-01）**：`lock_wheels`（默认 true）在雷达后方转向序列
  （右转90°→停2s→左转90°回正）期间锁 4 轮——右转前 `enable_wheel_control(1)` +
  `wheel_control([128,128,128,128])` 抱死防转向时轮子滑动漂移，左转回正完成后
  `enable_wheel_control(0)` 解锁（平时行进不锁，避免拖慢速度；2026-08-16 实测
  锁轮+move_x 可用）；退出自动恢复 `enable_wheel_control(0)` 防残留（2026-08-16 教训）。
- **弯道右转 = IMU yaw 闭环（2026-09-01）**：线宽突变（`raw_line_w > 95px` 连续
  3 帧）触发右转 90° 时不再盲转固定时长（`turn(-16)×4.2s` 开环——转弯时机器
  摇晃看不到线也照转，转多转少无反馈），改为读机载 IMU yaw 累积角（0x66 单轴，
  度，相对变化即转角）闭环：`|yaw 变化| ≥ 90°` 立即 `turn(0)` 停。目标角度
  `surge_turn_deg`、速度 `surge_turn_speed`、超时 `surge_turn_timeout` 可调；
  读取失败/超时立即停转并报错（不静默盲转）。
- **弯道右转（默认）= 雷达后方第一个右转定位（2026-09-01，替代旧 armed+rising）**：
  依赖雷达后方距离桥（`run_lidar_rear_bridge.sh`，/scan 正后±15° 中位距离 →
  HTTP :8767/rear）。两阶段：
  - 阶段1（识别第一个右转）：正常巡线中，**曾见 rear > 2.0m（起点后方开阔）后，
    首次 rear < 1.0m** → 判定为第一个右转，开启功能（只一次）。
  - 阶段2（转向序列，可多次）：功能开启后 rear **依次增大到 ≥ 0.75m、≥ 1.5m**
    （`rear_turn_at_steps_m=[0.75, 1.5]`）各执行一次 IMU yaw 闭环
    **右转 90° → 停 2s → 左转 90° 回正 → 继续巡线**（全部完成不再触发）。
    **第1次触发前加 yaw 验证**：相对阶段1识别时刻的 yaw 基准已转过 ≥
    `rear_yaw_min_deg`（默认 80°，防刚转角就触发）；第2次起不要求（车已过弯）。
  - 参数 `rear_dip_from_m`/`rear_dip_to_m`/`rear_turn_at_steps_m`/`rear_yaw_min_deg`/
    `rear_turn_deg`/`rear_hold_s` 可写入 follow_line_config.json；线宽突变默认关闭
    （`use_line_surge`）。
- **双路 8090/8091 推流**：`http://192.168.137.157:8090/stream.mjpg` = 带框原画面
  （FOLLOW+mode+`lw/raw/阈值` 水印）、`http://192.168.137.157:8091/stream.mjpg` = 阈值二值画面
  （MASK V/crop + 线宽水印）；终端每 0.3s 打 `[线宽] lw=… raw=…/阈值`。浏览器开两个标签页并排同时看；跑前须停 oumax-camera
  释放 8090 与相机（8091 无冲突）。
- **边走边调**（SSH 终端，raw 单键即时生效）：`p`/`o` P ±1、`R`/`F` P ±50、
  `i`/`u` D ±0.1、`[`/`]` 直行速度 ±1、`-`/`=` 转向速度 ±1、**`t` 切换转向方向**、
  **`m` 轮/足式切换**、**`s` 保存参数到 follow_line_config.json（下次启动即默认）**、
  Ctrl-C 退出；每次按键打印当前
  `P/D/V/crop/spd/dir` 及 mode。**PID 目标 = 裁剪窗中心**
  （crop 不对称时不再是 160，否则线在裁剪窗中心也有固定偏差、P 越大越偏）；
  **默认 P=396/D=30**（2026-08-30 实机标定，基本巡线；P 的 Kp=P/1000，
  直行阈值 8 对应 ~20px 偏差），灯光变化时用 `R`/`F` 微调。转向方向不对时按
  `t` 切换（`dir=+/-`）。退出自动 `dog.stop()`。
  速度默认已降：直行 `move_x(8)`、转向 `move_x(6)`，实机过快用 `]`/`=` 再降。
  **调好的运动参数（PID/速度/方向/模式/轮速）按 `s` 保存后**，下次启动
  `follow_line.py` 自动作为默认值，无需重调。

## 阈值与裁剪配置（follow_line_config.json）

`follow_line.py` 启动时读取**同目录** `follow_line_config.json`，缺失则用默认并
打印提示。格式：

```json
{
  "lower": [0, 0, 0],
  "upper": [180, 255, 30],
  "crop": [0, 319],
  "line_width": [5, 150],
  "pid": [396.0, 0, 30.0],
  "straight_speed": 8,
  "turn_move_speed": 6,
  "direction": 1,
  "mode": "foot",
  "wheel_base": 145,
  "lock_wheels": true
}
```

- 视觉字段（`lower`/`upper`/`crop`/`line_width`）：用 `follow_line_tune.py`（见下）
  调好并按 `q` 保存后自动生成；HSV 的 H/S 保持全范围即可，实际主要调 V 上限
  （黑色判定的亮度阈值）。
- 运动字段（`pid`/`straight_speed`/`turn_move_speed`/`direction`/`mode`/
  `wheel_base`）：由 `follow_line.py` **边走边调按 `s` 保存**（也可手工编辑）；
  下次启动自动作为默认值，与视觉字段同文件。
- 旧配置缺运动字段时自动补默认（兼容），`follow_line_tune.py` 保存视觉参数时
  原样保留运动字段，不会覆盖。

## 部署与运行

```bash
# 上传到机器（脚本为机器端独立程序，非 ROS 节点）
scp scripts/follow_line.py pi@192.168.137.157:/home/pi/oumax-xgo/

# 容器内运行（默认直接指向机器上厂商 demos 原版目录亦可）
docker exec ros-noetic /home/pi/RaspberryPi-CM5/xgovenv/bin/python \
  /home/pi/oumax-xgo/follow_line.py
```

运行前注意：先停 `raicom-original-main.service` 与 `oumax-camera.service`
（原厂主服务占 SPI/串口、相机服务占 Picamera2，会导致 xgolib 挂死或相机打不开），
结束后可恢复。

## 调参工具（follow_line_tune.py，狗只摆姿态不走）

机器端运行（需 SSH 交互终端），8090 推流（**不用 LCD**——LCD 走 SPI 会与原厂
main.py 并发死锁，2026-08-30 两次实机复现）：
电脑浏览器打开 `http://192.168.137.157:8090/` 看"原图+红白二值掩码+裁剪边界"画面。

```bash
scp scripts/follow_line_tune.py pi@192.168.137.157:/home/pi/oumax-xgo/
ssh pi@192.168.137.157
cd /home/pi/oumax-xgo
./follow_line_tune.py
```

- 自动停 `raicom-original-main` + `oumax-camera`（SPI/LCD 与相机互斥，2026-08-30
  教训：只停相机不停止 SPI 死锁），退出按启动前状态恢复。
- **调参时狗摆成巡线同款低趴姿态**（z=10/p=15，相机俯视近处地面，与正式巡线
  视角一致），不做行走动作；退出自动 `dog.reset()` 复位站立。
- 按键：`w/s` V 上限±10、`1/2` V 上限±1、`a/d` V 下限±10、`z/x` 左裁剪±10、
  `c/v` 右裁剪±10、`q` 保存退出、`Q`/Ctrl-C 不保存退出。
- 画面二值图为红白高对比 + TUNE 水印，与 oumax-camera 的原始流可区分；
  裁剪边界在原图上有紫线标注。

## 主流程2（备选主流程：开始任务后直接巡线）

主流程1（导航 5 点 → 抓球放球）行不通时使用：机器端一键脚本
`host/run_main_flow2.sh`，自动完成"停占串口/相机的服务 → 直接进入黑线巡线"，
跳过定点巡航导航。

```bash
# 部署到机器（仅首次）
scp host/run_main_flow2.sh pi@192.168.137.157:/home/pi/oumax-xgo/

# 机器端执行（开始任务后直接巡线；B 键或 Ctrl-C 退出）
bash /home/pi/oumax-xgo/run_main_flow2.sh
```

说明：脚本用宿主机 xgovenv 前台运行 follow_line.py（容器 ros-noetic 未直通
`/dev/ttyAMA0`，串口需宿主机权限）；运行中不自动恢复已停服务，巡线结束后
如需其他程序再手动恢复。解释器/脚本路径可用环境变量 `RAICOM_XGO_PYTHON`、
`RAICOM_FOLLOW_LINE` 覆盖。

## 相关文件

- 来源：`archive/full-device-source/home-pi/RaspberryPi-CM5/robots/Mini3W_W/demos/follow_line.py`
  （与 Dog_LM 版本 SHA-256 完全一致，均为 11864 字节；本包副本仅将 shebang
  移到文件首行并改为 `python3`，其余代码未改动）。

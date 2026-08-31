# 代码改动记录

## 2026-09-01｜直行速度 10 → 5（锁轮改回仅转向序列，无需大速度补偿）

- 状态：改动完成（已改机器配置）
- 目标：锁轮改为仅转向序列后平时不锁轮，用户把直行速度降回 5。
- 影响文件：机器 `follow_line_config.json` `straight_speed 10→5`；备份
  `backups/follow_line_config.json.*`；本记录。
- 验证：JSON 合法；须重启 follow_line 生效。

## 2026-09-01｜锁轮时机改为仅在转向序列（右转前锁、回正后解锁）

- 状态：改动完成（已部署）
- 目标：用户反馈全程锁轮拖慢速度；改为只在转向序列（右转90°→停2s→左转90°回正）
  期间锁轮——右转前先锁（防转向时轮子滑动漂移），左转回正完成后解锁，平时行进不锁。
- 影响文件：`follow_line.py`：
  - `execute()` 移除两处 `lock_wheels_now()`（行进中不再锁）
  - `lock_wheels_now()` 改为 enable_wheel_control(1) + wheel_control(128)；新增
    `unlock_wheels()`（enable_wheel_control(0) 恢复默认）
  - `start_rear_turn_seq()`：开头锁轮、左转回正后解锁（中断/超时也会走到解锁？
    否——turn_closed_loop 内部失败会停转返回，但解锁在 ok_l 之后，若右转超时返回
    False 仍继续执行左转和解锁；若左转异常抛错则不解锁，由退出 finally 的
    enable(0) 兜底）
  - 启动/切回 foot 不再无条件 enable(1)（仅 wheel 模式）
  - 退出 finally 保留 enable_wheel_control(0) 恢复兜底
- 验证：py_compile；9 逻辑用例全 PASS；已部署机器（scp + 机器端 py_compile OK）。
- 遗留风险：转向序列期间锁轮若使 turn 异常（实测 lock+move_x 可用，turn 未单独
  验证），解锁在左转后；异常路径由退出恢复兜底。

## 2026-09-01｜锁轮后直行速度 6 → 10（补偿轮锁阻力）

- 状态：改动完成（已改机器配置）
- 目标：用户反馈锁轮后速度变小，要求加大前进速度。
- 影响文件：机器 `follow_line_config.json` `straight_speed 6→10`；备份
  `backups/follow_line_config.json.*`；本记录。
- 验证：JSON 合法；须重启 follow_line 生效；现场可用 `[`/`]` 键 ±1 微调（按 s 保存）。
- 遗留风险：速度加大会影响 PID 跟随（弯道可能跟不上）；turn_move_speed 保持 4 未动。

## 2026-09-01｜巡线行进中锁 4 轮（lock_wheels）：防轮子自由滚动漂移

- 状态：改动完成（已部署）
- 目标：用户要求 foot 巡线行进过程中锁住 4 个轮子（防步态行走时轮子自由滚动漂移）。
- 影响文件：
  - `follow_line.py`：新增 `DEFAULT_LOCK_WHEELS=True`（config 可写 `lock_wheels`）；
    foot+lock 启动/切回时 `enable_wheel_control(1)`；`lock_wheels_now()` 在每次
    move_x 前发 `wheel_control([128,128,128,128])` 抱死；`switch_mode` 切回 foot 时
    按 lock 保持 enable(1) 并立即锁轮；退出 finally 恢复 `enable_wheel_control(0)`
    （防 2026-08-16 wheel 模式残留导致后续 move_x 失效）
  - 机器 `follow_line_config.json`：新增 `lock_wheels: true`
  - 本记录
- 实施记录：复用 2026-08-16 实测结论"锁轮(128)+move_x 可用"；左后轮（通道3）硬件
  故障不影响锁轮；wheel 模式差速不受影响（lock 只在 foot 生效）。
- 验证：py_compile；既有 9 逻辑用例全 PASS（锁轮不影响雷达状态机）；已部署机器
  （scp + 机器端 py_compile + JSON 合法）。
- 遗留风险：锁轮不显著改善位移重复性（2026-08-16 实测）；enable(1)+move_x 组合若
  实机 move_x 失效需回退 lock_wheels=false；退出恢复 enable(0) 已兜底残留。

## 2026-09-01｜修复日志 f-string 崩溃：完成后 next_at '--' 应用 :.2f → ValueError

- 状态：改动完成（已部署）
- 目标：实机运行到两次转向序列完成后崩溃 "ValueError: Unknown format code 'f' for
  object of type 'str'"（摄像头已停止）。
- 影响文件：`follow_line.py` `check_rear_trigger`：step 完成检查提前到函数开头
  （`_rear_turn_step >= len(...)` 直接短路返回 False）——process() 内调用无 step
  前置条件，不提前返回会走到日志行；日志行 `next_at` 去掉三元表达式 '--'（开头
  短路后不可能为 '--'）。
- 实施记录：主循环调用有条件 `_rear_turn_step < len(...)` 保护，但 process() 里
  `if self.check_rear_trigger():` 无保护，完成后仍调用 → 日志行 f-string 对字符串
  '--' 应用 :.2f 崩溃；日志 0.3s 节流使测试首帧后不打日志，掩盖了该 bug（实机
  持续运行 0.3s 后暴露）。
- 验证：py_compile；9 逻辑用例全 PASS（新增"完成后调用不崩"回归用例：清零日志
  节流强制打日志验证短路）；已部署机器。
- 遗留风险：无。

## 2026-09-01｜雷达后方 yaw 验证阈值 80° → 30°（80°实机达不到）

- 状态：改动完成（已部署）
- 目标：用户要求"30试试"——80° 实机弯道幅度仅 ~30°，第1次转向永不触发（无触发
  行为）；降为 30°。
- 影响文件：`follow_line.py` `DEFAULT_REAR_YAW_MIN_DEG 80→30`；机器
  `follow_line_config.json` `rear_yaw_min_deg 80→30`；已 scp。
- 验证：py_compile；机器端 py_compile + JSON 合法。
- 遗留风险：30° 是否仍偏保守/足够防"刚转角就触发"，实机观察。

## 2026-09-01｜巡线 crop 放宽到左右各剪 50px：[50,269]

- 状态：改动完成（已改机器配置）
- 目标：yaw 验证版乱跑——crop [60,259] 太窄导致弯道丢线循环、yaw 累积不到 80°
  锁死第1次转向；用户决定放宽到左右各剪 50px。
- 影响文件：机器 `follow_line_config.json` `crop [60,259] → [50,269]`；备份
  `backups/follow_line_config.json.*`；本记录。
- 验证：JSON 合法；须重启 follow_line 生效，重点观察日志"等 yaw"能否累积到 80°。

## 2026-09-01｜雷达后方第1次转向序列加 yaw 验证：转过≥80°才允许触发

- 状态：改动完成（已部署）
- 目标：用户实机发现第1次转向序列在"刚到转角"就触发（rear≥0.75 条件在弯道入口即
  满足），要求加 yaw 验证——至少转过 80° 再开启第1次。
- 影响文件：
  - `follow_line.py`：新增 `DEFAULT_REAR_YAW_MIN_DEG=80.0`（config 可写
    `rear_yaw_min_deg`）；阶段1（dip）触发时记录 yaw 基准 `_rear_yaw0`；阶段2第1次
    （step 0）触发前校验 |yaw-yaw0| ≥ rear_yaw_min_deg，未满足打"等 yaw"（0.5s 节流）、
    满足打"yaw 验证通过"；第2次起不要求；yaw0 读取失败/缺失则不触发第1次（full exposure）
  - 机器 `follow_line_config.json`：新增 `rear_yaw_min_deg: 80.0`
  - `README.md`/`docs/launch-commands.md`/`docs/lingo.md`：文档同步
  - `tmp/test_rear_trigger.py`：harness 支持 (rear, yaw) 序列 + dog.read_yaw mock
- 实施记录：yaw 基准取阶段1识别瞬间（dip_done 置位时 read_yaw），后续车巡线过弯累积
  转角；abs 判断方向不敏感。第2次（1.5m）在首次执行（右转90°→左转90°回正）之后，
  车已过弯，不再要求 yaw。
- 验证：py_compile；8 逻辑用例全 PASS（含"yaw 未转够阻止第1次/转够后触发"、
  "yaw 始终不转够则不触发"）；已部署机器（scp + py_compile + JSON 合法）。
- 遗留风险：yaw0 读取失败则第1次永不触发（报错可见）；80° 阈值实机可能需调
  （0.5s 节流日志可见差多少）。

## 2026-09-01｜雷达后方转向序列改为两次触发：rear 依次≥0.75m、≥1.5m

- 状态：改动完成（已部署）
- 目标：用户要求"两次：0.75 一次、1.5 一次"——转向序列执行两次，触发距离依次为
  0.75m、1.5m（替代单次 0.75m）。
- 影响文件：
  - `follow_line.py`：`DEFAULT_REAR_TURN_AT_M` 单值 → `DEFAULT_REAR_TURN_AT_STEPS_M=[0.75, 1.5]`；
    `_rear_turn_done` → `_rear_turn_step`（已执行次数/下一阈值索引）；阶段2按 steps
    依次触发，全部完成不再触发；日志显示 step/next_at
  - 机器 `follow_line_config.json`：`rear_turn_at_m` → `rear_turn_at_steps_m: [0.75, 1.5]`
  - `README.md`/`docs/launch-commands.md`/`docs/lingo.md`：文档同步
  - `tmp/test_rear_trigger.py`：6 用例（含两次触发场景）
- 实施记录：每次触发执行完整转向序列（右转90°→停2s→左转90°回正），阻塞期间不轮询；
  第一次（0.75）完成后车回正继续巡线，rear 再增大到 1.5 触发第二次。
- 验证：py_compile + 6 逻辑用例全 PASS（缓慢下降两次触发、两次执行后停止、只触发一次等）；
  已部署机器（scp + py_compile + JSON 合法）。
- 遗留风险：dip 触发瞬间若 rear∈(0.75,1.0) 会立即第一次转向；0.75 与 1.5 之间若
  rear 波动来回穿越，只按首次 ≥ 阈值触发一次（step 递增不回溯）。

## 2026-09-01｜雷达后方转向触发距离 1.5m → 0.75m（rear_turn_at_m）

- 状态：改动完成（已部署）
- 目标：用户要求把阶段2转向触发距离 1.5m 改为 0.75m。
- 影响文件：`follow_line.py` `DEFAULT_REAR_TURN_AT_M 1.5→0.75`；机器
  `follow_line_config.json` 新增 `rear_turn_at_m: 0.75`；已 scp 至机器。
- 实施记录：注意 0.75 < rear_dip_to_m(1.0)：若 dip 触发瞬间 rear∈(0.75,1.0) 会
  立即满足阶段2（马上转向）；若 rear<0.75 则等增大到 0.75。
- 验证：py_compile OK；机器 grep 0.75；JSON 合法。
- 遗留风险：0.75 触发点较近，转向序列开始时机变早；实机看效果。

## 2026-09-01｜巡线恢复最小线宽 25、crop 左右各剪 60px：[60,259]

- 状态：改动完成（已改机器配置）
- 目标：用户要求恢复最小线宽（50→25），裁剪加大到左右各 60px。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line_config.json` `line_width [50,150] → [25,150]`、
  `crop [40,279] → [60,259]`（有效宽 200px）；备份 `backups/follow_line_config.json.*`；
  本记录。
- 实施记录：crop 中心 (60+259)/2=159.5 不变，PID 目标不受影响。
- 验证：JSON 合法；须重启 follow_line 生效。

## 2026-09-01｜巡线 crop 左右各剪 40px：[40,279]

- 状态：改动完成（已改机器配置）
- 目标：用户实测后定：左右各裁剪 40px 避开旁边黑色。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line_config.json` `crop [10,309] → [40,279]`
  （有效宽 240px）；`line_width` 保持 [50,150]；备份 `backups/follow_line_config.json.*`；
  本记录。
- 实施记录：crop 中心 (40+279)/2=159.5 与 [10,309] 相同，PID 目标不变。
- 验证：JSON 合法；须重启 follow_line 生效。

## 2026-09-01｜巡线 crop 恢复左右裁剪 [10,309]（全宽误跟旁边黑色）

- 状态：改动完成（已改机器配置）
- 目标：全宽 [0,319] 实测把旁边的黑色物体误识别进视野，用户要求剪掉左右两边。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line_config.json` `crop [0,319] → [10,309]`；
  `line_width` 保持 [50,150]（上一条改动保留）；备份
  `backups/follow_line_config.json.*`；本记录。
- 验证：JSON 合法；须重启 follow_line 生效。
- 遗留风险：裁剪回 [10,309] 后弯道丢线风险回到上上条水平；如仍误跟可现场用
  follow_line_tune.py 的 z/x/c/v 调裁剪（q 保存）。

## 2026-09-01｜巡线 line_width 下限 25→50（过滤弯道伪线）

- 状态：改动完成（已改机器配置）
- 目标：用户现场观察后判断丢线由小线宽目标误识别引起（弯道处 lw 41-47 抖动、正常
  段 58-69），要求最小线宽改为 50 过滤伪线。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line_config.json` `line_width [25,150] → [50,150]`；
  备份 `backups/follow_line_config.json.*`；本记录。
- 验证：JSON 合法；须重启 follow_line 生效，实机看弯道是否还丢线。
- 遗留风险：下限 50 后正常线如果受光照变细（<50px）会被过滤成丢线；V=120 上限
  阈值不变。

## 2026-09-01｜巡线 crop 放宽到全宽 [0,319]（防弯道丢线）

- 状态：改动完成（已改机器配置）
- 目标：用户反馈第一个右转处弯道丢线（PID 跟不上、线跑出裁剪区），要求左右画面
  全部放宽到最大。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line_config.json` `crop [10,309] → [0,319]`；
  本机代码默认值本就是 `DEFAULT_CROP=[0,319]` 无需改。备份
  `backups/follow_line_config.json.20260901_005522`；本记录。
- 实施记录：crop 中心 (0+319)/2=159.5 与 [10,309] 相同，PID 目标不变；8090 推流
  显示未裁剪原图，crop 只影响检测区（8091 阈值画面可见）。
- 验证：JSON 合法；须重启 follow_line 生效，实机看弯道是否还丢线。
- 遗留风险：全宽后旁线/场地边更容易进视野误跟（08-31 放宽时的已知风险）。

## 2026-09-01｜修复雷达桥 pkill 自匹配：容器内逻辑拆独立脚本

- 状态：改动完成（已部署并实测）
- 目标：run_main_flow2.sh 合并雷达桥后实机卡死在"starting rear lidar bridge"。
- 影响文件：
  - 新增 `robot_dog_follow_line/host/lidar_rear_bridge_inner.sh`（容器内执行：起
    roscore/雷达/http；source ROS 环境时临时关 -u 防 nounset 报错）
  - `robot_dog_follow_line/host/run_lidar_rear_bridge.sh`：改 docker exec 调内层
    脚本（原 bash -lc 长字符串里 `pkill -f lidar_rear_range_http.py` 匹配 bash -lc
    自身 argv 被杀）
  - `docs/launch-commands.md` §2/§3.2 部署清单补 inner 脚本；mistakes 记录
- 实施记录：拆独立脚本后 argv 只含脚本路径、脚本内容不进 argv，pkill -f 不再自匹配；
  内层脚本 `set -u` 下 source setup.bash 报 `ROS_MASTER_URI: unbound variable`，改
  source 时 set +u。
- 验证：本机/机器 bash -n；实测 `run_lidar_rear_bridge.sh` 输出 bridge-ok +
  `{"ok":true,"rear_m":0.104}`；二次运行幂等复用。
- 遗留风险：无新增（雷达桥功能不变）。

## 2026-09-01｜主流程2 合并雷达后方桥：一条指令跑带雷达定位的巡线

- 状态：改动完成（已部署）
- 目标：用户要求把雷达桥启动合并进主流程2，减少操作指令。
- 影响文件：
  - `robot_dog_follow_line/host/run_main_flow2.sh`：停服务后、启动巡线前自动
    `bash run_lidar_rear_bridge.sh`（容器内 roscore+雷达+HTTP :8767）；新增
    `RAICOM_REAR_BRIDGE` 环境变量覆盖；雷达桥失败（容器未起等）→ 脚本中止
    （set -e，full exposure 不静默降级）
  - `docs/launch-commands.md` §2、`docs/lingo.md`「主流程2」词条：文档同步
- 实施记录：桥脚本幂等（已起则复用）；桥在停服务之后、巡线之前拉起；部署列表补
  `run_lidar_rear_bridge.sh`；前置条件补"容器 ros-noetic 运行中"。
- 验证：本机 `bash -n` 通过；已 scp 至机器 `/home/pi/oumax-xgo/`（md5 一致）。
- 遗留风险：雷达桥依赖容器 ros-noetic 已启动；巡线退出后服务仍不自动恢复。

## 2026-09-01｜雷达后方第一个右转定位：rear 突降开启功能，rear≥1.5m 右转90°→停2s→左转90°回正

- 状态：改动完成（已部署）
- 目标：用户新方案——主流程2（巡线）正常巡线中，第一次雷达后方距离从 >2m 变为
  <1m 即"第一个右转"，开启功能；此后 rear 增大到 ≥1.5m 时右转 90°、停 2s、再
  左转 90° 回正继续巡线。替代旧 armed（rear<2.8m）→ rising（rear≥3.0m）右转 90° 逻辑。
- 影响文件：
  - `robot_dog_follow_line/scripts/follow_line.py`：新参数
    `rear_dip_from_m=2.0`/`rear_dip_to_m=1.0`/`rear_turn_at_m=1.5`/`rear_turn_deg=90`/
    `rear_hold_s=2.0`/`rear_turn_speed=16`/`rear_turn_timeout=10`；`check_rear_trigger()`
    重写为两阶段（阶段1 曾见 rear>2m 后首次 rear<1m 开启；阶段2 rear≥1.5m 执行转向
    序列）；新增 `start_rear_turn_seq()`（IMU yaw 闭环右转90°→sleep 2s→左转90°回正）；
    `follow_line_config.json` 可写入 5 个距离/时长参数（load/save 同步）
  - `robot_dog_follow_line/README.md`、`docs/launch-commands.md` §3.2：文档同步
  - `tmp/test_rear_trigger.py`（不入库）：mock 依赖的逻辑测试
- 实施记录：阶段1 用"曾见 >2m + 首次 <1m"状态标志而非相邻帧比较（缓慢下降
  2.5→1.8→0.8 时相邻帧比较会漏触发）；转向方向复用现有 yaw 闭环（speed 负=右转、
  正=左转，|yaw delta|≥90° 停转，超时停转报错）。
- 验证：py_compile 通过；`tmp/test_rear_trigger.py` 5 个逻辑用例全 PASS（缓慢下降
  触发、起点贴墙不触发、触发后只执行一次、远后无突变不触发、触发未到 1.5 不执行）。
  未实机。
- 遗留风险：须 bridge 常开（:8767）；YDLIDAR 0° 前/180° 后约定若装反则 rear 扇区
  实际测的是前方；起点后方须 >2m 且第一个右转处车尾须贴近障碍 <1m 才能开启；两段
  90° 用同一 `rear_turn_speed` 绝对值（左转取正），实机方向反时需调正负号；转向
  序列阻塞约 5-7s，期间不巡线。

## 2026-08-31｜巡线再压低：translation z 10→0（p=0 保持）

- 状态：改动完成（已部署）
- 目标：用户问能否爬更低。
- 影响文件：`follow_line.py`/`follow_line_tune.py`：`translation('z', 0)`；本记录。
- 实施记录：xgomini 库 z 约按 ±19.5 映射，0 低于原抓球/巡线常用的 10；p 仍 0 前后等高。若还要更低可试负值（如 -5），过低可能蹭地/步态不稳。
- 验证：py_compile + 机器 grep z=0；须重启 follow_line 实机看高度。

## 2026-08-31｜巡线低趴前后等高：p=15→0，撤销单收后腿

- 状态：改动完成（已部署）
- 目标：用户澄清「后腿和前腿一样」——不是单收后小腿，而是前后一样高；先前误加 31/41=12/11。
- 影响文件：`follow_line.py` `dog_init`：保持 `z=10`，`attitude p=15→0`（取消低头翘臀），删除 `motor(31/41)`；`follow_line_tune.py` 同步 p=0；本记录。
- 验证：py_compile + 机器 grep 无 31/41、p=0；须重启看实机是否前后平齐。
- 遗留风险：p=0 后相机俯视角度变浅，线可能变小/变远，必要时再微调 z 或轻量 p；步态仍可能改腿姿。

## 2026-08-31｜巡线低趴时后小腿再收（31=12 / 41=11）【已由上条纠正】

- 状态：改动完成（已被「前后等高 p=0」替代）
- 目标：曾误读为单收后腿；用户本意是前后腿一样。
- 影响文件：见上条。

## 2026-08-31｜雷达后方触发距离 1.5m → 3.0m

- 状态：改动完成（已部署）
- 目标：用户要求后方定位右转改为 3m。
- 影响文件：`follow_line.py` `DEFAULT_REAR_TRIGGER_M=3.0`；launch-commands；本记录。
- 验证：机器 grep/py_compile；须重启 follow_line。armed 仍为 trigger-0.2=2.8m 以下。

## 2026-08-31｜巡线弯道改雷达后方 1.5m 定位右转（替线宽突变）

- 状态：改动完成（已部署；桥已实机拉起 /rear 有数）
- 目标：用户要求改用雷达后方定位，后方距离 3.0m 处右转。
- 影响文件：
  - 新增 `robot_dog_navigation/scripts/lidar_rear_range_http.py`（/scan 正后±15° 中位距离 → HTTP :8767/rear）
  - 新增 `robot_dog_follow_line/host/run_lidar_rear_bridge.sh`
  - `follow_line.py`：`check_rear_trigger` rising≥3.0m → 原 IMU 闭环右转；默认关线宽突变；主循环每帧查后方
  - CMakeLists 列入新脚本；launch-commands §3.2；本记录
- 实施记录：触发=先 armed（rear&lt;1.3m）再 rear≥1.5m 一次；HTTP 失败打日志不装死。实机瞬时 rear≈4.46m（未贴后墙则不会 armed）。
- 验证：容器 /scan 有数据；`curl /rear` 返回 ok+rear_m；follow_line py_compile；未整段复跑巡线转弯。
- 遗留风险：须 bridge 常开；YDLIDAR 0° 前/180° 后约定若装反则扇区要改；起点须后方够近才能 armed；与全导航 bringup 同抢 /scan 时注意。

## 2026-08-31｜巡线 crop 再大幅放宽 50,249 → 10,309

- 状态：改动完成（已写机器配置）
- 目标：用户要求再次大幅增加左右可见面积（弯道/丢线前多看两侧）。
- 影响文件：机器 `follow_line_config.json`：`crop [50,249]`→`[10,309]`（有效宽 199→299，左右各+40，边留 10px）；本记录。
- 验证：机器 json 已更新；须重启 follow_line。
- 遗留风险：旁线/场地边更容易进视野误跟；若仍不够可再开到 `[0,319]` 全宽。

## 2026-08-31｜line_width 上限 100→150（弯道粗块仍可跟踪+突变）

- 状态：改动完成（已部署）
- 目标：用户确认弯道 raw>100 会被过滤成丢线、突变检测走不到；要求上限提到 150。
- 影响文件：`follow_line.py`/`follow_line_tune.py` 默认 `[5,150]`；机器配置 `line_width` 保持下限 25、上限 **150**；README 示例；本记录。
- 验证：本机/机器 py_compile；json 确认 `[25,150]`；须重启 follow_line。
- 遗留风险：上限放宽后大块杂物可能被当线，需实机看误跟；突变仍要 raw>95 连续 3 帧。

## 2026-08-31｜巡线速度再降：直行 8→6、转向前进 6→4

- 状态：改动完成（已部署）
- 目标：用户要求速度降一点再试。
- 影响文件：`follow_line.py` 默认常量；机器 `follow_line_config.json` 写入 `straight_speed=6`/`turn_move_speed=4`；本记录。
- 验证：机器 py_compile + json cat；须重启 follow_line 生效。边走边调仍可用 `[`/`]`、`-`/`=`。
- 遗留风险：过慢时弯道探测/闭环时长体感变长，按实机再调。

## 2026-08-31｜巡线实时显示线宽（8090/8091 水印 + 终端 [线宽]）

- 状态：改动完成（已部署）
- 目标：用户要求实时显示线宽，便于对照突变阈值与丢线/弯道。
- 影响文件：`follow_line.py`（推流水印 + 0.3s 日志；无轮廓时清零 best/raw）；README；本记录。
- 实施记录：水印格式 `lw=<过滤后> raw=<突变用>/<surge_lw_thresh>`；8090 FOLLOW 行与 8091 MASK 行均带；终端 `logging.warning('[线宽] …')` 节流 0.3s。
- 验证：ast + 机器 py_compile；scp 至 `/home/pi/oumax-xgo/follow_line.py`；未复跑。
- 遗留风险：推流仍每 2 帧一次，线宽显示约半帧率；须重启 follow_line 生效。

## 2026-08-31｜巡线 crop 左右放宽 70,229 → 50,249

- 状态：改动完成（已写机器配置）
- 目标：用户反馈丢线后仍不转弯，要求左右画面再打开一点（扩大可见线宽/弯道边缘）。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line_config.json` 的 `crop`；本记录。
- 实施记录：`[70,229]` → `[50,249]`（左右各 +20px，画面 320 宽）；其余 HSV/line_width 未改。需重启 follow_line 生效。
- 验证：机器端 json 已更新并 cat 确认；未复跑巡线。
- 遗留风险：裁宽后可能看到旁线；若仍不转需查探测日志（`[探测]`/`[丢线开始]`）而非只调 crop。

## 2026-08-31｜巡线线宽突变阈值 75→95（防正常段 89px 误触发）

- 状态：改动完成（已部署）
- 目标：实机日志 `当前线宽 89px > 75px` 误触发弯道右转；用户要求阈值改 95。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（`surge_lw_thresh=95`）、README；本记录。
- 验证：ast/机器 py_compile 通过；scp 至 `/home/pi/oumax-xgo/follow_line.py`，grep 确认 95；未复跑巡线。
- 遗留风险：真弯道线宽若 ≤95 会漏触发，需实机确认；阈值仍硬编码（未入 config）。

## 2026-08-31｜四轮依次各转 7 秒诊断脚本

- 状态：改动完成
- 目标：用户要求写程序让轮子依次转 7 秒（单轮诊断顺序跑完四轮）。
- 影响文件：`tmp/drive_wheels_sequential.py`；`docs/launch-commands.md` §7；`docs/lingo.md` 词条「轮子依次转」；本记录。
- 实施记录：通道顺序 [左前,右前,右后,左后]，每轮 10Hz 刷新，默认 7s@1.2；主机名自动选手控地址（pi→127.0.0.1，开发机→192.168.137.157，`RAICOM_MANUAL_HOST` 可覆盖）；已 scp 到机器 `/home/pi/oumax-xgo/drive_wheels_sequential.py`。
- 验证：本机/机器 py_compile 通过；开发机曾实跑：左前/右前/右后转、左后不转；用户在 pi 家目录误跑 `tmp/...` 已改文档为机器绝对路径。
- 遗留风险：左后轮倾向硬件故障；勿在 `~` 下写仓库相对路径 `tmp/`。

## 2026-09-01｜Cartographer 纯激光建图模式：enable_mapping:=true + odom_mode:=carto

- 状态：改动完成（已部署实机，建图验证中）
- 目标：用户要求“从零建图”——当前 carto 分支只支持定位（加载已有地图
  + lidar_loc 全局匹配），无法用 Cartographer 建图；且原 carto 分支挂在
  `<group unless="enable_mapping">` 下，enable_mapping:=true 时 cartographer
  根本不启动。
- 影响文件：`robot_dog_bringup/launch/robot_dog_main.launch`：①gmapping 分支
  条件改为 `enable_mapping and odom_mode != 'carto'`（carto 建图时不用 gmapping）；
  ②carto 分支从定位 group 移出为独立 group（`if odom_mode == 'carto'`，建图/
  定位两用，注释说明两种模式）；③`odom_mode`/`use_amcl` arg 定义前移到
  `enable_mapping` 之后（launch arg 顺序敏感，gmapping 分支先引用）；
  `robot_dog_navigation/config/cartographer_2d.lua`（num_subdivisions
  =10→1，见下）；`docs/launch-commands.md`（§5 新增 carto 建图/定位命令）；
  本记录与 mistakes 记录。
- 实施记录：新增组合 `enable_mapping:=true odom_mode:=carto` = 纯雷达从零建图：
  无 map_server/lidar_loc/move_base，cartographer 全局 SLAM 自行发布 map→odom
  与 /map 子图；遥控用 mapping_keyboard_teleop（发 cmd_vel → 桥 → 运动，需
  enable_motion:=true）。
- **num_subdivisions 实机坑（本次核心修复）**：ydlidar scan 无 per-point 时间
  偏移，`num_subdivisions_per_laser_scan=10` 时 cartographer 报 subdivision
  时间恒等（"previous subdivision time ... is not before current"）并忽略
  大部分 scan → 建图停滞（/map 只有 ~1 帧的障碍点、无空闲）；设 0 会让
  1.0.0 CHECK 崩溃（trajectory_options.cc:30 要求 >=1）。最终设 **1**（合法
  最小值 = 整帧一段不细分，跨帧按 header.stamp 比较正常推进）→ 实测 subdivision
  警告消失、/map 正常累积空闲/障碍。
- 验证：XML 合法；roslaunch --nodes 五种组合节点集全对——定位 carto
  （cartographer+imu_bridge+lidar_loc+map_server+move_base）、建图 carto
  （cartographer+imu_bridge 仅）、建图 gmapping（slam_gmapping+simple_odom，
  原行为保持）、定位 amcl（amcl+map_server+move_base+odom_from_amcl）、
  定位 cmd_vel 默认（lidar_loc+map_server+move_base+simple_odom）。已部署实机
  （launch 备份 .bak-20260901-cartomapping，sha256 一致）；实机建图验证：
  num_subdivisions=1 后 /map 正常增长（空闲 19.6%、障碍 0.9%、未知 79.5%，
  随时间扩展）；RViz 看不到地图为显示问题（map 色带空闲=黑色、黑背景不可见，
  调亮背景 + Alpha 1.0 解决）。
- 遗留风险：carto 建图实机效果（足式颠簸时纯激光建图质量、空闲概率收敛）
  待用户遥控走完场地后评估；建图时 imu_bridge 仍需 8765（手动服务）；遥控
  建图 enable_motion:=true 有运动风险，需净空场地；occupancy_grid_node 需
  单独启动（cartographer_node 不发布 /map）；容器重建后 cartographer 编译
  产物丢失风险仍存在。

## 2026-09-01｜巡线运动参数（PID/速度/方向/模式/轮速）纳入配置文件自动保存

- 状态：改动完成
- 目标：用户反馈——巡线边走边调（P/D/直行速度/转向前进速度/方向/轮足式）
  每次启动都回硬编码默认值，调好无法复用；要求与 HSV 阈值一样保存为下次
  启动默认。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（启动读取全部参数 +
  新增 `s` 键保存）、`follow_line_tune.py`（保存视觉参数时保留运动字段）、
  `README.md`、本记录。
- 实施记录：①`follow_line.py` 顶部新增 `DEFAULT_PID=[396,0,30]`/
  `DEFAULT_STRAIGHT_SPEED=8`/`DEFAULT_TURN_MOVE_SPEED=6`/`DEFAULT_DIRECTION=1`/
  `DEFAULT_MODE='foot'`/`DEFAULT_WHEEL_BASE=145` 常量；②`load_follow_line_hsv`
  升级为 `load_follow_line_config`：返回完整 dict（视觉 + 运动字段），缺文件/
  缺字段回默认（旧配置兼容）；③新增 `save_follow_line_config`：把当前参数
  全部写回 `follow_line_config.json`（s 键调用）；④`LineDetect.__init__` 默认值
  改引用常量，`dog_init()` 后统一应用配置，`mode=wheel` 时自动
  `enable_wheel_control(1)`；⑤主循环新增 `s` 键保存 + 提示更新；⑥
  `follow_line_tune.py` 的 `load_hsv` 返回运动字典、`save_hsv` 原样写回
  （调视觉参数不覆盖运动参数）。
- 验证：两个脚本 py_compile 通过；从源码提取函数做往返测试——①无配置回默认
  运动参数；②保存→重载一致（含 wheel 模式/负方向/新 PID）；③旧配置（仅视觉
  字段）运动字段回默认；④tune 改 V 上限后保存，运动字段保留。CRLF 行尾与原
  文件一致（follow_line.py/README 原厂 CRLF，新增行同用 CRLF）。
- 遗留风险：`s` 保存与 `Q` 保存日志两个快捷键易混淆（已更新提示文本）；
  旧 `follow_line_config.json`（仅视觉字段）仍兼容（已实机验证）；wheel 模式
  启动自动 enable_wheel_control(1)，切回 foot 由 m 键恢复 0。
- 部署：已 scp 上传机器 `/home/pi/oumax-xgo/`（旧版备份为
  `follow_line.py.bak-20260901-saveparams`、`follow_line_tune.py.bak-20260901-saveparams`），
  chmod +x 恢复 755（scp 覆盖丢 x 教训）；机器端 py_compile 通过、sha256 与仓库
  一致；实机验证新脚本读取现有旧配置：视觉字段保留、运动字段回默认。未启动巡线。

## 2026-09-01｜线宽突变右转 90° 改 IMU yaw 闭环（替代盲转固定时长）

- 状态：改动完成
- 目标：用户指出转角处机器狗走路摇晃导致看不到转角，盲转 90°（turn(-16)×4.2s
  开环）不可靠——转多转少无反馈；先做最小改动：把 `start_surge_turn` 的盲转
  改为读机载 IMU yaw 累积角（0x66 单轴，度）闭环，|yaw 变化|≥90° 即停转。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①新增
  `turn_closed_loop(target_deg, speed, timeout_sec)`——以当前 yaw 为基准持续
  turn(speed)，每 0.1s 读 yaw，|delta|≥目标即 turn(0) 停；读取失败/超时立即
  停转返回 False（full exposure，不静默盲转）；②`start_surge_turn` 改为调用
  闭环（原 `turn(-16) sleep 4.2s` 盲转删除）；③`__init__` 参数
  `surge_turn_90=4.2` → `surge_turn_deg=90.0`/`surge_turn_speed=-16`/
  `surge_turn_timeout=10.0`；新增 `import math`；README 行为要点同步；本记录。
- 实施记录：闭环只用 yaw **相对变化**（累积角 delta 即转角，无需 wrap），避开
  2026-08-15 教训（IMU 绝对 yaw 不能当坐标基准）；方向只由 speed 符号决定
  （负=右转，同原盲转），用 |delta| 判断方向不敏感；read_yaw 为 0x66 单轴读
  （0x65 批量读在该固件不可用，2026-08-17 已验证），手控服务 /imu 同源路径
  已实机验证可用；巡线进程同进程持有 dog 实例，串口无跨进程竞争。
- 验证：py_compile 通过；无 surge_turn_90 残留；工作区 CRLF 行尾与新增行一致
  （原厂文件既为 CRLF，仓库 autocrlf=input 提交时转 LF，diff 全量行变化属
  既有假象）；未部署实机、未实机验证。
- 遗留风险：①turn 持续转向期间循环读 yaw（串口读）是否影响转向节奏、yaw
  读数在足式转动时的延迟/跳变需实机确认（采样周期 0.1s，转弯末端有过冲风险，
  必要时降速或提前停）；②`read_yaw` 若实机返回非 float（如 None/字符串）会
  立即停转并报错——暴露而非盲转，符合设计；③超时 10s 是转不动/方向错时的
  保护，实机若 turn(-16) 转 90° 需 >10s（原盲转 4.2s 标定，不太可能）需调大。

## 2026-08-31｜线宽突变改绝对阈值：raw_line_w > 75px 连续 3 帧 → 右转 90°

- 状态：改动完成（已部署，待实机复测）
- 目标：用户按实机经验定参——线宽超过 75px 即判定突变（弯道），触发右转 90°
  （不再用基线×5/3 相对阈值、不再逐格转）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`surge_ratio`
  → `surge_lw_thresh=75`（绝对阈值，删除 EMA 基线）；`start_surge_turn` 改为
  **阻塞一次转完 90°**（turn(-16) × surge_turn_90=4.2s，转完停 0.3s、PID 重置、
  继续巡线）；删除 `surge_turn_step` 与主循环 surge 状态机分支（触发即阻塞完成）；
  日志保留 lw/raw 显示；README 同步；本记录。
- 验证：ast 通过（无 surge_turn_step/_lw_baseline/surge_ratio 残留）；部署后
  机器端 py_compile 通过、sha256 一致（6f775432…）；未实机复测。
- 遗留风险：75px 阈值需实机确认（正常段线宽 ~60-90px 可能与阈值重叠，若正常
  段即超 75 会误触发）；surge_turn_90=4.2s 转角需标定；转 90° 后线不在视野时
  由丢线探测兜底。

## 2026-08-31｜新增线宽突变检测：线宽 > 基线×5/3 连续 3 帧 → 右转

- 状态：改动完成（已部署，待实机复测）
- 目标：弯道处线转横向/连通成块时线宽突变（minAreaRect 短边增大），作为
  弯道信号：线宽超过基线线宽 5/3 且连续 3 帧 → 右转。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①`color_follow`
  记录 `best_line_w`（过滤后线宽）与 `raw_line_w`（不过滤的全局最大轮廓短边，
  突变检测用，不受 line_width 上限过滤影响）；②`LineDetect` 新增线宽突变
  状态：`_lw_baseline`（EMA 基线，突变帧不污染）、`_lw_surge` 计数、
  `_surge_active/_surge_step` 右转状态机；③`check_line_surge()` 跟踪帧调用
  （raw_line_w > 基线×5/3 连续 3 帧 → `start_surge_turn()`）；④
  `surge_turn_step()`：逐格右转（step_duration=1.167s、每格停 0.5s）直到
  线宽恢复（≤基线×5/3）停止转弯继续巡线，限格未恢复则停；⑤主循环 surge
  状态机优先于丢线探测；README 同步；本记录。
- 实施记录：raw_line_w 不受 line_width=[25,100] 上限过滤影响（突变到 >100
  的 L 形也能检测到）；触发后右转与丢线探测同参数（step_duration、probe_steps、
  每格 0.5s 停）。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （a92ccb2d…）；未实机复测。
- 遗留风险：基线 EMA 初始值从首个跟踪帧开始，启动瞬间线宽突变可能误判；
  线宽突变阈值 5/3 与连续帧数 3 需实机确认（场地多线时可能误触发）。

## 2026-08-31｜探测去除 90° 概念：每格独立时长、见线即停、无弯道停留

- 状态：改动完成（已部署，待实机复测）
- 目标：用户指出——丢线右转探测已不需要 90° 上限与弯道确认后的停留。
  ①`turn_duration`（90°总时长）删除，`step_duration` 独立定义 0.7s/格；
  ②探测见线即停交回 PID（上轮已改），无限格时不再有"转完剩余 90°"；
  ③`_finish_turn` 删除弯道确认后的 0.5s 停留（见线直接恢复巡线）；
  ④日志/注释全面去除 90° 字样。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（__init__ 探测参数
  step_duration=0.7/probe_steps=6、_finish_turn 简化、start_probe/probe_step
  日志与注释更新）；README 同步；本记录。
- 验证：ast 通过（无 90°/turn_duration 残留）；部署后机器端 py_compile
  通过、sha256 一致（6a542afb…）；未实机复测。
- 遗留风险：每格 0.7s 的实际转角未标定（探测 6 格总转角可能不足/超过弯道
  需求）；限格数 6 是否够（弯道大时可能需更多格）待实机确认。

## 2026-08-31｜探测见线即停：不再强制转完剩余 90°

- 状态：改动完成（已部署，待实机复测）
- 目标：用户两次质疑"为什么见到线会右转"——原设计"看到线=弯道确认→转完
  剩余格数"反直觉，且线边缘闪烁时会把原线误当弯道转完 90°。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`probe_step`
  看到线分支改为**立即停止转弯、交回 PID 对准线继续巡线**（不再转剩余格）；
  仅未看到线时继续转格，6 格全无则丢线即停；README 同步；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （242bb180…）；未实机复测。
- 遗留风险：弯道后线方向与狗朝向偏差大时靠 PID 逐步拉回（多帧转向），
  若线在视野边缘脱离可能再丢线（届时由正常丢线流程处理）。

## 2026-08-31｜确认保留弯道探测（丢线后右转继续巡线）

- 状态：改动完成（已部署，待实机复测）
- 目标：用户先要求移除弯道检测，随后确认**保留丢线后右转探测、继续巡线**。
  恢复完整探测逻辑（含全部实机修复：抖动丢线 5 帧确认、每格 0.3s 稳定、
  弯道确认后 0.5s 停留、90° 未见线放弃即停、冷却 5s 防死循环）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（恢复
  start_probe/probe_step/_finish_turn、_lost_frame 计数、主循环探测分支与
  冷却判断；与最新修复版本一致）；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （911ffe4b…）；未实机复测。

## 2026-08-31｜修复"看到线后右转"：丢线抖动不再触发探测（连续 5 帧确认）

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"为什么看到线后会右转"——根因：线在 crop 边缘闪烁的**抖动丢线**
  （日志大量 0.1-0.2s 丢线→恢复）也会启动探测，探测第一格右转 15° 后线被
  转回视野 → 误判"弯道确认" → 强制右转 90°。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：新增
  `_lost_frame` 连续丢线计数——process 丢线分支每帧 +1、恢复时清零；
  主循环探测启动条件增加 `_lost_frame >= 5`（约 0.5s 确认真丢线）；
  抖动丢线（1-2 帧恢复）自动恢复巡线，不触发探测；README 同步；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （f7544f16…）；未实机复测。
- 遗留风险：5 帧确认窗口内真弯道若线消失快（<0.5s 完全离开）可能拖后探测
  启动（无害，只是晚 0.3s）；抖动阈值可调。

## 2026-08-31｜弯道确认后停留 0.5s + 线宽下限 20→25

- 状态：改动完成（已部署，待实机复测）
- 目标：①弯道转完看到线后停留更久（0.3→0.5s）让狗/画面完全稳定再进 PID；
  ②线宽阈值下限 20→25（再滤细线）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（`_finish_turn`
  advance 路径 sleep 0.3→0.5s）；机器配置 `follow_line_config.json`
  line_width [20,100]→[25,100]；README 同步；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （f1e1be92…）、配置已更新；未实机复测。

## 2026-08-31｜移除弯道后直行推进：确认看到线时线已在视野内，推进导致丢线

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"见到线之后向前走了几步，导致直接丢线"——上一轮 `_finish_turn`
  的直行推进 0.6s 是元凶：探测确认看到线时线已在视野内，推进反而把狗推过
  弯道/推出线。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`_finish_turn`
  移除 `move_x 0.6s` 推进段，弯道确认后仅 0.3s 画面稳定即恢复 PID 巡线
  （advance=False 路径不变，直接停）；README 同步；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （354871ac…）；未实机复测。
- 遗留风险：若转角偏差导致线不在视野（探测未确认而放弃）仍会停——届时
  需标定 turn_duration 修正 90° 转角。

## 2026-08-31｜弯道转弯后处理修复：稳定+直行推进+探测冷却

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"右转后等待时间太短，且丢线"——转弯完成立即进 PID，转角偏差/
  画面未稳导致马上再丢线；且会陷入 丢线→探测→丢线 循环。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①探测每格
  `turn(0)` 后加 0.3s 画面稳定再检测（防惯性残帧误判）；②`_finish_turn`
  加 `advance` 参数——弯道确认路径：0.3s 稳定 + 直行推进 0.6s（把线带回
  视野）再恢复 PID 巡线；90° 未见线放弃路径不推进直接停；③新增
  `_probe_cooldown`（5s）：探测完成后冷却期内再丢线不重复探测（防死循环），
  主循环启动探测加冷却判断；README 同步；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （1dbe88dd…）；未实机复测。
- 遗留风险：直行推进 0.6s 若线仍不在视野（转弯角度偏差大）会再丢线并停
  （冷却 5s 后仍停，需人工介入）；转弯角度实测偏差仍待标定 turn_duration。

## 2026-08-31｜弯道最终方案：丢线后右转探测（每格见线确认，不依赖 cx/area）

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"拐角处不转"。日志（00:36 段）[弯道判定] recent_cx=[170,177,155,165,159,166]
  over175=1/6——**宽线实机 cx 全程 ≤177，cx 类判据（均值/计数/单调）全部失效**
  （用户"线很宽 cx 不漂移"的判断最终证实）。废弃 cx/area 判据。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：全新**探测式转弯**——
  丢线后主循环启动 `start_probe()`（右转第一格 turn(-16)×step_duration），
  之后每帧 `probe_step(frame)`：抓当前帧 `line_follow` 检测，**看到线 = 弯道确认**
  （转完剩余格数），90° 内未见线 = 放弃（丢线即停）。90° 分 6 格（每格
  turn_duration/6≈0.7s）。删除 `_lost_to_turn`/`_do_right_turn`/`_turning`；
  主循环丢线分支接管探测（探测期间不推流/不响应按键，最长约 5s）；
  README 同步；本记录。
- 实施记录：探测用"事实确认"（转后见到线）替代一切图像判据——弯道（右转
  15-30° 即可见拐过去的线）必然确认；出线/断线 90° 内无线则停。零误判
  （不转错），零漏判（弯道必见线）。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （9d00dba1…）；未实机复测。
- 遗留风险：①step_duration 基于 turn_duration=4.2s 估算（turn(-16) 90°），
  每格实际转角需实机确认（若每格≠15°，总转角由 step_duration×6 决定，仍
  可整体按比例调 turn_duration）；②探测 5s 内不响应按键，紧急停止需等探测
  结束或断电。

## 2026-08-31｜弯道判定改帧数计数（相位无关）：丢线前 6 帧中 ≥3 帧 cx>175

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"第一次转第二次没转"。日志对比：第一次触发序列
  `126,167,202,213`（均值高）；第二次 `100,163,205` 后丢线——刚左摆完再
  右摆，**6 帧均值被左摆帧拉低 <175**。均值判据对摆动相位敏感。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`_lost_to_turn`
  改为计数判据——丢线前最近 6 帧中 **≥3 帧 cx>175** 判定右弯道（右弯道丢线
  前通常连续多帧偏右；蛇形末尾丢线仅 1-2 帧高值，如 170,173,170,180,175→1帧）；
  判定时打印 `[弯道判定] recent_cx=[...] over=..` 便于现场定位；README 同步；
  本记录。
- 实施记录：帧数计数对相位不敏感（只要累计右偏帧够多，不要求连续或均值）。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （0a9ac494…）；未实机复测。
- 遗留风险：若实机仍临界（如 205,202,196,175,120,119 判 3 帧触发但实为蛇形），
  可用新打印的 [弯道判定] 日志微调 turn_cx_thresh（175）或帧数（3）。

## 2026-08-31｜弯道判定改"丢线时判定"：丢线前 cx 偏右 → 右转 90°

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"拐角没转"。日志（00:31 段）显示拐角处 cx 序列
  `180→175→丢线`——**宽线时 cx 被大面积黑块平均、变化滞后，单调递增帧数
  不足 4 步，在线判定无法触发**。弯道必然以丢线收场（线拐走），故把判定
  移到丢线瞬间：用丢线前 cx 历史判断（均值>阈值 = 线此前已偏右 = 右弯道）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`_detect_turn`
  （在线判定）替换为 `_lost_to_turn()`（丢线判定：最近 6 帧 cx 均值>
  turn_cx_thresh）；process 检测到线时只记录 cx/area 历史（不再在线触发），
  丢线分支先 `_lost_to_turn()` 判定——真则右转 90° 并继续巡线，否则
  "丢线即停"；README 同步；本记录。
- 实施记录：在线误触发（蛇形右摆）与拐角不触发（帧数不足）均被此方案规避
  ——判定只看丢线时的 cx 历史均值，蛇形在线不丢线不触发，拐角丢线时
  cx 必偏右。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （60dd9ef9…）；未实机复测。
- 遗留风险：蛇形右摆顶点恰好出线的场景可能误判弯道（cx 高+丢线）；
  若出现需调高 turn_cx_thresh 或加"丢线前 cx 持续偏右时间"条件。

## 2026-08-31｜弯道误触发修复：加回 area 衰减条件（区分蛇形右摆与真弯道）

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"正常巡线时转弯了"——误触发。根因：单纯"cx 单调递增+>175"
  判据在**蛇形右摆的上行段**同样满足（蛇形时 cx 也能单调递增并超过 175，
  但线仍在画面中）；area 衰减才是弯道（线拐走、面积减少）与蛇形（面积
  稳定）的本质区别。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`_detect_turn`
  恢复双条件——cx 最近 6 帧递增步≥4 且末值>175，**且** area 近 5 帧均值
  < 10 帧峰值×0.6（turn_area_ratio 恢复配置，采样数据弯道处 area 衰减至
  0.30）；`_area_hist` 重新参与判定。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （ca3c67cd…）；未实机复测。
- 遗留风险：area 阈值 0.6 若实机弯道衰减不够（线宽很大时拐角处 L 形连通
  area 可能先增后减）可能需要微调；误触发是否消除待实机确认。

## 2026-08-31｜弯道检测改为 cx 单调递增判据 + 转向速度上限降为 15（治蛇形）

- 状态：改动完成（已部署，待实机复测）
- 目标：实机"拐角处不转"。日志（V=120 配置下）显示 cx 序列
  `180→127→166→191→174→111` 剧烈蛇形（每次转向过冲 30-60px）——旧弯道
  判据（5 帧均值>170 + area 衰减）无法满足；且蛇形峰值 203 与弯道值重叠，
  cx 阈值本身无法区分。
- 根因：转向窗口改回 0.5s 后 M 型 turn_speed 上限仍 18，P=396 下每次全速
  转向单次转角过大 → 过冲蛇形。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①弯道判定改
  **最近 6 帧中 ≥4 步 cx 单调递增 且 当前 cx>175**（蛇形方向频繁反转、
  递增步≤2 天然免疫；area 条件移除——实机动态不稳定）；参数化
  turn_cx_thresh=175/turn_up_steps=4；②M 型 turn_speed 上限 18→15、
  斜率 1.1→0.8（缓解蛇形过冲，死区 12 不变）；README 同步；本记录。
- 实施记录：单调递增步数判据对"线宽 cx 变化慢"仍适用（无需大漂移，只需
  同向不反转）。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （436ed8d9…）；未实机复测。
- 遗留风险：turn_cx_thresh=175 在蛇形改善后是否合适待实机确认；弯道触发
  时机（过早/过晚）与 turn_duration 仍需现场标定。

## 2026-08-31｜弯道检测实现：cx 单侧漂移 + area 衰减 → 右转 90°

- 状态：改动完成（已部署；转弯时长 turn_duration=4.2s 为估算，待实机标定）
- 目标：巡线路线上 90° 右转弯：自动检测并执行右转，避免弯道处丢线停止。
- 采样标定：用户摆 9 个位置按 p 采样（line_samples.log）。数据结论：线实际
  ~70-90px 宽（crop 内），**左右边缘条带恒为 0（线未及边缘）→ 否决"单侧条带
  变空"方案**；弯道真实信号：正常段 cx≤156/area 稳定（5158-6924），弯道拐点处
  cx=170+angle 偏离 90°，出口前 cx=194、**area 骤减至 0.30、ncont 1→2**。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：`color_follow` 记录
  `best_area`；`LineDetect` 新增弯道状态（cx/area 双 deque×10、turn_cx_thresh=170、
  turn_area_ratio=0.6、turn_duration=4.2、_turning 标志）；`_detect_turn()`（最近
  5 帧 cx 均值>170 且 area 近帧<峰值×0.6，排除直线大偏移）+ `_do_right_turn()`
  （turn(-16) sleep 4.2s turn(0)，足式一次一个动作）；process 检测到线时弯道
  优先，丢线时清历史；README 同步；本记录。
- 实施记录：直线大偏移（cx 高但 area 稳定）不会触发，真弯道 area 衰减才触发；
  只右转（比赛弯道固定右侧）。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致（dcf4e3f8…）；
  未实机验证弯道触发与转弯角度。
- 遗留风险：①turn_duration=4.2s 为 rotate 180°@turn15=9s 的比例估算，**90°
  实际转角需实机标定**（跑一次看角度再调）；②turn_cx_thresh=170 临界于
  采样位置 7（cx=170），实机如早触发/晚触发可微调；③误触发风险待实机确认
  （直线大幅偏移但 area 短时波动的场景）。

## 2026-08-30｜固化实机标定参数：P=396/D=30 + 配置补 line_width

- 状态：改动完成（已部署验证）
- 目标：用户实机确认"基本巡线"，固化最终参数，使主流程2/巡线开箱即用：
  无需每次边跑边调。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（`FollowLinePID`
  默认 [1,0,0]→**[396.0, 0, 30.0]**）；机器与仓库配置
  `follow_line_config.json`（lower=[0,0,20] upper=[180,255,140] crop=[80,219]
  **补 line_width=[5,100]**）；README 同步；本记录。
- 实施记录：参数来自 2026-08-30 23:34-23:38 实机日志稳定段（P 396、D 30±、
  连续 turn=±12~18 纠偏、丢线均恢复）；spd=8/6、dir=+、foot 保持默认。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （17a7a64d…）、grep 确认默认值、json 已更新；未复跑（参数即用户实机
  验证值）。
- 遗留风险：灯光变化/场地不同时 V 阈值与 P 可能需再微调（边走边调键保留）。

## 2026-08-30｜巡线日志诊断化：时间戳 + 丢线开始/恢复状态 + 输出值入日志

- 状态：改动完成（已部署重验证，待实机复测）
- 目标：运行结束后能从保存的日志（Q 键 → follow_line_log_1/2.log）立马读出
  问题：偏左/右、实际输出（足式 turn 速度/轮式 L R）、丢线时刻与持续时长、
  按键调整时间点。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①logging.basicConfig
  加毫秒时间戳（`%(asctime)s.%(msecs)03d`）；②丢线改状态化日志——开始时打一次
  `[丢线开始] mode/P/D/V/crop/lw/spd/dir` 全参数快照，恢复时打
  `[恢复寻线] 丢线持续 X.Xs`（不再每帧刷屏）；③print_params 加 `HH:MM:SS` 前缀
  （按键调整时间点）；④`log_bias` 已带 detail：足式 `直行/turn=16`、轮式
  `L=145 R=135`；⑤M 型转向速度死区钳制 `max(12, min(1.1|z|,18))`；⑥轮式差速
  放开 0~255（允许一侧后退）。README 同步；本记录。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （5bf8172b…/27aadcf1…）；未实机复测。
- 遗留风险：丢线持续时无逐帧日志（有意为之，恢复时会给总时长）。

## 2026-08-30｜巡线双路推流：8090 带框原画面 + 8091 阈值画面 + 偏差方向日志

- 状态：代码完成（机器关机未部署，开机后部署）
- 目标：①电脑同时看"阈值画面"与"带框原画面"（两个标签页并排）；
  ②日志实时显示线偏左/偏右。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①StreamingServer
  改为接收 output 参数（实例级，Handler 从 `self.server.output` 取），支持
  多路流；新增 `MASK_PORT=8091`，双 server 线程；每帧推两路：8090 画框原图
  （FOLLOW+mode 水印）、8091 二值掩码图（MASK V/crop 水印，binary 非 ndarray
  时跳过）；finally 关两个 server。②`log_bias()`：节流 0.5s 打印
  `[线偏左/偏右/居中] cx/中心 z_Pid mode`，execute 开头调用（foot/wheel 通用）；
  README 同步；本记录。
- 实施记录：承接上一轮"偏左偏右"需求（机器关机前未部署）；本轮一并完成。
- 验证：ast 语法通过；未部署未实机。
- 遗留风险：8091 端口在 oumax-camera 场景无冲突，但需确认无其他服务占用；
  双路 imencode 增加少量 CPU。

## 2026-08-30｜巡线推流到电脑 + 轮式/足式切换 + 足式"一次一个动作"转向修复

- 状态：改动完成（已部署重验证，实机复测待用户）
- 目标：①巡线画面实时传到电脑；②轮式/足式两种方式运行时切换；③用户实机
  洞察"足式可能不能同时做两个动作"——查 xgolib 源码确认：`move_x` 发 VX、
  `turn` 发 VYAW 寄存器，固件后发覆盖先发（`move_by` 只用 VX+VY 合成从不混
  VYAW，`turn_by` 单独用 VYAW），原厂 turn+move_x 连发 = 转向被吞，实机表现为
  只前进不转向（"方向怎么调都没用"的真凶）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①新增 8090 MJPEG
  推流（StreamingOutput/Handler/Server，主循环 imencode 推画框图 + FOLLOW/mode
  水印）；②`mode` 属性 foot/wheel，`m` 键切换（`enable_wheel_control(1/0)`），
  `execute_wheel` 四通道差速（通道 [左前,右前,右后,左后]，128=停，base=145，
  差速 clamp ±40），`stop_motion` 按模式停（wheel 发 128）；③足式转向分支改为
  **先纯转向（turn+sleep runtime_x）→ turn(0) 停转 → 短前进（move_x 0.25s）→
  stop**，一次只发一个运动指令；README 同步；本记录。
- 实施记录：wheel_byte 语义参考 manual_control_server（128=停、>128 前进、
  <128 后退）；轮式低趴姿态是否适用待实机确认。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致（610c9401…）；
  未实机复测。
- 遗留风险：足式转向+前进分步后节奏变"顿挫"，速度/时长按实机再调；轮式差速
  方向与 base 速度待实机标定；推流与 oumax-camera 同用 8090（跑前须停相机服务）。

## 2026-08-30｜巡线方向修复：PID 目标=裁剪窗中心 + t 键切换转向方向

- 状态：改动完成（已部署重验证，实机复测待用户）
- 目标：用户实机反馈"方向反了、P 怎么调都没用"。两个根因：①crop 不对称
  （如 [80,219] 中心 149.5 ≠ 硬编码目标 160）→ 线在裁剪窗中心时误差恒为
  ~10.5px，P 越大转向越猛、永远对不齐；②原厂 turn 符号语义未实机验证，
  方向可能反（P 放大反向偏差，表现为调 P 无效）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：execute 目标点由
  硬编码 160 改为 `(crop[0]+crop[1])/2`；新增 `self.direction`（默认 1）乘
  z_Pid，`t` 键切换正负；print_params 显示 `dir=+/-`；启动提示加 t 键；
  README 同步；本记录。
- 实施记录：方向用运行时开关而非写死——实机一键验证，不用猜符号；
  crop 中心修复消除固定偏差，P 调大即真正生效。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （c06bc815…）、grep 确认 crop_center/direction 就位；未实机复测。
- 遗留风险：实机需按 t 确认方向（dir=+ 或 -）；crop 中心修复后 P 应立刻
  有效，若仍无效需重新调参。

## 2026-08-30｜丢线行为改"丢线即停、看到再寻"（替代原地转圈）

- 状态：改动完成（已部署重验证，实机复测待用户）
- 目标：用户指令：丢线就停（`dog.stop()`），重新看到线后自动恢复巡线；
  不再原地转圈（转圈 + 慢速锁线实机仍难恢复）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（丢线分支：打印
  `未检测到线条，停止` + `dog.stop()`，保留 `PID_controller.timeOfLastCall=None`
  重见线全新启动）；README 行为要点同步；本记录。
- 实施记录：承接上一轮修复（PID 长空档 >0.5s 重置 + 丢线时 timeOfLastCall=None，
  保证重见线第一帧不污染）；本轮仅把转圈指令换成 stop。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致（8e4d6096…）、
  grep 确认无"原地转圈"残留；未实机复测。
- 遗留风险：丢线停止后若线在视野外，狗原地等待不找（用户可手动摆正或把狗
  移到线上即自动恢复）。

## 2026-08-30｜巡线实机修复：退出时停狗 + PID 默认 P=1/D=0

- 状态：改动完成（已部署重验证，实机复测待用户）
- 目标：用户实机反馈：①摄像头停了机器还在运动——move_x/turn 是持续指令，
  退出路径（Ctrl-C）未显式停狗，最后一条运动指令继续执行；②D 默认从 0 开始、
  P 默认从 1 开始。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：finally 清理开头加
  `line_detect.dog.stop()`（在 picam2.stop 之前，先停运动再停相机）；默认
  `FollowLinePID = [1.0, 0, 0.0]`（原 [50,0,30]）；README 同步；本记录。
- 实施记录：B 键路径本有 cancel()→dog.reset()，Ctrl-C 路径此前无停狗；
  现 finally 统一 stop()（reset 有摆位动作，stop 只停运动）。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （b5fe985b…）、grep 确认默认值与 dog.stop 就位；未实机复测。
- 遗留风险：P=1（Kp=0.001）起步极弱，实机需长按 p 快速加到有效值。

## 2026-08-30｜巡线边走边调细粒度化：P±1/D±0.1、速度默认再降且步进±1

- 状态：改动完成（已部署重验证，实机复测待用户）
- 目标：用户反馈速度仍快、P/D 步进（±50/±10）太粗。改为：P `p`/`o` 步进 **1**、
  D `i`/`u` 步进 **0.1**；速度实时调整保留且默认再降（直行 8、转向 6），
  `[`/`]`、`-`/`=` 步进 ±1。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（FollowLinePID 改
  float list [50.0,0,30.0]；按键步进重设；速度默认 8/6；print_params 用
  `:.1f` 格式化；启动提示同步）；README 同步；本记录。
- 实施记录：D 用 round(x,1) 防浮点累积误差；P 按 1 步进从 50 提到 300 需
  250 次按键，raw 模式长按触发键盘 repeat 可连续累加。
- 验证：ast 通过；部署（机器重启后）py_compile 通过、sha256 一致
  （930e060c…）；未实机复测。
- 遗留风险：P 目标 300+ 需实机长按或多次按键达到；速度 8/6 是否合适待实测。

## 2026-08-30｜巡线实机问题修复：退出卡死（atexit close）+ 速度太快（降速并可调）

- 状态：改动完成（已部署重验证；实机复测待用户）
- 目标：用户实机首跑反馈两点：①Ctrl-C 退出卡死——`摄像头已停止` 打印后进程不
  退，二次 Ctrl-C 打断解释器 atexit 阶段的 `picamera2.close()`（join 预览线程）
  报 "Exception ignored in atexit callback: ... stop_preview ... KeyboardInterrupt"；
  ②速度太快——M 型实机转向角 70~90 时 `turn(18)+move_x(15)` 过快（用户 `sudo
  reboot` 强退）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`：①finally 清理在
  `picam2.stop()` 前 `signal.signal(SIGINT, SIG_IGN)` 且**不恢复**（atexit 回调
  期间 Ctrl-C 不再打断 close）；②新增 `straight_speed`（默认 10，原 18）与
  `turn_move_speed`（默认 8，原 15）属性，execute 改用属性；边走边调新增
  `[`/`]` 直行速度 ±2、`-`/`=` 转向速度 ±2，print 显示 `spd`；README 同步；
  本记录。
- 实施记录：SIGINT 免疫不恢复是为了覆盖解释器退出阶段的 atexit 回调（tune 中
  恢复 old_handler 的做法对 picamera2.close 不够）；速度上限钳到 30。
- 验证：ast 通过；机器重启后部署，py_compile 通过、sha256 一致
  （60803f05…）；main.py 服务正常（Ssl do_wait，SPI 正常）；未实机复测。
- 遗留风险：速度目标值（直行 10/转向 8）按实机再微调；退出仍有 1-2s 的
  picamera2 close 等待属正常。

## 2026-08-30｜巡线"边走边调"：SSH 单键实时调 PID，解决原厂 Kp 极弱不纠偏

- 状态：改动完成（已部署重验证，实机边走边调待用户）
- 目标：用户调好 HSV/裁剪后询问"宽线会怎么走"——推演发现原厂 PID 参数
  P=50（Kp=0.05）+ 直行阈值 8 = 160px 偏差，**画面 320px 内 z_pid 恒 <8 全部判
  直行**，转向只在线完全出画面（cx≤0）时触发；宽线时黑块圆心恒贴画面中心
  （z_pid≈0）恒定直行冲出场地（8-16 乱走与此吻合）。用户选择"边走边调"。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（`FollowLinePID`
  元组→list；主循环加 SSH 键盘 raw 单键监听：`p`/`o` P 增益±50、`i`/`u` D±10、
  Ctrl-C 退出，改后 `PID_init()` 重建控制器即时生效并打印 P/D/V/crop；
  stdin raw、stdout 保持，B 键退出逻辑不变）；README 行为要点同步；本记录。
- 实施记录：raw 只设置 stdin（tty.setraw(sys.stdin)），stdout 的 ONLCR 保留，
  终端 print 正常换行；`PID_init` 重建时积分器清零，调参即时生效。
- 验证：ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （ed3a5170…）；未实机（待用户重启后跑主流程2/巡线现场按 p 调 P）。
- 遗留风险：实机 P 目标值约 300（偏差 27px 即转向）需按场地实测；
  边跑边调时注意狗的运动安全。

## 2026-08-30｜SPI 死锁根治：调参/YOLO 工具移除 LCD，改用浏览器 8090 推流

- 状态：改动完成（已部署重验证；机器当前 SPI 死锁需重启清除）
- 目标：第二次实机复现 SPI 死锁（tune 第二次运行零输出挂死、Ctrl-C 无效，进程卡
  `spidev_ioctl`，与 main.py 同占 /dev/spidev0.0）。根因：本工具虽已停
  raicom-original-main，但该服务 `Restart=on-failure`——原厂 main.py 一旦卡 SPI
  使 systemctl stop 超时被判 failed，服务自动重启，又与工具 LCD 初始化抢 SPI，
  循环死锁。根治：**调参/YOLO 工具彻底移除 xgoscreen LCD（不再碰 SPI）**，画面
  全走 8090 浏览器推流（用户本就是远程看）；调参工具保留低趴姿态（需串口，仍停
  raicom-original-main）；yolo_view 不碰串口/SPI，只停 oumax-camera。
- 影响文件：`follow_line_tune.py`（删 LCD import/初始化/显示；`stop_services`
  停服务后新增 `_wait_inactive` 轮询验证，防 Restart=on-failure 竞态拉起；finally
  清理期间 `signal.SIGINT→SIG_IGN` 免疫，防二次 Ctrl-C 打断 dog.reset/httpd.shutdown
  导致清理不完整+traceback）；`yolo_view.py`（删 LCD；SERVICES 减为只停
  oumax-camera；加 _wait_inactive 与 SIGINT 免疫）；README 调参章节同步；本记录。
- 实施记录：死锁诊断链：第二次运行无输出 + Ctrl-C 无效 → ps 见进程 D 状态
  spidev_ioctl → fuser 确认 main.py 与 tune 同占 /dev/spidev0.0 → 确认
  raicom-original-main.service Restart=on-failure 是自动重启来源 → 移除 SPI 依赖。
- 验证：本机 ast 通过；部署后机器端 py_compile 通过、sha256 一致
  （2b99ce2c…/80c90b59…）、grep 确认无 LCD 代码残留；**机器当前仍有死锁进程
  （main.py + tune 卡 SPI），需用户重启机器后生效**。
- 遗留风险：重启后跑 tune 验证无 SPI 冲突；后续任何新工具不得初始化 xgoscreen
  LCD（除非先禁用 raicom-original-main 的 on-failure 重启并验证独占 SPI）。

## 2026-08-30｜调参工具摆低趴姿态：画面与正式巡线视角一致

- 状态：改动完成（已部署重验证，实机确认待用户）
- 目标：用户运行调参工具验证低趴姿态；原调参工具不初始化 XGO（画面是当前站立
  视角，与正式巡线低趴视角不一致）。改为调参时摆巡线同款低趴姿态（z=10/p=15），
  退出 `dog.reset()` 复位站立。
- 影响文件：`robot_dog_follow_line/scripts/follow_line_tune.py`（import xgolib.XGO；
  新增 `init_low_pose()`：固件识别机型（M→xgomini）后 stop/pace/gait_type/
  translation z=10/attitude p=15，与 follow_line.dog_init 一致；main 在停服务、
  端口检查后调用，finally 中 `dog.reset()` 复位）；README 调参工具章节同步；
  本记录。
- 实施记录：姿态设置在 `stop_services()` 之后（串口已释放）、相机初始化之前；
  狗只有站立→趴下的摆位动作，无行走；退出复位后再由 atexit 恢复服务。
- 验证：ast 语法通过；部署后机器端 py_compile 通过、sha256 一致
  （37acfda3…）；未实机运行（待用户跑 `./follow_line_tune.py` 确认趴下姿态）。
- 遗留风险：实机首跑确认低趴摆位正常（用户当前指令即为此验证）；调参期间狗
  趴着不动，注意别在狗身上放东西。

## 2026-08-30｜巡线加左右裁剪（多线场地防误跟）+ 默认低趴姿态

- 状态：改动完成（已部署重验证，实机调参/巡线待用户）
- 目标：①场地三条线，单独巡线会跟到旁边的线——给视觉处理加左右裁剪（ROI 置零），
  只保留中间区间，并在调参工具中可实时调整裁剪；②站立姿态视角太远，默认姿态
  改为夹球趴下姿态（与抓球接近姿态一致）。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（`load_follow_line_hsv`
  返回新增 crop `[left_x, right_x]` 绝对像素区间，默认 `[0,319]` 全宽；`color_follow`
  增加 crop 属性；`line_follow` 清空上半后对 crop 区间外置零，坐标体系不变；
  `dog_init` 默认 `translation('z', 10)` 低趴，原 z=75 站立）；
  `follow_line_tune.py`（配置读写加 crop、`make_mask` 应用裁剪、画面显示 CROP 值并
  在原图画紫线裁剪边界、按键 `z/x` 左边界±10、`c/v` 右边界±10、`clamp_crop` 保证
  至少 10px 保留）；`robot_dog_follow_line/README.md`（行为要点补裁剪与低趴姿态、
  新增"阈值与裁剪配置"与"调参工具"章节）；本记录。
- 实施记录：crop 用绝对像素坐标（0~319），默认全宽零行为变化；裁剪在 HSV 转换
  前置零（与清空上半同一 img 副本），轮廓/坐标不受影响；调参工具 `q` 保存时
  连同 crop 写入 `follow_line_config.json`，正式巡线启动读取即生效。
- 验证：本机 ast 语法通过、无 CRLF；部署后机器端 py_compile 通过、sha256 与本地
  一致（504a705d…/60751fa4…）；未实机调参/巡线（待用户在场）。
- 遗留风险：低趴姿态（z=10）实际巡航中是否影响步态/速度需实机确认；裁剪边界
  具体值需现场按三线间距调整。

## 2026-08-30｜修复调参/YOLO 工具 SPI 死锁：停服务补 raicom-original-main

- 状态：改动完成（已部署重验证，实机运行验证待用户）
- 目标：follow_line_tune.py 实机首跑卡死——进程 D 状态 `spidev_ioctl`，8090 一直
  是 oumax-camera 原始流；根因是工具只停了相机服务，`LCD_2inch()` 初始化与原厂
  main.py（raicom-original-main.service 常驻刷新 LCD）**并发抢 SPI 总线导致控制器
  挂起**，双进程 ioctl 永不返回，kill -9 无效，只能重启机器恢复。
- 影响文件：`robot_dog_follow_line/scripts/follow_line_tune.py`、
  `robot_dog_ball_grab/scripts/yolo_view.py`（原 `stop_oumax_camera`/`start_oumax_camera`
  改为 `stop_services`/`restore_services`：同时停/恢复 `raicom-original-main` +
  `oumax-camera`，记录启动前 active 状态、退出按原状还原；tune 保留用户新增的
  `assert_port_free` 端口检查与 TUNE 水印）；`docs/ai-records/mistakes/2026-08-30.md`
  （新）；`MISTAKE_INDEX.md`（新条目）；本记录。
- 实施记录：诊断链：8090 显示原画面 → `ps` 见 tune 进程 D 状态 → `/proc/stack`
  定位 `spidev_ioctl` → `fuser /dev/spidev0.0` 发现原厂 main.py（907）与 tune
  同占 SPI → 停 raicom-original-main 时 systemd stop 超时（907 已卡死）→ 用户
  重启机器恢复 → 两个工具补停 raicom-original-main 后重新部署。
- 验证：机器重启后两服务正常；部署文件 LF/可执行/py_compile/ssh sha256 与本地
  一致（c47e7c7c…/a974da79…）；未实机跑工具（待用户在场）。
- 遗留风险：SPI 死锁是否只在并发时触发（单进程独占 SPI 正常），本次重启后
  未实测工具运行；若复现需评估 SPI 独占锁或禁用 LCD 分支。

## 2026-08-30｜修复 follow_line 丢线 bug：原地转圈寻找（只转不走）

- 状态：改动完成（未部署、未实机验证）
- 目标：原厂 follow_line.py 丢线时不会停止——`line_follow()` 未检测到线时返回
  `(0,0,0)` 三元组，`process()` 的 `len(self.circle) != 0` 恒真，`dog.stop()` 分支
  是死代码；丢线被误判为"线在最左侧 x=0"，PID 满偏转 → `turn()` + `move_x(15)`
  前进转向，I 项累计越转越猛（疑为 2026-08-16 实机乱走主因之一）。按用户决策
  改为：丢线时**原地转圈寻找、不前进**。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（`line_follow` 无检测
  返回 None、`__init__` circle 初值 None、`process` 改判 `is not None`，丢线分支
  `dog.turn(50 if L else 18)` 只转不走）；`robot_dog_follow_line/README.md`
  （脚本行为要点同步：丢线 = 原地转圈寻找）；本记录。
- 实施记录：改动 4 处共约 10 行；有检测路径与 PID/execute 逻辑零改动。
- 验证：本机 ast 语法检查通过；未部署、未实机。
- 遗留风险：持续丢线（如线被完全遮挡）会一直原地转圈直至重新见线或人工干预；
  重见线首帧 PID 积分残留可能有一次大转向（随后收敛）。

## 2026-08-30｜follow_line_tune 合成流强化标识（防误连原厂 8090）

- 状态：改动完成
- 目标：实机浏览器见整幅彩色无字——实为仍在看 oumax-camera 原厂流；强化分屏标识，
  停相机后检测 8090 仍占用则硬失败。
- 影响文件：`follow_line_tune.py`；本记录。
- 实施记录：画面加大号 `TUNE`、红白掩码下半、分隔线；首页标题标明 follow_line_tune；
  `assert_port_free` + bind 失败抛错；停服务后 sleep 0.5s。
- 验证：本机未实机；需 scp 后看首页是否有 "NOT oumax-camera" 字样。
- 遗留风险：旧浏览器标签可能缓存旧 multipart，建议硬刷新或开新标签。

## 2026-08-30｜follow_line_tune shebang 改为 xgovenv

- 状态：改动完成
- 目标：实机 `./follow_line_tune.py` 用系统 python3 报 `No module named 'xgoscreen'`，
  改为 shebang 直指厂商 xgovenv。
- 影响文件：`robot_dog_follow_line/scripts/follow_line_tune.py`；本记录。
- 实施记录：shebang `#!/usr/bin/env python3` → `/home/pi/RaspberryPi-CM5/xgovenv/bin/python`。
- 验证：未再实机跑；需重新 scp 后验证。
- 遗留风险：yolo_view 仍可能需 ballenv（含 onnxruntime），与调参工具运行时不同。

## 2026-08-30｜巡线 HSV 调参工具 + YOLO 检查工具 + follow_line 读配置

- 状态：改动完成
- 目标：本机编写巡线阈值调参与 YOLO 框检查工具，并使 follow_line.py 启动时读取同目录
  follow_line_config.json（无配置则原厂默认）；暂不部署。
- 影响文件：`robot_dog_follow_line/scripts/follow_line.py`（掩码改实例属性 + 读 JSON）；
  新增 `follow_line_tune.py`、`robot_dog_ball_grab/scripts/yolo_view.py`；两包
  `CMakeLists.txt`（列入 catkin_install_python）；本记录。
- 实施记录：①`color_follow` 增加 `lower_black`/`upper_black`，`line_follow` 从实例属性
  读掩码（原 `hsv_msg` 形参仍保留未用）；启动加载同目录 JSON，缺省打印提示并保持
  `[0,0,0]`~`[180,255,30]`。②`follow_line_tune.py`：停/atexit 恢复 oumax-camera、
  Picamera2 320×240、视觉与 line_follow 一致、LCD 上下分屏+阈值字、OpenCV JPEG
  自推 8090、SSH 键调 V、q 保存配置。③`yolo_view.py`：默认 letters.onnx（A/B/C/D），
  复用 letterbox/blob/NMS 并画全部框，2× 推流 + LCD，s 存图；两工具均不初始化 XGO。
- 验证：本机 `python -m py_compile` 三脚本通过；未部署、未实机、未浏览器验证 8090。
- 遗留风险：实机首跑需确认免密 sudo 停/启相机服务与 8090 可达；调参后需把
  `follow_line_config.json` 与脚本同目录部署才能让正式巡线生效。

## 2026-08-30｜新增主流程2：开始任务后直接巡线（备选主流程）

- 状态：代码完成（未部署、未实机验证）
- 目标：按用户要求为主流程1（导航 5 点 → 抓球放球）提供备选方案——主流程1
  行不通时，机器端一键"停占串口/相机的服务 → 直接进入黑线巡线"，跳过定点巡航导航。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_follow_line/host/run_main_flow2.sh`
  （一键编排：`systemctl stop raicom-original-main + oumax-camera` → 宿主机 xgovenv
  前台运行 `/home/pi/oumax-xgo/follow_line.py`，路径可用 `RAICOM_XGO_PYTHON`/
  `RAICOM_FOLLOW_LINE` 环境变量覆盖；退出后不自动恢复服务，与主流程1一致）；
  `robot_dog_follow_line/README.md`（新增"主流程2"小节：部署与运行命令）；
  `docs/lingo.md`（新增「主流程2」词条 + 高频索引行）；本记录。
- 实施记录：follow_line.py 为原厂示例**零改动**（HSV 黑线 + PID，启动即 tracking
  巡线）；主流程2 不跑容器（容器 ros-noetic 未直通 /dev/ttyAMA0，串口需宿主机
  权限），沿用 2026-08-16 实机验证过的宿主机 xgovenv 直跑路径；编排脚本风格参照
  `run_ball_in_docker.sh`/`run_main_flow_in_docker.sh`（只停不恢复）。
- 验证：脚本 `bash -n` 语法检查通过；未部署真机、未实机运行。
- 遗留风险：巡线参数仍是原厂默认未标定（2026-08-16 实机首跑乱走），主流程2
  实机可用前须先完成巡线调参；脚本部署到机器后首跑需用户在场确认运动安全。

## 2026-08-17｜定位方案改造：Cartographer 2D 激光里程计 + IMU 桥（odom→base_link 替换 cmd_vel 积分）

- 状态：改动完成（实机静态验证通过，运动验证待用户在场进行）
- 目标：按用户与外部建议，用 Cartographer 2D（+IMU）替代"AMCL 位姿回灌/ cmd_vel
  积分"作为 odom→base_link 激光里程计层；map→odom 暂留 lidar_loc。
- 影响文件：`robot-src/host-services/oumax-xgo/manual_control_server.py`（新增
  read_imu_angles 含 euler 字段，/imu 端点扩展 9 轴结构但回退单轴三连读——见下）；
  新增 `robot-src/catkin_ws/src/robot_dog_navigation/scripts/imu_bridge.py`（轮询
  /imu → 发布 sensor_msgs/Imu，orientation 用 euler、angular_velocity.z 用 yaw
  差分、linear_acceleration 置零）；新增 `robot_dog_navigation/scripts/carto_odom.py`
  （cartographer TF → /odom 消息桥，只发消息不发 TF）；`robot_dog_navigation/CMakeLists.txt`
  （catkin_install_python 加入 imu_bridge.py/carto_odom.py）；`robot_dog_bringup/launch/
  robot_dog_main.launch`（新增 odom_mode arg：cmd_vel/carto/amcl 三态互斥，carto 分支
  含 cartographer_node(gflags args)+imu_bridge+carto_odom，use_amcl 保留向后兼容并
  前移定义）；新增 `robot_dog_navigation/config/cartographer_2d.lua`（纯激光 2D SLAM，
  use_imu_data=false）；本记录与 mistakes 记录。
- 实施记录：①调查真机 IMU 链路：8765 manual 服务（oumax-manual-control.service，
  与 raicom-original-main Conflicts）未运行；xgolib 1.0.3 提供 read_imu()（0x65
  批量 9 轴）与 read_yaw/pitch/roll（0x66/67/68 单轴）。②抓原始帧验证：**0x65 在
  M-7.0.0b8 固件返回固件版本串，read_imu() 不可用**；0x66/67/68 有效（yaw 为累积
  角 -3847°~-4129°，pitch/roll 体角度）。固件无原始 accel/gyro 流 → IMU 桥
  angular_velocity.z 用 yaw 差分、accel 置零；Cartographer 将配置
  use_imu_data=false（纯激光 2D SLAM）。③部署：manual_control_server.py 已部署
  真机并重启服务（8765 正常，/imu 返回 yaw/pitch/roll/euler）；imu_bridge.py 已
  部署 ros_ws + 容器 catkin_make 通过（devel 空间 6 脚本齐全，发现真机 CMakeLists
  为旧版缺 main_flow 声明，已同步仓库新版）。④Cartographer 安装：arm64 官方无
  预编译包（snapshots + packages.ros.org 均无），改源码编译——本机下载
  cartographer/cartographer_ros 1.0.0 tag 源码 → scp → docker cp 容器，依赖
  （ceres/protobuf/lua5.3/glog/gflags/boost）apt 安装中，编译进行中。
- 验证：/imu 端点 curl 返回有效姿态（yaw 累积角连续变化、pitch/roll 稳定）；
  imu_bridge.py 本地 py_compile 通过；**Cartographer 编译与实机静态验证全部通过**：
  ①cartographer 1.0.0 源码编译成功（-j2，本机下载 → scp → 容器，注释测试段避开
  g++9 iterator_traits 错误，functions.cmake -std=c++11→14 满足 PCL1.10）；
  cartographer_ros_msgs/cartographer_ros 编译安装（cartographer_rviz 删除，不需要）；
  ②carto 模式 launch 节点集正确（cartographer_node+imu_bridge+carto_odom+lidar_loc，
  无 simple_odom，use_amcl 兼容保留）；③实机静态启动（enable_motion:=false）：
  cartographer 发布 odom→base_link TF（~10Hz 匹配更新）、carto_odom 发 /odom 30Hz、
  imu_bridge 发 /imu 30Hz（yaw 差分角速度）、lidar_loc 发 map→odom（修正量趋 0）、
  move_base 正常（costmap 已建，/move_base/status 发布）；④位姿稳定性：机器静止
  40s，yaw 收敛 -2.93°±0.1°，位置 ±2cm 匹配噪声带内（可接受）。
- 遗留风险：①实机运动验证未做（enable_motion:=true 需用户在场安全确认）：纯激光
  （无 IMU、无编码器）在足式颠簸/快速转向时 yaw 估计鲁棒性、导航联调（move_base+
  cym_planner 走点）效果待验证；②cartographer 静止时位置 ±2cm 匹配噪声，运动场景
  是否被 motion_filter/匹配吸收待观察；③0x65 批量读若后续固件升级可用，可升级为
  全 9 轴 IMU（服务端与 imu_bridge 已留字段扩展点）；④容器内编译产物（/usr/local
  cartographer、catkin_ws 三个包）在容器重建后会丢失，需固化进镜像或重建后重跑
  编译流程（本记录含完整步骤）；⑤机器重启后 oumax-manual-control 不自启（disabled），
  需手动：停 raicom-original-main → 启 oumax-manual-control。

## 2026-08-17｜实机导航改造：AMCL 全权定位替代 cmd_vel 积分 odom（foot 步态无编码器）

- 状态：改动完成（实机验证未完成——机器断电）
- 目标：主流程实机跑通后 waypoint 5 失败，排查确认 simple_odom（cmd_vel 积分）是
  定位污染源；按用户判断改为"foot 步态无编码器、odom 不可信，比赛场景激光始终
  可用，定位全权交给 AMCL"。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_navigation/scripts/odom_from_amcl.py`
  （AMCL 位姿 EMA 平滑后直接作为 odom→base_link 与 /odom，替代 cmd_vel 积分）；
  `robot_dog_navigation/scripts/simple_odom.py`（yaw_jump_limit 默认 0.4→1.5，修复
  转向 delta 被丢弃）；`robot_dog_bringup/launch/robot_dog_main.launch`（simple_odom
  加 `unless="$(arg use_amcl)"`，use_amcl group 新增 odom_from_amcl 节点）；本记录。
- 实施记录（实机 192.168.137.157，用户在场）：
  ①主流程实机全链路首跑：导航 1-4 点真到达（容器化链路验证通过），**waypoint 5
  ABORTED**——move_base "Failed to find a valid control. Even after executing
  recovery behaviors"（7s 即败，机器停在 (2.03,-0.19)，P5 目标 (1.30,-0.175)）。
  ②球程序容器内真实运行验证通过：`ros-noetic-ball` 内编排→抓球程序完整拉起，
  YOLO 推理循环运行（模型/相机/串口全链路 OK）。
  ③odom 污染实锤：机器静止时 odom→base (4.88,2.49) yaw 134° vs 实际
  (2.03,-0.19) yaw≈101°；日志 `imu yaw jump 0.43 rad dropped`（yaw_jump_limit=0.4
  把 XGO 脉冲式转向当跳变丢弃，丢弃后 _last_raw=raw 永久抹掉该段航向 → 平移积分
  方向错 → odom 路径分叉）；另有 8 次 imu fetch failed。
  ④按用户决策实施 AMCL 全权定位：odom_from_amcl 订阅 /amcl_pose，EMA（α=0.4）+
  静止死区（5mm/0.005rad）平滑，直接发布 odom→base（AMCL 的 map→odom 自动趋于
  恒等）；首帧前用 init 位姿发 TF 打破"AMCL 等 laser→odom TF、odom 节点等
  amcl_pose"的死锁（实机踩到并修复）。
  ⑤新架构启动验证通过：AMCL 正常发布位姿、/odom 10Hz、map→odom 恒等 (0,0,0)。
  ⑥单点测试（0.5m goal）执行中**机器断电**，实机验证中断。
- 验证：新架构静态验证全部通过（amcl_pose 发布、odom 10Hz 跟随、TF 链完整、
  map→odom 恒等）；实机运动验证（单点/主流程）未完成。
- 遗留风险：①新架构核心风险——AMCL 运动模型输入变为自身输出的平滑值，机器运动时
  粒子跟随性/定位延迟待实机验证（若跟不上需调 alpha/粒子参数）；②odom_from_amcl
  的 twist 供局部规划器用，AMCL 修正跳变被 0.05m/0.1rad 阈值挡掉不计速度，实机
  观察；③机器来电后按 08-16 总结 §4 顺序：restore_mode（本次已做过一次，若再次
  F 测试需重做）→ 单点测试新 odom 架构 → 重跑主流程全链路；④simple_odom 的
  yaw_jump_limit 修复只对非 AMCL 模式生效（未实机验证）。

## 2026-08-17｜新建底层运动控制包 robot_dog_control：cmd_vel 桥自 robot_dog_teleop 迁入

- 状态：改动完成
- 目标：按用户要求补建 catkin 工作空间缺失的底层运动控制功能包，把 cmd_vel→OUMAX 手控
  服务桥接节点 `oumax_cmd_vel_bridge`（含急停/看门狗/步态模式）从 robot_dog_teleop 迁入
  新包 `robot_dog_control`，作为控制层统一承载地。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_control/`（scripts/oumax_cmd_vel_bridge.py
  为 git mv 迁入、package.xml、CMakeLists.txt、README.md）；
  `robot-src/catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`（桥启动
  pkg 改 robot_dog_control 并加注释）；`robot_dog_teleop/README.md`（「真实控制桥接」节
  补迁移说明）；`.agents/skills/project-index/INDEX.md`（新增「运动控制」行、更新时间）；
  `docs/ai-records/CHANGE_LOG.md`。
- 实施记录：纯包归属迁移，节点行为零变化（节点名/话题/全部参数/HTTP 客户端原样，git mv
  保留历史）；新包 package.xml 依赖 rospy/geometry_msgs/std_msgs（桥脚本实际 import）；
  CMakeLists 把桥列入 catkin_install_python（旧包未列入，属补齐，install 空间也可用）；
  启动入口不变，仍由 robot_dog_main.launch 统一启动。
- 验证：py_compile 通过；launch XML ElementTree 解析通过；git status 确认 rename 记录、
  teleop 包内无残留脚本；全仓 grep 确认唯一 pkg 启动引用已指向 robot_dog_control，其余
  命中均为 docs 历史记录、simple_odom.py 与 move_base.yaml 注释（不改）。
- 遗留风险：机器端 `/home/pi/ros_ws/src/` 副本需同步部署新包并在容器内 catkin_make 后
  实机回归（launch 节点解析 + enable_motion:=true 实机运动场景）；迁移本身未实机验证。

## 2026-08-17｜主流程全部容器化（实机）：球程序容器 ros-noetic-ball 落地 + 相机/串口全链打通

- 状态：改动完成
- 目标：按用户要求，主流程（导航 5 点 → 抓球放球）不再在宿主机跑程序，全部走容器。
- 影响文件：`robot_dog_navigation/scripts/main_flow.py`（`--grab-release-ssh` 改为仅停服务，
  球触发经 ssh `docker exec` 进球容器，新增 `--grab-release-container`/`--grab-release-runner`）；
  新增 `robot_dog_navigation/host/run_main_flow_in_docker.sh`（宿主机一键入口）；
  新增 `robot_dog_ball_grab/host/setup_ball_container.sh`（球容器创建/配置，幂等）与
  `run_ball_in_container.sh`（球容器内运行入口）；重写 `run_ball_in_docker.sh`；
  `robot_dog_navigation/README.md`、`robot_dog_ball_grab/README.md`、`docs/lingo.md`、
  `.agents/skills/project-index/INDEX.md`、`docs/technical/2026-08-16-docker-runtime-unification.md`、
  本记录。
- 实施记录（机器实机 192.168.137.157，用户在场）：
  ①**restore_mode 恢复腿模式**（08-16 遗留第一优先）：宿主机 xgovenv 执行成功
  （`wheel control disabled; foot mode restored`），raicom-original-main 恢复 active。
  ②**导航容器重建**：旧容器仅挂 ros_ws/ydlidar 且无 ttyAMA0 直通；`docker update`
  不支持 --device-add → rename 旧容器兜底后按原配置重建，补 `-v /home/pi:/home/pi` 与
  `--device /dev/ttyAMA0`。导航容器内 xgovenv 复用验证失败——**focal 与宿主机
  Python 3.11 / libcamera 0.3 不兼容（硬性版本矛盾，方案文档 §3 已预警）**。
  ③**球程序独立容器方案**：新容器 `ros-noetic-ball`（debian:bookworm-slim，与宿主机
  同基线）——容器内自建 ballenv（pip 装 numpy==1.24.2、opencv-python==4.11.0.86、
  onnxruntime==1.20.0，与宿主 xgovenv 对齐）+ `.pth` 兜底宿主 dist-packages 与
  xgovenv site-packages（含 editable 的 uiutils src）+ `LD_LIBRARY_PATH` 兜底宿主
  `/usr/lib/aarch64-linux-gnu` + 挂载 `/usr/lib/aarch64-linux-gnu/libcamera`（IPA）、
  `/usr/share/libpisp`、`/usr/share/libcamera`（tuning）、`-v /dev:/dev`（全设备）+
  `--privileged` + 容器内跑 **udevd**（libcamera 的 udev 枚举器依赖 /run/udev/data
  数据库，缺之相机枚举为空且静默——最深的坑）+ `RPI_LGPIO_REVISION=00c041a0` 环境
  变量绕过 rpi-lgpio 的 device-tree 检测 + 复制宿主 pinctrl 工具。
  ④**全链验证 ALL_OK**：xgolib 串口固件识别（xgomini）、SPI 屏初始化、
  cv2/numpy/onnxruntime import、**Picamera2 实拍 (480,640,3)** 全部通过。
  ⑤球包/主流程脚本/球容器 host 脚本全部部署至机器 catkin_ws
  （`/home/pi/ros_ws/src/...`，容器内 `/root/catkin_ws/src/...`），md5 校验一致、LF 干净。
  ⑥机器端旧 `run_main_flow.sh` 传参与新语义兼容（`--grab-release-ssh pi@127.0.0.1`），
  仅需重新部署 main_flow.py。
- 验证：球容器全链验证脚本 ALL_OK；部署 6 文件 md5 与仓库一致；服务恢复
  raicom-original-main/oumax-camera active；main_flow.py py_compile 通过。
- 遗留风险：①主流程全链路（导航 5 点 → ssh 停服务 → docker exec 球容器抓球放球）
  实机未跑，导航 launch 未启动（容器重建后需按 08-16 总结 §1 重建系统）；②球程序
  实机动作（抓球/放球）未在容器内验证——相机/串口/依赖链已通，但视觉参数
  （target_radius 等）在容器内的实际表现待实机跑球编排确认；③球容器内 GPIO.setmode
  有 "No GPIO chips found"/"sudo: not found" 警告（uiutils 顶层 setmode 失败但被吞，
  球程序不用 GPIO，暂不影响；如后续程序需 GPIO 按钮需再处理）；④setup 脚本幂等但
  udevd 是容器内进程，容器重建后需重跑 setup（脚本已固化该步骤）。

## 2026-08-16｜巡线（黑线）实机首跑：脚本部署 + 宿主机 xgovenv 运行 + 容器串口直通缺失发现

- 状态：改动完成
- 目标：把 `follow_line.py` 部署到机器并实机跑一遍黑线巡线。
- 影响文件：机器 `/home/pi/oumax-xgo/follow_line.py`（scp 部署，SHA-256 `0eae5b47…` 与仓库 `robot_dog_follow_line/scripts/follow_line.py` 一致）；`docs/lingo.md`（新增「巡线」词条）；`docs/ai-records/{CHANGE_LOG,MISTAKE_INDEX}.md`、`mistakes/2026-08-16.md`。
- 实施记录：①机器离线（ping 不通）→ 用户开机后连通（9ms，SSH 免密可用）；②停 `raicom-original-main` + `oumax-camera` 释放串口/相机；③**发现容器 `ros-noetic` 未直通 `/dev/ttyAMA0`**（`docker inspect` 仅 ydlidar/video0 直通），与 `docs/technical/2026-08-16-docker-runtime-unification.md` 声称的"设备直通 /dev/ttyAMA0"不符 → 不改容器（导航还在用），改用宿主机 `/home/pi/RaspberryPi-CM5/xgovenv/bin/python` 直接运行（pi 在 dialout 组，串口/相机权限够）；④nohup 后台运行：相机初始化成功、固件识别 xgomini，进入 tracking 巡线——初始转向角 70.7 大幅纠偏 → 持续转向角 8.0（PID 饱和边界）微调；⑤用户叫停：首次 `pkill -f` 匹配远程 shell 自身导致命令中断（python 进程实际已杀），二次确认后恢复两服务 active。
- 验证：运行期间日志持续输出 PID 转向/前进决策；停止后 pgrep 无 python 巡线进程；`raicom-original-main`/`oumax-camera` 恢复 active。实机结果：**未正常巡线、乱走**（用户现场确认，全程转向角 ≥8 饱和、未见直行段）。
- 遗留风险：容器缺 `/dev/ttyAMA0` 直通，README/方案文档与实机不符——容器内跑厂商程序需 docker update/重建容器补串口，或继续宿主机 xgovenv 直跑；巡线乱走待现场调参（HSV 掩码/黑线宽度/PID 或转向速度映射，原厂默认参数未标定）；**巡线启动改由用户手动执行，AI 不再自动启动**（lingo 词条已注明）。

## 2026-08-16｜厂商示例全部入库 + 运行环境统一容器化方案

- 状态：改动完成
- 目标：把其余厂商示例程序也写入 ROS 功能包；统一运行环境为 ros-noetic Docker 容器（消除宿主机/容器割裂），抓球程序一并容器化。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_demos/`（Mini3W_W 12 个顶层脚本 + common 13 个 + follow_person/speech/face_classification 子目录，61 个内容文件、零代码改动、SHA-256 全量一致）；新增 `robot_dog_demos/host/run_demo_in_docker.sh` 与 `robot_dog_ball_grab/host/run_ball_in_docker.sh`（容器内 xgovenv 运行封装）；`docs/technical/2026-08-16-docker-runtime-unification.md`（方案文档）；`robot_dog_ball_grab/README.md`、`robot_dog_follow_line/README.md`、`robot_dog_demos/README.md`（运行方式改为容器化说明）；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：①demos 包参照 robot_dog_follow_line 结构，来源 `archive/full-device-source/home-pi/RaspberryPi-CM5/`（Mini3W_W/demos 与 common/demos），剔除 follow_line.py（独立包）、YDLidar-SDK（robot_dog_lidar 使用）、xiaozhi_test 与云服务子项目（mcp_server/realtime_dialog/WIFI/AI_gym/sample/src）；56 个 py 仅 3 个带 shebang 且均合法，零调整。②容器化方案：容器挂载 `/home/pi`（厂商 xgovenv 同路径复用）+ 设备直通 `/dev/ttyAMA0`、`/dev/video0`，主流程 `--grab-release-ssh` 跳板改为容器内直接执行（待实机）；备选 pip 方案因 picamera2 在 Focal 无 wheel 不推荐。③两个 host 封装脚本按 robot_dog_teleop/host/launch_*.sh 风格（docker exec + 可选 --release-camera-serial 停 oumax-camera/oumax-manual）。
- 验证：demos 包 56 个 py 全部 py_compile 通过、package.xml XML 解析通过、入库后凭据扫描零命中、61 个文件与 archive 源逐文件 SHA-256 一致；两个 host 脚本 bash -n 语法检查通过（见下方验证补充）；README 更新为容器化说明。
- 遗留风险：机器离线，容器挂载/设备直通与"容器内运行厂商程序"均未实机验证（方案文档 §2.3 列出检查清单，§4 列出实施步骤）；picamera2/xgolib 依赖的 /dev/video0、/dev/ttyAMA0 直通需重建或 docker update 容器；xgoscreen SPI 屏在容器内可能不可用，部分示例显示功能需评估；主流程抓球触发方式（ssh 跳板 → 容器内直接执行）待实机改造。

## 2026-08-16｜厂商巡线示例纳入 ROS 功能包：新增 robot_dog_follow_line

- 状态：改动完成
- 目标：把厂商巡线示例 follow_line.py 写入 catkin 功能包，作为巡线任务代码存放处。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_follow_line/`（scripts/follow_line.py、CMakeLists.txt、package.xml、README.md）；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：包结构参照 robot_dog_ball_grab（scripts + catkin_install_python，脚本非 ROS 节点、机器端宿主机直接运行）。脚本取自 `archive/full-device-source/home-pi/RaspberryPi-CM5/robots/Mini3W_W/demos/follow_line.py`（与 Dog_LM 版 SHA-256 一致，28A134C8…）；仅做最小调整：shebang 从第 6 行移到首行并改为 `#!/usr/bin/env python3`（原文件 shebang 在 docstring 之后无效），其余代码零改动。README 记录运行环境（机器端 xgovenv，含 uiutils/xgolib/picamera2/xgoscreen，系统 Python 不可用）、行为要点（HSV 黑掩码 [0,0,0]-[180,255,30]、最大轮廓、PID(P=50,D=30)、|z_pid|<8 直行 move_x(18)、≥8 转向、未检测到线停止、固件首字符识别 xgolite/xgomini、A/C/D 按钮切状态、B 退出）、部署运行与停服务注意事项。
- 验证：python py_compile 通过；package.xml XML 解析通过；逐行对比确认除 shebang 外与厂商原版一致（去除 shebang 行后 Compare-Object 无差异）。
- 遗留风险：脚本依赖机器端专有运行时与硬件（Picamera2/XGO 串口），本地不可运行；掩码范围需按实机光照调节；尚未部署到机器（机器当时离线）。

- 状态：进行中
- 目标：实机跑通主流程全链路（导航 5 点 + 抓球放球）。
- 影响文件：`docs/technical/2026-08-16-main-flow-debug.md`（完整调试总结：时间线/根因/标定数据/遗留事项）；`CHANGE_LOG.md`。
- 实施记录：详见总结文档。核心进展：①桥 x 步长死区修复后导航 5 点真走通（缩点路径）；②CRLF 污染修复（simple_odom shebang）；③AMCL 静止漂移修复（过滤半径 0.45→0.25）；④odom_scale 标定 0.23（轮足打滑 ±20% 物理限制，靠视觉闭环兜底）；⑤发现 XGO mini3W 轮足打滑导致位移不可重复；wheel 模式不可用、锁轮（128）+move_x 可用但不显著改善重复性；⑥⚠️ F 测试后狗留在 wheel 模式未恢复，主流程 move_x 失效原地转圈——`restore_mode.py` 已写好待机器来电执行。
- 验证：导航 5 点跑通（odom_scale 修正后）；单点 1.0m goal 多次实测 85~146cm（打滑离散）；AMCL 静止稳定 (0,0,0)。
- 遗留风险：机器断电充电中；来电后按总结文档 §4 顺序执行（恢复模式 → 跑主流程 → 补地图 → DWA 对比可选）；手控服务卡死原因未查。

## 2026-08-16｜CRLF 修复 + 系统重建：simple_odom/AMCL/move_base 全链路恢复

- 状态：改动完成
- 目标：排查主流程实机调试中 simple_odom 在 roslaunch 里启动即死（exit 127）、TF 缺 odom→base_link 导致 AMCL 不发 map TF、move_base 卡"Timed out waiting for transform"。
- 影响文件：`robot-src/catkin_ws/src/robot_dog_navigation/scripts/simple_odom.py`（新增 odom_scale 标定参数，位移乘标定系数；修复部署版 CRLF 行尾）；`main_flow.py`（部署版 CRLF 修复）；机器端容器内 sed 转 LF + launch 重启；`docs/ai-records/mistakes/2026-08-16.md`、`MISTAKE_INDEX.md`、`CHANGE_LOG.md`。
- 实施记录：simple_odom 手动 `python3` 显式调用正常、roslaunch 直接执行（shebang）崩溃——根因是 Windows 端 scp 部署的脚本带 CRLF，shebang 变 `python3\r`（exit 127，掩盖于手动调用）。期间还处理了：整机重启后的系统重建流程（acquire → roscore → launch，docker exec -d 方式）、pkill -f 匹配自身、手控服务未恢复导致桥 refused、雷达 /dev/ydlidar 设备节点需容器重启重挂等。修复后 rosnode 全 12 节点（含 simple_odom）、TF map→base_link (0,0,0)、AMCL 发布位姿正常。
- 验证：rosnode list 含 /simple_odom；tf_echo map base_link = (0,0,0)；/scan 10Hz、/scan_filtered 10Hz；amcl_pose 有输出。
- 遗留风险：odom_scale 尚未标定（默认 1.0）——主流程"移动距离太短"问题待标定实验（发 1.0m goal 量实际距离 → scale=实际/1.0 → 写入 launch）；主流程右侧路径仍按已知区收缩（0.5,0.25,-0.575），地图右下角待补扫。

## 2026-08-15｜主流程实机首跑：只转不走，桥 x 步长死区修复（进行中）

- 状态：进行中
- 目标：实机跑通主流程（定点巡航 5 点 → 抓球放球）；首跑发现"只能左右转、无法前进"。
- 影响文件：`robot-src/catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`（桥参数 x_scale_ref 4.0→0.2、新增 linear_motion_value 25、x_min_step 12→15、dead_zone_wz 0.05→0.10）；`robot-src/catkin_ws/src/cym_planner/config/cym_planner_params.json`（lookahead_distance 0.5→1.0、heading_tolerance 0.2→0.6、final_yaw_tolerance 0.08→0.15）；部署版 `/home/pi/ros_ws/...` 与 `/home/pi/run_main_flow.sh` 已同步（md5 校验一致）；`docs/ai-records/mistakes/2026-08-15.md`、`MISTAKE_INDEX.md`、`CHANGE_LOG.md`。
- 实施记录：系统改为机器端本地 master（容器 roscore + robot_dog_main.launch，local_master_ip:=192.168.137.157，AMCL 模式，init 0,0,0，enable_motion:=true）；主流程经 `/home/pi/run_main_flow.sh` 一键执行（容器内跑导航，导航完成后 ssh 本机停 oumax-manual 释放串口并跑 ball_grab_release.py，容器→宿主机 ssh 免密已配置）。首跑失败"只转不走"：根因①桥 x 映射 x_scale_ref=4.0 使 vx 0.1~0.8 只映射到步长 12~13（XGO 固件死区边缘，实测 13 不动），yaw 步长 17~27 明显；根因②桥 yaw 优先分支在 vx/wz 同时非零时吃掉 x。修复（x_scale_ref=0.2、linear_motion_value=25、x_min_step=15、dead_zone_wz=0.10）后单点测试桥发出 x=25 满步长、狗实际前进；主流程重跑 waypoint1 (2.3,0) 12s 真到达、waypoint2 4s，waypoint3 仍 ABORTED——原因：实机地图 `ricam_arena_mapped`（8-15 03:42 建图）右下角未扫到（y≤-1.2 全未知，navfn 把 unknown 当 lethal），且 y=-0.85~-1.1 存在实时障碍膨胀高代价带（cost 99-100）。按用户要求放宽追线参数（lookahead 1.0 / heading_tolerance 0.6 / final_yaw_tolerance 0.15）并把 `--side-distances` 缩到已知区（0.5,0.25,-0.575，y≥-0.75）。
- 验证：单点测试（0.5m goal）桥发 x=25 步长、狗实际前进（用户确认）；主流程 waypoint1/2 真走通；waypoint3 缩点后尚未实机复测（机器断电）。
- 遗留风险：地图右下角缺失导致原路径（右方累计 2.15m）不可达——最终比赛路径需补建图扫右下角后恢复 0.5,1.65,-0.575；实时障碍膨胀带（y<-0.85）在实机布局确认前限制右侧活动范围；手控服务 06:24 曾卡死 07:05 被 systemd 重启（原因未查）；AMCL 曾假定位（odom/激光匹配行为待观察）；x=15/25 步长与放宽后的追线参数实机效果待复测。
- DWA 对比验证（新增）：为验证"局部规划器追线/容差是否导致走走停停"，新增标准 DWA 切换：`robot_dog_main.launch` 加 `local_planner` arg（cym 默认 / dwa 可选），新增 `robot_dog_navigation/config/dwa_planner.yaml`（DWAPlannerROS 参数：max_vel_x 0.4、xy_goal_tolerance 0.10、yaw_goal_tolerance 0.15 等）；`move_base.yaml` 的 base_local_planner 移到 launch 按 arg 设置。机器来电后部署并 `local_planner:=dwa` 重启 launch，单点/主流程对比狗的行为，排除/确认 cym_planner 参数问题。

## 2026-08-15｜主流程：定点巡航 → 抓球放球 一键编排

- 状态：改动完成
- 目标：按用户要求写比赛主流程：上电后定点前方 2.3 米（朝向与初始相差 90° 向右），再依次定点右方 0.5/1.65 米（累计 2.15 米）与左方 0.575 米（回撤至累计 1.575 米，朝向与初始呈 180°），最后沿当前朝向前进 1 米（朝向与第一个点相同），随后运行抓球放球程序。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_navigation/scripts/main_flow.py`；`CMakeLists.txt`（catkin_install_python 声明）；`README.md`（新增「主流程」章节）；`docs/lingo.md`（新增「主流程」词条）；`.agents/skills/project-index/INDEX.md`（导航行说明更新）；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：路径以起点为原点、初始朝向为 0 基准的相对位姿定义（x 前 y 左、右转 yaw 为负），再经旋转叠加到地图绝对坐标，与实机建图方向解耦（起点按 AMCL 原点摆放 init 0,0,0 时即等价绝对路径）；5 个点依次经 actionlib 发 move_base goal 并等待 SUCCEEDED（失败/超时报错退出，无 pass-through——每个点都需要转向到位）；全部到达后 subprocess 运行同目录 `ball_grab_release.py`（默认路径同目录解析，`--grab-release-script` 可覆盖），`--enable-motion` 门禁透传。距离/角度全部参数化（`--forward-m 2.3 --side-distances 0.5,1.65,-0.575 --final-forward-m 1.0 --turn-deg 90`，side 正值=右方、负值=左方），实机标定时可调，方向反了把对应参数取负。
- 验证：本地 `py_compile` 通过；`build_waypoints`/`to_map` 纯逻辑自检：起点面向南场景下 P1(0,-2.3) 朝西 → P2(-0.5,-2.3)/P3(-2.15,-2.3) 朝北 → P4(-1.575,-2.3)（左方回撤 0.575）朝北 → P5(-1.575,-1.3) 朝西，终点落在场地左下角球区附近，全部点在场内。P4 方向按用户修正为左方 0.575 m（`--side-distances` 第三项取负）。
- 遗留风险：实机尚未运行验证；move_base 带朝向 goal 的原地转向（90°/180°）此前只验证过直线前进，需实机确认；起点默认从 tf 读取（AMCL 收敛后），若起点与地图原点有偏差，路径会整体偏移；主流程需部署到机器端 ROS 容器（脚本 + 球编排同目录），球程序路径与串口控制权按部署形态确认。

## 2026-08-15｜实机定点导航：地图修正 + AMCL 定位替代 lidar_loc

- 状态：实机验证通过
- 目标：实机定点导航"掉头向后走"问题（已修 lidar_loc y 镜像后仍不稳定），切换 AMCL 定位并修正实机地图。
- 影响文件：`robot-src/catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`（新增 `use_amcl` arg：true 时起 amcl 替代 lidar_loc，参数 base_frame_id=base_link / scan_topic=/scan_filtered / likelihood_field / initial_pose 取 init_x/y/yaw / min-max particles 500-2000）；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：实机排查发现（1）launch 默认 `map_file` 是离线小地图 `ricam_arena`（3×2.5m），实机应加载建图保存的 `ricam_arena_mapped`（1312×1312 @ 0.02m，origin [-12.38,-12.14]），且机器在原点摆放时应 `init_x:=0.0 init_y:=0.0`（launch 默认 -0.70/1.00 是离线小地图位姿）；（2）lidar_loc 贪心匹配（±1°±1px 局部搜索、收敛判据只看 10 帧稳定不看质量）在实机场地持续漂移（yaw 15-70°、位置跳变），换 AMCL 后收敛稳定；（3）多次 roslaunch 残留同名节点注册导致新节点被挤掉（"new node registered with same name"），需先清干净再启动。
- 验证：实机 `use_amcl:=true map_file:=ricam_arena_mapped.yaml init_x:=0.0 init_y:=0.0 init_yaw:=0.0` 启动，amcl 收敛于 (0,0,0) 稳定；发 goal (1.0, 0.0)，`Goal reached`，终点 (0.989, -0.020, yaw 4.9°)，直线前进无掉头。
- 遗留风险：lidar_loc 仍保留在 launch（use_amcl 默认 false），修复后的 y 符号改动已部署但未再单独实测；amcl 参数（粒子数、laser_max_range=8.0）未做长距离/复杂场景调优；amcl 需 initial_pose 大致正确（原点摆放 + init 参数对齐已验证）。

## 2026-08-15｜修复 lidar_loc 激光点云 y 镜像导致定位 180° 错位

- 状态：改动完成
- 目标：修复定点导航"定点在前方、机器掉头向后走"问题。静态分析定位到 `lidar_loc.cpp` 扫描点转换用 `y = -r*sin(angle)`，与仓库其他节点（`scan_to_cloud_and_body.py`、`scan_circle_filter.py` 均为标准 `+sin`）相反，点云左右镜像 → 贪心匹配收敛到 180° 镜像位姿 → `map→base_link` 朝向错 → cym_planner 掉头。
- 影响文件：`robot-src/catkin_ws/src/jie_ware/src/lidar_loc.cpp`（`y_laser` 去掉负号）；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：仅改 `y_laser = -r*sin(angle)` → `y_laser = r*sin(angle)` 一行，并加注释说明标准约定。`lidar_is_inverted` 分支基于 TF roll 检测，本项目 `laser_frame_tf.py` 发布单位旋转（roll=0）不触发，无需改动；`initialPoseCallback`/`pose_tf` 的 yaw 双取负互相抵消，也不动。
- 验证：静态比对三处 scan 转换公式（lidar_loc / scan_to_cloud / scan_circle_filter）确认只有 lidar_loc 一处负号；LSP 报错均为本机缺 ROS 头文件的环境噪音。
- 遗留风险：实机需重新 `catkin_make --pkg jie_ware` 并部署（按惯例先备份至 `/home/pi/ros_ws/backups/`）；`lidar_loc` 须与 `initial_pose_publisher` 同启（单独重启会卡地图原点）；改后实机验证顺序：RViz `/lidar_points` 与 `/map` 重合 → `tf_echo map base_link` RPY 与狗头一致 → 2D Nav Goal 全程。**不需要重新建图**（地图由 gmapping 标准转换生成，一直正确；bug 只污染 map→odom TF）。

## 2026-08-15｜放球/旋转/编排程序并入抓球包 robot_dog_ball_grab

- 状态：改动完成
- 目标：按用户要求把所有程序（抓球、放球、旋转、一键编排）统一放入 `robot_dog_ball_grab` 包。
- 影响文件：移动 `ball_release.py`/`rotate.py`/`ball_grab_release.py` 至 `robot-src/catkin_ws/src/robot_dog_ball_grab/scripts/`；删除 `robot_dog_ball_release/` 包；`robot_dog_ball_grab/{CMakeLists.txt,README.md,package.xml}` 更新（四脚本安装声明、合并文档）；`docs/lingo.md`（放球序列/抓完掉头放球/yaw 补偿词条按实机标定更新）、`.agents/skills/project-index/INDEX.md`（合并抓球/放球任务行）、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：四脚本同目录（仓库 `scripts/` 与机器端 `/home/pi/oumax-xgo/` 形态一致）；编排脚本移除 `_find_script` 分包回退逻辑（同目录直接解析）；README 汇总实机标定参数：抓球瞬间与放球瞬间 y=-3 补偿（原 -6 调小）、接近阶段不加补偿、180° 掉头 turn 脉冲 9s（attitude y=180 不生效已弃用）、放球对齐 60s 超时后继续放球。
- 验证：四脚本本地 `py_compile` 通过；放球包目录已删除（Test-Path False）。
- 遗留风险：机器端 `/home/pi/oumax-xgo/` 四脚本与仓库需保持同步（本次移动不改程序内容，仅仓库组织变化；机器端编排脚本已同步最新版）。

## 2026-08-15｜抓球→旋转180°→放球 一键编排程序

- 状态：进行中
- 目标：按用户要求写一个编排程序：抓球程序完成后旋转 180 度，再运行放球程序。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_ball_release/scripts/{rotate.py,ball_grab_release.py}`、`CMakeLists.txt`、`README.md`；`docs/lingo.md`、`.agents/skills/project-index/INDEX.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：待更新。
- 验证：待更新。
- 遗留风险：待更新。

## 2026-08-15｜抓球→旋转180°→放球 一键编排程序

- 状态：改动完成
- 目标：按用户要求写一个编排程序：抓球程序完成后旋转 180 度，再运行放球程序。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_ball_release/scripts/{rotate.py,ball_grab_release.py}`、`CMakeLists.txt`（新增两脚本安装声明）、`README.md`（新增「一键编排」章节）；`docs/lingo.md`（高频索引「抓完掉头放球」行，指向新词条「抓完掉头放球」）、`.agents/skills/project-index/INDEX.md`（放球任务行说明更新）、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：三个独立进程顺序串联，各自取得/释放串口控制权，避免跨进程串口竞争，且不改动已实机验证的抓球/放球程序本体：阶段 1 `ball_yolo_grab.py`（透传 --model/--target-radius/--confidence）、阶段 2 `rotate.py --yaw 180`（dog.attitude("y", 180) 目标角掉头，--settle 默认 3s 稳定）、阶段 3 `ball_release.py`；编排脚本默认按同目录解析脚本（机器端部署形态 /home/pi/oumax-xgo/），找不到时回退仓库分包相对路径；`--enable-motion` 门禁透传三阶段；日志 `stage=1/3`…`action=grabrelease-complete`。
- 验证：三个脚本本地 `py_compile` 全部通过；编排默认路径解析逻辑静态复核（机器端同目录与仓库分包两种形态均可解析）。
- 遗留风险：`dog.attitude("y", 180)` 大角度掉头尚未实机验证（若不可靠需改用 turn 转向脉冲并标定时长，README 已注明）；放球程序完成后的 yaw 复原以其进程启动时车体朝向为零位，编排链结束后车体保持掉头方向（符合预期，但整链实机效果待验证）；机器端三脚本 + 抓球脚本需先上传同目录。

## 2026-08-15｜放球程序加入视觉跟踪对齐（球模型暂代）

- 状态：改动完成
- 目标：按用户要求在放球程序的低趴车体之后加入与抓球一致的模型跟踪对齐（模型先用球的模型代替），跟踪对齐达标后再执行放球动作。
- 影响文件：`robot-src/catkin_ws/src/robot_dog_ball_release/scripts/ball_release.py`、`README.md`；`docs/lingo.md`（「机械臂关节」词条放球序列补视觉对齐段）、`.agents/skills/project-index/INDEX.md`（放球任务行说明更新）、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`ball_release.py` 从纯动作程序升级为 低趴 → 视觉跟踪对齐 → 放球 三段流程：`prepare_low_pose`（slow_trot + 低趴 z=10/p=15/y=-6）；`align_to_target` 复用抓球程序同款 letterbox/detect_ball 与对齐参数（3 帧确认、|dx|>25 转向 15°×0.74s、半径<28 前进 3×0.15s、达标输出 `action=align-complete`），默认模型 `best.onnx`（球模型暂代，README 注明后续换 `letters.onnx`）；`drop_ball` 在放球前重新低趴（对齐脉冲可能让车体恢复站姿，沿用抓球 grab 分支经验），随后抬后肢、安全伸臂、张爪、安全收臂、yaw 复原。
- 验证：本地 `py_compile` 通过；对齐阈值与脉冲参数与抓球程序逐项比对一致。
- 遗留风险：放球时爪内持球，球模型能否在低趴姿态下稳定检出并支撑对齐（对齐的是视野中目标还是爪内球）需实机确认；若球模型不可用，应换 `letters.onnx` 字母模型并对齐 A/B/C/D 目标；对齐循环无超时保护（与抓球程序一致），视觉始终不达标时程序不会进入放球。

## 2026-08-15｜simple_odom yaw 基准修复：建图起点朝向归零

- 状态：改动完成
- 目标：修复建图模式 RViz 里机器朝向斜约 26° 的问题——`simple_odom` 把 IMU 绝对磁力计朝向（实机当前 25.67°）当作 odom yaw 基准，而建图起点应为 yaw=0（机器正对地图 +X）。
- 影响文件：`robot-src/catkin_ws/src/robot_dog_navigation/scripts/simple_odom.py`（`fetch_imu_yaw` 首帧基准 `raw` → `self.init_yaw`）。
- 实施记录：修复后同步部署至实机容器（scp + docker cp，转 LF、chmod +x）；重启建图 launch（`local_master_ip:=192.168.137.193`）。
- 验证：`tf_echo odom base_link` RPY = [0, 0, 0]；建图链路（slam_gmapping、ydlidar_scan、laser_frame_tf、scan_circle_filter、simple_odom）全部注册到 WSL master，/map 有发布者，/scan_filtered 数据流正常。
- 遗留风险：`robot_dog_main.launch` 的 `local_master_ip` 默认值 192.168.137.232 已过时（WSL IP 由 DHCP 动态分配，现为 193），每次实机启动须手动传参，建议后续改为必填或自动探测；本次修复前已建的部分地图因重启已作废，需重新建图。

## 2026-08-15｜新建放球功能包 robot_dog_ball_release

- 状态：改动完成
- 目标：按用户要求写一个与抓球相反的放球功能包：机器狗夹球到达目标区域后，低趴并张开爪子把球放下。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_ball_release/`（package.xml、CMakeLists.txt、README.md、scripts/ball_release.py）；`docs/lingo.md`（高频索引「放球」行 + 「机械臂关节」词条放球序列）、`.agents/skills/project-index/INDEX.md`（功能索引放球任务行）、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：新包为与抓球包同构的标准 catkin 脚本包；`ball_release.py` 为纯动作程序（无相机/YOLO 依赖，球已在爪内），流程为抓球序列末端状态的逆操作：低趴(z=10、p=15、y=-6) → 抬后肢(31=26、41=25) → 安全伸臂持球(52=-50 → 53=90 → 52=-45) → 张爪放球(51=-65，默认等待 1s) → 安全收臂(53=0 → 52=0) → yaw 复原(y=0)；沿用抓球包的 `--enable-motion` 门禁与 `action=release-start/complete` 日志信号，参数表含 `--claw-open`、`--hold-after-open`。
- 验证：本地 `py_compile` 通过；package.xml XML 解析通过。
- 遗留风险：放球序列为抓球序列的对称逆推，尚未实机验证（张爪后球能否完全落下、-65 最大张开是否让球滚出目标区域待现场观察，可用 `--claw-open`/`--hold-after-open` 调整）；机器端部署路径 `/home/pi/oumax-xgo/ball_release.py` 尚未上传。

## 2026-08-15｜恢复 ABCD YOLO 数据集并完善批量标注分段参数

- 状态：改动完成
- 目标：恢复 `datasets/yolo/abcd/` 中已验证的 ABCD YOLO 数据集，并为自动标注脚本增加分段并行处理参数。
- 影响文件：`scripts/auto_label_abcd.py`；恢复 `datasets/yolo/abcd/` 的已提交数据集文件。
- 验证：已从 HEAD 恢复 `data.yaml`、train/val 数据、110 个字母标签及 3000 张原图；确认类别为 A/B/C/D、类别索引为 0/1/2/3。
- 遗留风险：工作区保留了本次 OCR 抽样产生的少量未跟踪临时 txt/图片文件，未纳入数据集。

每个改动单元的状态只能使用“进行中”或“改动完成”。

## 2026-08-15｜ABCD 字母 YOLO 数据集与训练产物全量入库

- 状态：改动完成
- 目标：按用户要求把地图字母检测的完整数据集与训练产物推送到仓库（不再“不入库”），与球模型 best.onnx 一样入库。
- 影响文件：`datasets/yolo/abcd/`（images 3000 张 jpg + 622 npy + EasyOCR 标注 txt、data.yaml、classes.txt）、`runs/abcd/`（train/train2 训练产物含 best.onnx/best.pt/last.pt 与曲线图）、根目录预训练权重 `yolo26n.pt`、`yolov8n.pt`；`.gitignore` 白名单调整（abcd/、runs/abcd/、根目录 yolo*.pt）。
- 验证：git 暂存区确认新增约 480MB 文件全部纳入；分两个 commit 推送 origin/main（先小文件后图片，降低大体积传输中断风险）。
- 遗留风险：仓库体积增大约 480MB，clone/拉取变慢；后续重新采集或训练产物仍会被 `/runs/*`、`/datasets/yolo/*` 默认忽略，只有白名单路径入库。

## 2026-08-15｜地图 A/B/C/D 字母 YOLO 模型：自动标注训练并部署

- 状态：改动完成
- 目标：用户实拍 3000 张地图照片后，自动完成标注、训练 YOLO 字母检测模型并部署到机器狗。
- 影响文件：新增 `scripts/auto_label_abcd.py`、`tmp/verify_letters.py`（机器端验证脚本）；机器 `/home/pi/ros_ws/models/letters.onnx`；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：EasyOCR 全量扫描 3000 张，仅 622 张（20.7%）拍到 A/B/C/D 字母（0.2s 连拍+狗走动导致大量空帧），自动生成 YOLO 标注（allowlist=ABCD、conf≥0.5、归一化中心坐标）；无标注的 2378 张移入 `images/unlabeled/`；9:1 切分（train 559/val 63）；yolov8n 训练 150 epochs（早停于 136，batch=16 曾 CUDA OOM，改 8+disk cache 后通过）；mAP50=0.877（A=0.968 B=0.993 C=0.735 D=0.810）；导出 ONNX（640, opset 12）部署为 `/home/pi/ros_ws/models/letters.onnx`（与球的 best.onnx 并存）。
- 验证：机器端 xgovenv 加载 onnx 成功（输入 1x3x640x640，输出 1x8x8400），Picamera2 实拍推理 0.2s/帧；验证时相机流服务（8090）需先停，验证后已恢复 active。
- 遗留风险：自动标注质量受 EasyOCR 限制，C 类 mAP 偏低（0.735）；622 张中 B 类样本最多（313），类别不均衡；采集时相机流仅 640x360，远处字母分辨率不足。建议后续人工抽查标注、针对性补拍 C/D 与远景样本再微调。

## 2026-08-14｜地图 A/B/C/D 字母 YOLO 数据采集与训练流水线

- 状态：改动完成
- 目标：用机器狗相机实拍比赛地图，建立 A/B/C/D 字母四类 YOLO 数据集，并打通采集→标注→切分→训练→导出 ONNX→部署机器端的完整流程。
- 影响文件：新增 `scripts/capture_map_photos.py`、`scripts/split_yolo_dataset.py`、`scripts/train_abcd_yolo.py`、`docs/map-abcd-yolo-workflow.md`；`datasets/yolo/abcd/`（data.yaml、classes.txt，不入库）；`.agents/skills/project-index/INDEX.md`；`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：机器端启用 `oumax-camera.service`（Picamera2 MJPEG 流，端口 8090，640x360），本机脚本直接解析 multipart 流抓帧，默认每秒 1 张存至 `datasets/yolo/abcd/images/`；训练脚本用 ultralytics（yolov8n）在 RTX 4050 上训练并导出 ONNX（imgsz=640, opset=12），部署目标 `/home/pi/ros_ws/models/letters.onnx`。
- 验证：`--probe` 单帧实测抓取成功（640x360 JPEG）；CUDA 可用（torch 2.11.0+cu126）；采集进行中。
- 遗留风险：训练效果依赖标注质量与样本覆盖（远近/斜视角度）；流分辨率 640x360 对远处字母可能偏小，若识别率不足需提高流分辨率或贴近拍摄。

## 2026-08-14｜抓球程序入 catkin：新建 robot_dog_ball_grab 包

- 状态：改动完成
- 目标：按用户约定（catkin_ws 为本次任务代码存放地、原厂程序不删），把机器端 YOLO 抓球程序 `ball_yolo_grab.py` 归档到 `robot-src/catkin_ws/src/` 下的独立 ROS 功能包。
- 影响文件：新增 `robot-src/catkin_ws/src/robot_dog_ball_grab/`（package.xml、CMakeLists.txt、README.md、scripts/ball_yolo_grab.py）；`docs/lingo.md`（新增「放 catkin」词条）、`.agents/skills/project-index/INDEX.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`ball_yolo_grab.py` 为复制归档（SHA-256 与 `robot-src/host-services/oumax-xgo/ball_yolo_grab.py` 原件一致），原厂区文件保留不动；新包为标准 catkin 脚本包（catkin_install_python 安装脚本），README 注明两处副本同步关系与机器端部署路径 `/home/pi/oumax-xgo/`。
- 验证：副本哈希一致；本地 `py_compile` 通过。
- 遗留风险：两处副本后续修改需保持同步；机器端实际运行仍以 `/home/pi/oumax-xgo/ball_yolo_grab.py` 为准。

## 2026-08-14｜lidar_loc 增加场地 ROI 空间过滤

- 状态：改动完成
- 目标：NAV 初始定位时，只让场地区域（裁剪地图范围）内的激光点参与 scan matching，过滤场地外观众、走廊等动态环境对定位匹配的干扰。
- 影响文件：`robot-src/catkin_ws/src/jie_ware/src/lidar_loc.cpp`、`robot-src/catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`robot-src/catkin_ws/src/robot_dog_navigation/launch/offline_navigation.launch`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`lidar_loc` 新增 `~use_map_roi_filter` 参数（默认 false，保持第三方包原行为）；开启后每个扫描点按当前位姿估计（lidar_x/lidar_y/lidar_yaw）变换到裁剪地图像素坐标，超出 `map_cropped` 范围的点不进入 `scan_points`；变换公式与匹配用 transform_points 完全一致，用布尔标志而非 continue（避免跳过 angle 递增）。两个项目 launch（实机主流程与离线导航）显式开启该参数。
- 验证：git diff 静态复核（过滤公式与匹配公式一致性、边界判定、angle 递增不受影响、map 未到达时行为同原版）；已部署至机器狗（192.168.137.157）：旧版备份至 `/home/pi/ros_ws/backups/deploy-20260814-lidar-loc-roi-filter/`，scp 上传后修复 CRLF，`ros-noetic` 容器内 `catkin_make --pkg jie_ware` 编译成功，`lidar_loc` 可执行已更新（Aug 14 07:34）；`robot_dog_main.launch --nodes` 与 `offline_navigation.launch --nodes` 静态解析均通过。未重启实机导航进程（下次 bringup 生效）。
- 遗留风险：过滤依赖 initialpose 附近的位姿估计，若初始位姿错误过大，可能滤掉场内点导致匹配退化；实机需观察定位收敛效果与日志中过滤开启提示。

## 2026-08-14｜YOLO 抓球小臂前伸到位改为 -45°

- 状态：改动完成
- 目标：把夹球序列的小臂前伸到位值从 `-58°` 改为 `-45°`，减少前伸量；过渡位 `-50°` 保持不变。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、`docs/lingo.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`grab` 机械臂序列 `(52, -58, 1.2)` 改为 `(52, -45, 1.2)`；词典「机械臂关节」与「低趴」词条的前伸到位值同步为 `52=-45°`。
- 验证：本地 Python 编译通过；尚未部署机器端。
- 遗留风险：前伸量减少会影响夹球距离与落点，实机需重新观察球能否落入爪内；机器端 `ball_green.py` 未同步修改（如仍在使用需一并更新）。

## 2026-08-14｜YOLO 抓球完成后车体 yaw 补偿复原

- 状态：改动完成
- 目标：夹球序列完成后把车体 yaw 从抓取补偿的 `-6°` 复原为 `0°`，避免程序退出后车体保持向右偏斜。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、`docs/lingo.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`grab` 的机械臂序列（含收臂）完成后、输出 `action=grab-complete` 前增加 `dog.attitude("y", 0)` 并等待 1 秒。
- 验证：本地 Python 编译通过；尚未部署机器端。
- 遗留风险：复原后车体朝向恢复为初始朝向，下次运行程序会重新下发 `y=-6`，不影响抓取；实机需现场确认复原动作平滑、无位置偏移。

## 2026-08-14｜YOLO 抓取前爪子最大张开

- 状态：改动完成
- 目标：在最终抓取准备时将 51 号爪子张开至实际下限 `-65°`，为球进入夹爪留出最大开口。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、`docs/lingo.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`grab` 的准备序列首项从 `51=-30°` 改为 `51=-65°`；抓球词典同步为最大张开、`53=90°`、`52=-58°` 的当前实机序列。
- 验证：本地 Python 编译通过；机器 SSH 当前超时，尚未部署。
- 遗留风险：更大开口会改变球进入夹爪的横向容差，须结合实际夹取结果复核。

## 2026-08-14｜YOLO 抓球车体 yaw -6° 补偿

- 状态：改动完成
- 目标：在低趴接近和最终抓取阶段保持实机确认有效的车体 `yaw=-6°`，补偿机械臂左偏。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：在 `prepare_approach_pose` 与 `grab` 的低趴命令后均增加 `dog.attitude("y", -6)`。
- 验证：本地和机器端 Python 编译通过，更新版本已部署并以 PID 6999 启动。
- 遗留风险：补偿角度按当前机械臂零位与场地标定，机械安装或车体姿态变化后需重测。

## 2026-08-14｜YOLO 前进脉冲增至 0.15 秒

- 状态：改动完成
- 目标：增加每次小步前进距离，解决 0.10 秒脉冲接近不足的问题。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`dog.move_x(3)` 的脉冲等待从 `0.10s` 改为 `0.15s`；更新版本已部署并以 PID 5121 启动。
- 验证：本地与机器端 Python 编译通过，后台抓球进程存活。
- 遗留风险：目标框尺寸不增长时仍可能需要多次脉冲才能到达抓取半径。

## 2026-08-14｜YOLO 后肢同步抬高

- 状态：改动完成
- 目标：最终抓取前同步抬高两条后肢，避免先抬单侧造成机身横移。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`、`docs/lingo.md`。
- 实施记录：将依次发送且相隔 0.5 秒的 `31=26°`、`41=25°` 改为紧邻的 `dog.motor([31, 41], [26, 25])` 调用。
- 验证：本地 Python 编译通过；后续从机器实际 `xgolib` 源码确认该列表接口会拆为两个单舵机串行帧，不能视为原子同步。
- 遗留风险：该版本只消除了中间的显式等待，无法保证物理同步；若横移仍影响抓取，需改用固件支持的批量协议或重新设计抬升方式。

## 2026-08-14｜YOLO 低趴接近与末端后肢抬高

- 状态：改动完成
- 目标：让程序以低趴姿态接近球，抵达抓取阈值后才抬高后肢并夹取。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`、`docs/lingo.md`。
- 实施记录：新增 `prepare_approach_pose`：仅在程序开始时设 `slow_trot`，随后发送 `z=10`、`p=15` 低趴，不设置后肢 31/41。转向和前进分支不再重复设置步态；到抓取分支后才设置 `31=26°、41=25°` 并执行机械臂序列。
- 验证：本地 Python 编译通过。
- 遗留风险：机器当前断电，尚未部署和实机确认步态设定后低趴能否在接近期间持续保持。

## 2026-08-14｜YOLO 抓取前低趴与前进脉冲调整

- 状态：改动完成
- 目标：只在最终抓取前进入低趴，避免接近阶段重复切换姿态；略微增加每次小步前进时长。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`。
- 实施记录：移除程序启动时的 `prepare_pose` 调用与定义，低趴只保留在 `grab` 分支；前进脉冲由 `0.08s` 调为 `0.10s`。新版本已部署。
- 验证：本地与机器端 Python 编译通过；实机运行确认接近阶段持续使用行走步态，未在程序起始时下发低趴指令。
- 遗留风险：当前球框半径可能在前进中不增长，造成持续接近而无法触发最终抓取；该视觉距离问题仍需单独标定。

## 2026-08-14｜YOLO 抓取前姿态重建

- 状态：改动完成
- 目标：在前进行走导致车体恢复站姿后，于合爪前重建已验证的低趴、后肢抬高和机械臂抓取准备姿态。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`。
- 实施记录：`grab` 在 `action=grab-start` 后先停步，重发 `z=10`、`p=15`、`31=26°`、`41=25°`；由于车体姿态会复位机械臂，再按安全顺序下发 `51=-30° → 52=-50° → 53=90° → 52=-58°`，最后才闭爪和收臂。
- 验证：本地与机器端 Python 编译通过，更新版本已部署至机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`。
- 遗留风险：尚待下一次实机完整流程确认球能落在爪内并被实际夹住。

## 2026-08-14｜YOLO 接近停止保护移除

- 状态：改动完成
- 目标：移除框半径回落和累计前进步数导致的提前退出，让已识别到的球持续进入抓取半径。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`。
- 实施记录：删除 `expected_radius`/`action=stop-no-approach` 与 `max_forward_pulses`/`action=stop-forward-limit` 分支；保留“检测到球、水平居中且框半径达到 28px 后抓取”的主流程。
- 验证：本地和机器端 Python 编译通过；后台实机实例连续执行前进脉冲，日志最终依次输出 `action=grab-start`、`action=grab-complete` 并退出。
- 遗留风险：`grab-complete` 仅证明机械臂序列完成，是否实际夹住球仍须现场观察。前进时 `slow_trot` 会接管车体并恢复行走站姿，低趴不能在行走阶段保持。

## 2026-08-14｜YOLO 抓球起始姿态对齐

- 状态：改动完成
- 目标：让完整 YOLO 抓球流程以现场确认可夹球的低趴、后肢抬高姿态开始，避免厂商 `z=75` 起始命令覆盖该姿态。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`prepare_pose` 改为 `z=10`、`p=15` 后再设 `31=26°、41=25°`，且不提前发送机械臂指令；抓取序列的大臂目标从会被运行库钳制的 `120°` 改为实际可达的 `90°`。远端旧版已备份为 `/home/pi/oumax-xgo/ball_yolo_grab.py.20260814-pre-low-pose.bak`，新版本已部署。
- 验证：本地与机器端均通过 Python 编译；实机完整流程检测到 green（置信度 0.91），执行一次 `action=forward-step`，随后因检测框半径从 25.2px 回落到 20.4px 触发 `action=stop-no-approach` 并正常停止。
- 遗留风险：本次未触发夹取；YOLO 框半径在移动后的波动仍会触发接近保护，需根据现场观察调整距离判断后再测。

## 2026-08-13｜YOLO 抓球完成信号

- 状态：改动完成
- 目标：为实机抓球流程输出可由持续监控判定的抓取开始与完成日志。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`grab` 函数在开始关节序列前输出 `action=grab-start`，完成最后一个关节收回后输出 `action=grab-complete`；已部署并重新启动真实动作实例。
- 验证：机器端 Python 编译通过，新实例 PID 39105 存活且相机初始化成功；Codex 已创建每分钟一次的抓球状态监控。
- 遗留风险：`action=grab-complete` 表示序列执行完毕，不等于爪内实际持球，仍须现场目视确认。

## 2026-08-13｜YOLO 接近距离误标定保护

- 状态：改动完成
- 目标：阻止 YOLO 抓球因错误套用厂商圆检测距离公式而连续前进至丢失目标。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`。
- 实施记录：移除 `54.82 - YOLO 框半径` 的虚假距离控制，改用可标定的 `target_radius=28px`；前进固定为速度 3、0.08 秒小步，每次运行最多 6 步，单步后若框半径明显缩小即停止。一次实测中发现 1px 增长要求对 0.08 秒小步过严，调整为仅在半径明显缩小时中止。
- 验证：机器端 Python 编译通过。PID 39670 实测连续完成 6 个 `action=forward-step` 后输出 `action=stop-forward-limit` 并退出；框半径仅在 14.9–16.5px 间波动，未出现旧版持续推进至丢失目标。
- 遗留风险：当前模型框半径尚未在“可抓取距离”做实机标定，28px 只是保守初值；自动接近将每次最多走 6 小步，达到上限后需根据现场位置重新启动或完成标定。

## 2026-08-13｜YOLO 抓球转向参数实机标定

- 状态：改动完成
- 目标：以实机确认有效的转向强度与脉冲时长更新 YOLO 抓球对准动作。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：直接复现厂商转向流程后确认 `slow_trot + turn(-8) × 0.74s` 无动作，而仅提高到 `turn(-15) × 0.74s` 后现场确认可转；YOLO 程序据此把转向脉冲从 0.15s 改为 0.74s，并增加动作日志。
- 验证：机器端 Python 编译通过，真实动作实例 PID 65690 已启动；日志显示模型稳定检测 green（0.89–0.92）并连续执行 `action=forward-fast`，距离估算从 41.1 下降至 35.9，证明对准后的前进行为已实际进入。
- 遗留风险：转向方向尚需在球明显偏离中心时再次观察；距离估算与抓取阈值仍未做物理距离标定。

## 2026-08-13｜YOLO 抓球改为类别无关目标选择

- 状态：改动完成
- 目标：让独立抓球程序完全按 YOLO 输出选择球，取消固定绿色类别和 Picamera RGB 通道的二次交换。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：检测器改为在 YOLO 的所有球类分数中选择最高置信目标，再进行 NMS；Picamera2 `RGB888` 图像改为不再执行 `swapRB`，直接按 RGB 输入模型。日志会输出模型选择的 red/blue/green 类别，不包含 HSV 或颜色阈值判断。
- 验证：机器端 Python 编译通过；单帧无动作实测模型选中 green（置信度 0.89、距离估算 38.9、水平偏差 36.5）；随后真实动作模式进程 PID 20322 已启动。
- 遗留风险：距离仍由 YOLO 框尺寸套用原厂圆半径公式估算，尚未实物标定；若视野内有多个球，当前按最高置信度选择而非指定颜色。

## 2026-08-13｜独立 YOLO 抓球程序

- 状态：改动完成
- 目标：以项目训练的 `best.onnx` 替代厂商 HSV/圆检测，重写为不依赖 Catkin 的机器端抓球程序。
- 影响文件：`robot-src/host-services/oumax-xgo/ball_yolo_grab.py`、机器 `/home/pi/oumax-xgo/ball_yolo_grab.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：新增独立脚本，直接使用厂商 `xgovenv`、Picamera2、XGO 控制库与机器 `/home/pi/ros_ws/models/best.onnx`；YOLO 仅选择训练类别 green（索引 2），连续 3 帧确认后才发出低速转向/前进脉冲，未检测到球时保持原地；抓取动作沿用已实机标定的 51/52/53 关节序列。
- 验证：已上传至机器并用厂商解释器完成 Python 编译；无动作单帧实测成功启动相机、加载模型并输出 `YOLO no green ball; holding position`，未发送运动命令。
- 遗留风险：模型的绿色类别索引按既有训练顺序 red/blue/green 假定；仍需在放球的实景中确认检测置信度与以框半径估算的抓取距离，再开启 `--enable-motion`。

## 2026-08-13｜厂商抓球 demo 前进速度降档

- 状态：改动完成
- 目标：降低厂商 `ball_green.py` 识别对准阶段的快速前进与微调前进速度，避免实机出现大幅前冲。
- 影响文件：机器 `/home/pi/RaspberryPi-CM5/robots/Mini3W_W/demos/ball_green.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：两处机型分支的 `x_speed_far` 均从 16 降为 6，`x_speed_slow` 均从 8 降为 3；修改前停止旧实例，随后用厂商 `xgovenv` 重启原厂 `ball_green.py`。
- 验证：远端源码四项速度常量均已读回为 6/3；新进程 PID 130998 持续运行并完成相机初始化。
- 遗留风险：原厂“绿色 HSV 阈值 + Hough 圆”不是语义模型，绿色圆形背景仍可能被误当作球；本次仅调低动作速度，未改识别算法。

## 2026-08-13｜厂商抓球 demo（ball.py）实机调试：arm_polar 不可靠，改关节直控

- 状态：进行中
- 目标：在机器（192.168.137.157）上运行厂商示例 `~/RaspberryPi-CM5/robots/Mini3W_W/demos/ball.py` 抓球，修复机械臂不动/伸不到位问题。
- 影响文件：机器 `~/RaspberryPi-CM5/robots/Mini3W_W/demos/ball_green.py`（由 ball.py 复制的绿球版，默认 color=green/mode=2）、`docs/lingo.md`（新增"机械臂关节"词条）。
- 实施记录：
  - 运行前置：停 `oumax-manual.service`（占 /dev/ttyAMA0）与 `oumax-camera.service`（占 picamera2）后 setsid 启动；备份脚本经 `arm_mode(1)` 验证有效。
  - 根因 1：ball.py 的 catch_arm/down_arm 未调用 `arm_mode(1)`，固件忽略 arm_polar，仅 claw 生效（现象：只有爪子开合）。加 `arm_mode(1)` 后臂能动。
  - 根因 2：`arm_polar(theta,r)` 极坐标命令在固件 M-7.0.0b8 上不可靠——命令帧（0x76/0x77）发出但固件经常不执行（多轮抓包确认发送正常、多次实测臂不动或只执行第一帧）。废弃 arm_polar，改用 `dog.motor(id, angle)` 关节直控。
  - 关节标定（现场逐步实测）：51=爪子（+收紧/-张开）；52=小臂（**负=前伸**，正=后收会扫摄像头）；53=大臂（+前抬/-后倒，+120 钳到上限）。收回顺序必须先大臂后小臂。
  - 抓球序列（当前版）：51:-30 张爪 → 52:-50 小臂前伸 → 53:+120 大臂前抬 → 52:-65 小臂前伸到位 → 51:+40 闭合 → 53:0 → 52:0。
- 验证：`arm_mode(1)` 修复后臂动；关节直控每步均有动作；摄像头曾两次被臂碰掉（+40 前抬、小臂后收路径），已装回；最终抓球距离仍在调（x_distance/小臂前伸量）。
- 遗留风险：52/53 方向结论是现场观察标定，不同固件/机型可能不同；抓球姿态参数未收敛（距离不够）；`x_distance.txt`（默认 22）控制抓取触发距离；测试后需恢复 oumax-manual/oumax-camera 服务（当前 inactive）。

## 2026-08-11｜四轮通道顺序校正

- 状态：进行中
- 目标：按实机观察修正轮控数据通道顺序，使左/右转分别让物理左侧和右侧的两个轮子同组反向运行。
- 影响文件：`robot-src/host-services/oumax-xgo/manual_control_server.py`、`docs/ai-records/{CHANGE_LOG,FAILED_APPROACHES}.md`。
- 实施记录：待更新。
- 验证：待更新。
- 遗留风险：待更新。

## 2026-08-11｜四动力轮差速转向映射

- 状态：改动完成
- 目标：按实机确认的四个主动轮实现轮式左/右转：左转左侧两轮向后、右侧两轮向前；右转相反。
- 影响文件：`robot-src/host-services/oumax-xgo/manual_control_server.py`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`gamepad_wheel_speeds` 改为四轮差速混合，输出顺序为左前、右前、左后、右后；正 yaw 输出 `[-,+,-,+]`（左转），负 yaw 输出 `[+,-,+,-]`（右转），同时移除右侧为被动轮的错误假设。已备份并部署到机器 `/home/pi/oumax-xgo/manual_control_server.py`，备份为 `/home/pi/oumax-xgo/manual_control_server.py.20260811-wheel4-turn.bak`。
- 验证：本地及机器端 Python 编译通过；映射断言确认左转 `[-1.15,1.15,-1.15,1.15]`、右转 `[1.15,-1.15,1.15,-1.15]`、直行四轮同向；部署后原厂主服务为 active、手控服务为 inactive，因此未发送新的运动指令。
- 遗留风险：轮式转向的正负方向已按用户定义映射，首次在实际地面使用仍应短时观察机身朝向；手控服务将在下一次控制权交接后加载新代码。

## 2026-08-09｜实机部署：jie_ware 定位 + 键盘姿态控制

- 状态：改动完成
- 目标：把 jie_ware 激光定位集成（lidar_loc/initial_pose_publisher/scan filter 三 launch 改动）与键盘姿态控制（pose_keyboard_teleop + kind=motor 接口）传输到机器狗（192.168.137.157）部署并编译。
- 影响文件：机器 `/home/pi/ros_ws/src/{jie_ware,robot_dog_navigation,robot_dog_bringup,robot_dog_teleop}/`、`/home/pi/oumax-xgo/manual_control_server.py`、`/usr/local/sbin/raicom-launch-pose-keyboard`；仓库 `docs/ai-records/CHANGE_LOG.md`。备份：机器 `/home/pi/ros_ws/backups/deploy-20260809-jie-ware-pose/`。
- 实施记录：scp 上传 jie_ware 包、navigation/bringup/teleop 差异文件与 manual_control_server.py；机器上 `sed -i 's/\r$//'` 修复 Windows scp 引入的 CRLF 行尾（install_host_handover.sh、launch_pose_keyboard_teleop.sh）；`sudo bash install_host_handover.sh --install-only` 注册 `raicom-launch-pose-keyboard`；容器内 `catkin_make` 编译成功（jie_ware 三节点 + 脚本 wrapper）。顺带修复两个机器侧历史误传：工作空间根 `/home/pi/ros_ws/CMakeLists.txt`（2026-08-07 误放的 catkin 顶层模板，挡住 catkin_make，移至 backups/CMakeLists.txt.stray-20260807-root）与 WSL 专用包 `ball_spotter/`（无 CMakeLists.txt 导致 catkin 配置失败，移至 backups/ball_spotter-stray-wsl-pkg-20260809）。
- 验证：devel 空间 `jie_ware/{lidar_loc,costmap_cleaner,lidar_filter_node}` 可执行存在、`initial_pose_publisher.py` 已安装；`roslaunch robot_dog_bringup robot_dog_main.launch --nodes` 解析出 map_server/lidar_loc/initial_pose_publisher/move_base；`pose_keyboard_teleop.launch enable_motion:=false --nodes` 解析出 /robot_dog_pose_keyboard_teleop；两个新 Python 脚本容器内 py_compile 通过；宿主机 manual_control_server.py py_compile 通过且 `kind=motor`/`MOTOR_RANGES` 就位。未切换串口所有权（oumax-manual.service 保持 inactive，raicom-original-main.service 维持 active），新版 manual_control_server 将在下次 launch_pose_keyboard_teleop.sh acquire 时生效。
- 遗留风险：姿态键盘首次实机使用须先按 `m` 回中（本地跟踪角可能与舵机实际角漂移），并在站稳、净空 1 m 场地以最小细步（w/s 1°）逐关节验证方向；`kind=motor` 参数校验已静态验证，实际动关节行为待实机；lidar_loc 实机首次导航需确认 initialpose 落点与实际位置偏差在收敛域内（±1 栅格/±1° 迭代），不匹配时用 rviz 2D Pose Estimate 修正后再发目标点；lidar_loc 不可单独重启（会卡地图原点）。

## 2026-08-09｜定点导航接入激光定位（jie_ware lidar_loc）与局部代价地图

- 状态：改动完成
- 目标：把 https://github.com/6-robot/jie_ware 的激光扫描匹配定位节点 `lidar_loc` 集成进定点导航任务（替代静态 map→odom TF），并让任务/本地 rviz 的局部代价地图具备 `/scan_filtered` 数据源与可视化。
- 影响文件：`catkin_ws/src/jie_ware/`（新增第三方包：`src/{lidar_loc,costmap_cleaner,lidar_filter_node}.cpp`、`CMakeLists.txt`、`package.xml`、`LICENSE`、`launch/`）、`catkin_ws/src/robot_dog_navigation/scripts/initial_pose_publisher.py`（新增）、`catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`catkin_ws/src/robot_dog_bringup/package.xml`、`catkin_ws/src/robot_dog_navigation/{launch/offline_navigation.launch,launch/robot_visualization.launch,CMakeLists.txt,package.xml}`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`lidar_loc` 订阅 `/map` 与 `/scan_filtered`，把激光点投影到地图障碍物渐变图做逐帧 15 变换（±1 栅格 × ±1°）迭代匹配，解出 map 系位姿并结合 `simple_odom` 的 odom→base 里程计发布 `map→odom` TF（30Hz）；收到 `/initialpose` 约 30 帧后自动调 `move_base/clear_costmaps`。导航模式用 `lidar_loc`（laser_topic=/scan_filtered）替换原静态 map_to_odom 并移除组外静态节点（顺带消除建图模式 gmapping 与静态 map_to_odom 双发布者冲突隐患）；新增 `initial_pose_publisher.py` 在 `/map` 到达后延时 1s 重复发布 5 次 `/initialpose`（init_x/init_y 默认 -0.70/1.00），覆盖 lidar_loc 收到地图时重置地图原点的竞争；本地 `offline_navigation.launch` 新增 `scan_circle_filter`（/scan→/scan_filtered，参数与实机一致）使局部代价地图有数据、rviz 的 Local Costmap 显示生效，并新增 `use_lidar_loc` arg（默认 false，true 时验证 lidar_loc 节点/TF 链路——mock 房间数据与 RICAM 地图不匹配，估计会漂移属预期）；`robot_visualization.launch` 同步加 filter 并把云点改订阅 `/scan_filtered`；`robot_dog_bringup/package.xml` 补齐运行依赖（gmapping/map_server/move_base/jie_ware/cym_planner 等）。
- 验证：jie_ware 三节点在 WSL Noetic 编译链接成功（需 cv_bridge/OpenCV，环境自带）；三个 launch 与两个 package.xml 均通过 XML 解析；离线默认模式端到端实测：`/scan_filtered` 有 360 点数据、`/move_base/local_costmap/costmap` 100×100@0.01 滚动窗口持续更新、`scan_circle_filter/move_base` 在线；`use_lidar_loc:=true` 实测：`lidar_loc/initial_pose_publisher` 在线，`tf map→odom` 持续发布且匹配结果随 mock 数据收敛（yaw ≈ -24°），`/initialpose` 发布窗口正常。
- 遗留风险：lidar_loc 收到 /map 会重置估计到地图原点，单独重启该节点会卡原点——须与 initial_pose_publisher 同启（已在 launch 注释与文档写明）；lidar_loc 匹配算法只在估计位姿附近 ±1 栅格/±1° 搜索，初始位姿误差需较小，实机开机后需确认 initialpose 落点与实际位置偏差在收敛域内；jie_ware 为 GPL-2.0 许可，与仓库其余 BSD-3-Clause 包隔离管理（进程间 topic 通信无链接传染）；实机导航闭环（lidar_loc 收敛后 2D Nav Goal 全程）待机器开机验证。

## 2026-08-08｜键盘姿态控制：j1-j15 关节步进调姿与姿态记录

- 状态：改动完成
- 目标：新增键盘程序控制车体姿态（机械爪、前腿、后腿共 15 个关节），终端实时显示当前姿态（如 `j1 1, j2 1`），支持一键记录姿态到文件。
- 影响文件：`catkin_ws/src/robot_dog_teleop/scripts/pose_keyboard_teleop.py`（新增）、`catkin_ws/src/robot_dog_teleop/launch/pose_keyboard_teleop.launch`（新增）、`catkin_ws/src/robot_dog_teleop/host/launch_pose_keyboard_teleop.sh`（新增）、`host-services/oumax-xgo/manual_control_server.py`（新增 `kind=motor` 单关节接口）、`catkin_ws/src/robot_dog_teleop/{CMakeLists.txt,host/install_host_handover.sh,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：关节映射 j1–j12 为四腿（j1/j2/j3 左前、j4/j5/j6 右前、j7/j8/j9 右后、j10/j11/j12 左后，分别为小腿/大腿/髋，舵机 id 11–43），j13 夹爪（51）、j14 小臂（52）、j15 大臂（53），范围按原厂 mcp 文档（小腿 [-73,57]、大腿 [-66,93]、髋 [-31,31]、爪 [-65,65]、小臂 [-115,70]、大臂 [-85,100]），默认姿态 0/0/-85/70；`manual_control_server.py` 新增 `MOTOR_RANGES` 表 + `handle_motor`（id/角度类型与范围校验、中文错误、`bot.motor(id, angle)`）+ dispatch 分支；`pose_keyboard_teleop.py` 沿用 u→y 双确认、`enable_motion:=true` 门禁、空格/x 锁定、Ctrl-C 双次退出模式，`[`/`]` 循环选关节、`w`/`s` 细步（默认 1°）、`q`/`e` 粗步（默认 10°）、`m` 回中、`r` 记录姿态（UTF-8 追加、失败仅报错）、`h` 帮助；终端底部 3 行 ANSI 实时重绘（状态行 + 姿态两行，每行 ≤80 字符，80 列终端不换行），姿态行格式 `j1 0, j2 0, ...` 便于抄录；未武装时按键只更新本地跟踪值不发送；`install_host_handover.sh` 注册 `raicom-launch-pose-keyboard`。
- 验证：py_compile 通过；launch XML 解析通过；两个 host 脚本在 WSL `bash -n` 通过；git 空白检查通过；独立测试脚本（mock `bot.motor`/rospy/termios）40+ 断言全部通过（15 关节范围端点 57/-73/93/-66/31/-31/65/-65/70/-115/100/-85 接受、越界拒绝、未知/缺失/非数字 id 拒绝、关节表名/id 映射、默认姿态行、钳制与边界 no-op、关节循环选择、记录文件内容、回中）；全部改动文件 LF 行尾。
- 遗留风险：本地跟踪角度与舵机真实角度可能漂移（若曾被其他程序移动），首次使用须先按 `m` 回中；单关节步进可能改变腿的姿态稳定性，须在站稳、净空 1 m 场地以最小细步逐关节验证方向；`kind=motor` 与 `raicom-launch-pose-keyboard` 需部署后实机验证；52/53 大臂舵机默认值按原厂文档，实机回中后需目视核对。

## 2026-08-08｜gmapping 键盘建图与实机地图切换

- 状态：改动完成
- 目标：在实机上用键盘控制机器狗行走，通过 gmapping 实时建图并保存地图，供导航模式加载使用；修复建图不出图与里程计位移不更新的问题。
- 影响文件：`catkin_ws/src/robot_dog_navigation/scripts/{laser_frame_tf.py,simple_odom.py,scan_circle_filter.py}`、`catkin_ws/src/robot_dog_navigation/maps/ricam_arena_mapped.{pgm,yaml}`（新增）、`catkin_ws/src/robot_dog_teleop/scripts/mapping_keyboard_teleop.py`（新增）、`catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`、`docs/local-rviz-navigation-quickstart.md`。
- 实施记录：容器安装 `ros-noetic-slam-gmapping`（可执行文件在 `gmapping` 包而非 `slam_gmapping` 空 wrapper，launch 必须 `pkg="gmapping" type="slam_gmapping"`）；`robot_dog_main.launch` 新增 `enable_mapping` arg（true 时停 map_server/move_base 并起 slam_gmapping，false 时原导航模式）；新增 `laser_frame_tf.py` 把 base_link→laser_frame 静态 TF 改为动态发布（gmapping 用 tf1 不读 /tf_static，这是实机“只有首图”的决定性根因）；新增 `mapping_keyboard_teleop.py` 键盘建图脚本（w/s 前后、a/d 转向、按住持续 10Hz 发布 /cmd_vel，走桥接→simple_odom 保证建图 odom 正确）；`simple_odom` 加固（yaw 毛刺限幅 0.4rad、静止冻结、位移限幅）并把初始位姿改为 launch 的 init_x/init_y arg（建图模式 0,0 对齐机器起点）；修复 `simple_odom` d_max 位移限幅 0.02→0.10（foot 步速 0.3~0.8m/s 时原限幅每帧清零导致 rviz 车体只转不走）。
- 验证：实机键盘建图成功，保存 `ricam_arena_mapped.pgm/yaml`（1408×1344 @ 0.02m/pix，origin [-13.66,-14.06]）；切回导航模式 `/map` 加载新建图、move_base 恢复、无 transform 超时；gmapping 本地对照实验全链路跑通（动态 TF + 0.2s scan 时间戳偏移后 /map 持续更新）；d_max 修复仅本地 py_compile 通过，实机验证待下次开机。
- 遗留风险：d_max=0.10 修复尚未实机验证（机器关机）；simple_odom 无真实里程计，重启后需对齐起点；建图地图原点按建图起点 (0,0) 对齐，导航模式下机器实际起点需用 init_x/init_y 与地图匹配；AMCL 闭环定位未实施（待装 ros-noetic-amcl）。

## 2026-08-08｜主流程集成：球检测、里程计、运动桥接与雷达滤波

- 状态：改动完成
- 目标：把 2D Nav Goal 选点、cym_planner 导航、OUMAX 运动控制、球检测画面与雷达滤波整合为本地 rviz + 实机主流程的端到端闭环。
- 影响文件：`catkin_ws/src/robot_dog_navigation/scripts/{simple_odom.py,scan_circle_filter.py}`、`catkin_ws/src/robot_dog_teleop/scripts/oumax_cmd_vel_bridge.py`、`catkin_ws/src/robot_dog_bringup/launch/robot_dog_main.launch`、`wsl-simulation/src/ball_spotter/{scripts/ball_detector_node.py,launch/local_control.launch}`、`wsl-simulation/src/ricam_dataset_capture/scripts/mjpeg_bridge.py`、`host-services/oumax-xgo/manual_control_server.py`（新增 `/imu` 只读接口、Timer 看门狗运动语义、wheel4 差速混合）、`catkin_ws/src/cym_planner/config/cym_planner_params.json`、`wsl-simulation/start_local_control.sh`、WSL 侧 `/root/fix_shm.sh` 与 `/etc/wsl.conf`。
- 实施记录：本地球检测节点（YOLO 画框发布 `/ball_detector/image`）；`/cmd_vel`→OUMAX HTTP 桥接（yaw 优先、watchdog 急停、步进线性映射避开固件死区）；`simple_odom` 里程计（cmd_vel 积分 + IMU yaw 融合，替代原静态 odom→base_link TF）；雷达滤波（前方机械臂扇形 ±20°/1.0m 后改为圆心 (0,0) 半径 0.45m 全向滤除站立姿态自身遮挡）；OUMAX 手控服务增加 `/imu` 接口与 Timer 看门狗（turn/move_x 立即返回，runtime 后自动停）；WSLg 窗口修复（boot.command 预挂载 tmpfs 到 /mnt/shared_memory）；IP 迁移至 192.168.137.232。
- 验证：球检测 3 球全检出（red 0.92/blue 0.90/green 0.87）；/odom 10 Hz 且 yaw 随 IMU 变化；/imu 返回 `{"ok":true,"yaw":5.61,...}`；自身遮挡滤波后 <0.45m 点 = 0；WSL 发 goal 到容器 move_base 成功（需 export ROS_IP=192.168.137.232）；**导航闭环 SUCCEEDED：goal (-0.20,1.00) 10s 到达，最终 odom (-0.218,0.961) 误差 ~4cm**；foot 模式转向死区确认（yaw<12 不动，15→21°/s、30→36°/s）。
- 遗留风险：simple_odom 重启后重置 init (-0.70,1.00) 但机器物理位置可能已移动——odom 绝对位置不闭合（无闭环定位），比赛需重新对齐起点；XGO 固件 yaw 步进死区 <12，小误差角修正依赖 cym final_yaw 逻辑（tolerance 0.08rad）；机器仅左侧两轮有驱动（右侧无刷被动），foot 模式为唯一可靠运动模式，wheel 模式转向打滑不可用；机器人侧 C++ 节点 master 掉线后不自动重连。

## 2026-08-05｜接入独立发布版 CymPlanner 局部规划器

- 状态：改动完成
- 目标：把 `tmp/cym_planner_standalone_20260713.zip` 中的独立发布版 `cym_planner` 源码包接入本仓库源码，替换离线演示原有的 `TrajectoryPlannerROS` 局部规划器；规划器内部的 OpenCV 窗口改为把全部可视化图像发布为 ROS 话题，供 rosmaster 上的 RViz 直接订阅。
- 影响文件：`catkin_ws/src/cym_planner/`（新增包）、`catkin_ws/src/robot_dog_navigation/{config/move_base.yaml,launch/offline_navigation.launch,launch/robot_visualization.launch,rviz/offline_navigation.rviz,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：把独立包源码复制到 `catkin_ws/src/cym_planner`，`cym_planner_params.json` 由 GB18030 转为 UTF-8，插件描述乱码修正；`cym_planner.h/.cpp` 移除 `cv::namedWindow/imshow/resizeWindow/waitKey`，新增 `sensor_msgs/Image` 发布器（`/cym_planner/map_image` 为代价地图与路径叠加图、放大 5 倍；`/cym_planner/plan_image` 为车体系 600×600 路径俯视图，话题名可由 `~/map_image_topic`、`~/plan_image_topic` 覆盖）；`package.xml` 与 `CMakeLists.txt` 增加 `sensor_msgs` 依赖。`move_base.yaml` 的 `base_local_planner` 改为 `cym_planner/CymPlanner`，两个 launch 均加载 `cym_planner_params.json`，RViz 配置新增两张 `rviz/Image` 显示。
- 验证：package/plugin/launch XML 均通过 XML 解析；参数文件按 YAML 解析成功且顶层键为 `CymPlanner`；修改后的源码无 `namedWindow/imshow/waitKey/highgui` 残留；离线与实机 launch 均能找到并加载参数文件。已部署至机器狗 `ros-noetic` 容器；安装 OpenCV 4.2 后，`catkin_make --pkg cym_planner robot_dog_navigation robot_dog_yolo_dataset` 成功，CymPlanner 插件可被 `nav_core` 发现，导航 launch 静态解析通过；未启动 `move_base` 或底盘控制。
- 遗留风险：该插件参数为 SmartCar 车体标定值（如 `max_vel_x: 14.0`、`max_vel_theta: 20.5`），远超机器狗安全速度；离线演示无 `/cmd_vel` 订阅者且实机 launch 已把 `cmd_vel` 重映射到禁用话题，但在接入真实底盘前必须按机器狗重新标定速度与增益，并验证避障与终点对准行为。

## 2026-08-05｜雷达正前方圆形区域过滤节点

- 状态：改动完成
- 目标：新增只读过滤节点，把 `/scan` 中雷达正前方 15 cm 处、半径 15 cm 圆形区域内的点置为 `inf`，用于屏蔽安装在雷达前方的机械臂；不访问底盘或雷达串口。
- 影响文件：`catkin_ws/src/robot_dog_navigation/{scripts/scan_circle_filter.py,launch/scan_circle_filter.launch,CMakeLists.txt}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：新增 Python3 节点订阅 `/scan` 发布 `/scan_filtered`，逐点把笛卡尔坐标落入以 `(center_x=0.15, center_y=0.0)` 为圆心、`radius=0.15` 的圆内的点置为 `inf` 并清零强度，其余字段原样透传；圆心与半径均可由 launch 参数覆盖，半径拒绝负值。新增配套 launch 与 `catkin_install_python` 安装声明。
- 验证：Python 语法检查通过；圆形判定断言覆盖圆心点、圆内近/远端、圆外侧方/后方/紧邻雷达点，均符合预期；Git 空白检查通过。已随导航包部署至机器狗，在 Noetic 容器构建成功，`scan_circle_filter.launch --nodes` 静态解析通过；未启动过滤节点或雷达。
- 遗留风险：圆位置按雷达坐标系（`laser_frame`）定义，机械臂若不在雷达扫描平面内则无需过滤；costmap 需将 `scan` 的 `topic` 改为 `/scan_filtered` 才能生效。

## 2026-08-05｜YOLO 相机训练集采集功能包

- 状态：改动完成
- 目标：新增独立 ROS 功能包，通过 USB 相机每 0.5 秒采集一张图片，共采集 600 张，供后续 YOLO 训练标注使用。
- 影响文件：`catkin_ws/src/robot_dog_yolo_dataset/`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：新增 OpenCV 相机采集节点、默认参数 launch 文件和使用说明；默认以单调时钟每 0.5 秒保存一次，文件连续编号至 600 张。节点不订阅或发布底盘控制话题；中断时释放相机，连续 20 次读取失败时退出。
- 验证：独立审查确认默认采集数量与间隔、定时逻辑、Catkin 安装声明和 launch 参数；本地 Python 语法、launch/package XML、默认值/关键错误路径断言与 Git 空白检查均通过。已部署至机器狗 Noetic 容器，容器已安装 Python OpenCV 4.2 并映射 `/dev/video0`，Catkin 构建与 `yolo_image_collector.launch --nodes` 静态解析通过；未启动相机或写入训练图片。
- 遗留风险：目标机器尚未连接相机；OpenCV、相机设备号和 Linux 脚本执行权限需在部署时确认，采集结束后仍需人工完成 YOLO 标注。

## 2026-08-05｜机械臂键盘控制接入

- 状态：改动完成
- 目标：新增机械臂键盘控制节点，通过 OUMAX 手控服务 `kind=arm` 接口（`cartesian`、`claw`、`mid`）逐步控制 XGO 机械臂，并沿用运动键盘的 `u→y` 双确认与急停模式。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/arm_keyboard_teleop.py,launch/arm_keyboard_teleop.launch,host/launch_arm_keyboard_teleop.sh,CMakeLists.txt,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：`w/s` 步进 x 前伸/收回、`a/d` 步进 z 降低/升高、`q/e` 夹爪开合、`m` 回中（默认 home x=80、z=60，与手控服务默认一致）；步长默认 10（范围 1–20）、夹爪步长 10（范围 1–40），客户端在 0–255 内钳制并本地跟踪姿态作为步进基准。`enable_motion:=true` 才允许真实运动；`verify_identity` 校验与运动键盘一致；空格/x 锁定、Ctrl-C 第一次锁定第二次退出。机械臂命令为点目标，无持续运动，无需看门狗。
- 验证：Python 语法检查通过；启动脚本与 launch XML 与既有物理键盘模式逐段比对一致；host 启动器沿用 `raicom-control-handover acquire/release` 包裹。未上传、未启动、未发送任何串口或 HTTP 命令。
- 遗留风险：本地跟踪姿态与机械臂真实姿态可能漂移（若曾被其他程序移动），首次使用须先按 `m` 回中；首次实机测试须净空 1 m 并仅验证一次回中行为；`raicom-launch-arm-keyboard` 需要安装后在机器端部署脚本。

## 2026-08-05｜键盘 Ctrl-C 双次退出修复

- 状态：改动完成
- 目标：修复 `tty.setraw()` 下 Ctrl-C 只停止运动、无法退出键盘控制进程的问题；第一次 Ctrl-C 保持紧急停止，第二次退出程序。
- 影响文件：`catkin_ws/src/robot_dog_teleop/scripts/{keyboard_pulse_teleop.py,physical_keyboard_teleop.py,physical_keyboard_continuous.py}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：raw 模式关闭 ISIG，Ctrl-C 以字节 `\x03` 到达；原处理分支只调用 `_lock_and_stop` 且循环不退出。三个脚本均新增 `_ctrl_c_exit_armed` 标志：第一次 `\x03` 紧急停止并提示，第二次 `\x03` 跳出循环，`finally` 恢复终端并发送停止。空格/x 行为不变。
- 验证：三个脚本 Python 语法检查通过；改动经逐一复核，break 位于 `try/finally` 内，终端设置必然恢复。
- 遗留风险：无；行为变更已在启动提示与帮助文本中说明。

## 模板：YYYY-MM-DD｜改动标题

- 状态：进行中
- 目标：
- 影响文件：
- 实施记录：
- 验证：
- 遗留风险：

读取与写入时机由 `project-memory-records` 技能定义。

## 2026-08-04｜带断链停止的连续键盘控制

- 状态：改动完成
- 目标：新增独立连续键盘模式：按住方向键持续刷新原厂幅值的前后/转向请求，停止刷新、节点异常或断链时自动停止；保留单点动模式。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_continuous.py,launch/physical_keyboard_continuous.launch,host/launch_physical_keyboard_continuous.sh,host/install_host_handover.sh,CMakeLists.txt,README.md}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：基于机器既有 `oumax-manual.service` UDP `gamepad` 接口（仅本机 `127.0.0.1:8766`）实现；该服务已提供 0.35 秒 UDP 看门狗。连续节点维持原厂默认前后 `17`、yaw `55`，以最多 10 Hz 的终端重复键刷新；本地无刷新 0.25 秒即连续发送三帧零命令，并保留 `u→y` 确认、空格/x/Ctrl-C 锁定停止和唯一串口服务切换。
- 验证：目标环境 Python 模拟验证前后归一化 `17/25=0.68`、yaw 归一化 `55/80=0.6875`、同方向 0.10 秒内限流、方向切换与三帧零停止；Python 语法、launch XML、宿主启动脚本语法、Git 空白检查、WSL `rospack find` 与 `roslaunch --nodes ... enable_motion:=false` 均通过。两次 WSL `catkin_make` 均卡在既有 CMake 构建系统检查并在 55 秒上限内超时，未进入本包编译；未连接、上传或启动机器狗。
- 遗留风险：普通 SSH 终端没有 key-up 事件；方向键释放后依赖客户端停止自动重复，少数终端可能在初始重复延迟期间动作不连续。若需要可靠“松键即停”，应另行采用宿主机 evdev 原始输入。连续控制会真实运动，部署后不得自动启动；首次必须在净空场地验证停止、本地超时、UDP 断链超时和实体急停。

## 2026-08-04｜键盘自动重复脉冲锁定

- 状态：改动完成
- 目标：防止终端键盘自动重复把单次 0.20 秒点动串联为连续运动；每次成功物理点动后自动重新锁定，下一次动作须再次 `u`、`y` 确认。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_teleop.py,README.md}`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：实机日志显示按住 `w` 产生了多次约间隔 0.20 秒的 accepted pulse，现有计时器会被后续重复键取消，无法实现单次点动的预期边界。
- 验证：本地模拟覆盖 `u→y→w→重复 w`，确认仅一次运动请求和一次超时停止；模拟请求失败后确认程序锁定、发送停止且重复键不重试。Python 语法、WSL Catkin 构建和 Git 空白检查通过。用户要求部署后，机器端脚本已更新并在容器内重新构建、Python 语法和节点解析通过；上一版备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-single-pulse-lock`。未重启当时的旧键盘进程或发送新的运动命令。
- 遗留风险：当前运行中的旧键盘程序不具备自动重复锁定，须由用户 Ctrl-C 退出后才会加载新版本；重启后每次动作都需要 `u`、`y`、方向键，且首次强度为原厂默认幅值，必须在净空场地单次验证。

## 2026-08-04｜键盘原地转向独立标定

- 状态：改动完成
- 目标：将真实键盘控制的前后与原地转向强度分离，并复用原厂 Dog_LM 摇杆默认强度：前后 XGO 值 `17`、`a/d` XGO 值 `55`，参数上限保持在原厂摇杆范围（前后 `25`、yaw `70`），脉冲仍不超过 `0.20 s`。
- 影响文件：`catkin_ws/src/robot_dog_teleop/{scripts/physical_keyboard_teleop.py,launch/physical_keyboard_teleop.launch,README.md}`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：实机日志已确认 `a/d` 的 HTTP 请求正常到达 OUMAX 服务；随后按用户要求读取原厂 `dog_Joystick.py`：默认 `step_control=70`，前后映射为约 `17`，yaw 映射为约 `55`（上限 `100`）。原先的保守 yaw `16` 方案已弃用；新方案保留键盘程序的脉冲超时、急停和同进程确认保护。
- 验证：本地 Python 语法、launch XML、WSL Catkin 构建和物理 launch 节点解析通过；用户要求部署后，机器端脚本、launch 和说明已更新，上一版物理键盘脚本/launch 备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-original-values`，容器内 Catkin 构建、Python 语法和节点解析通过。未重启或改变当时运行中的旧实控进程，未发送新的运动命令。
- 遗留风险：新参数会使首次 `a/d` 实际转向更明显；当前运行中的旧实控进程不会热加载新参数，须由用户主动退出并重新启动。重启后必须在净空场地单次验证方向；前后/yaw 值只是复刻原厂默认幅值，不是完整复刻原厂持续摇杆的时间行为，也不是 m/s 或 rad/s。

## 2026-08-04｜手控服务就绪等待修复

- 状态：改动完成
- 目标：修复控制权接管脚本在 OUMAX 服务刚被 systemd 启动时立即探测健康接口、误判服务失败并回滚的问题；只增加有限就绪等待，不改变运动接口。
- 影响文件：`catkin_ws/src/robot_dog_teleop/host/raicom-control-handover`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：实机复现显示 `oumax-manual.service` 从启动到监听 `127.0.0.1:8765` 存在约 1 秒初始化窗口；当前脚本在 systemd active 后立即 `curl`，触发安全回滚。新增总时限约 5 秒、每 0.2 秒一次的只读 `/health` 重试，并校验 `ok`、串口和端口身份；超时/服务退出时先停止手控服务、等待串口释放，才恢复原厂 UI。回滚后原厂 UI 已恢复、OUMAX 服务已停止、未发送运动命令。
- 验证：Bash 语法与 Git 空白检查通过；mock `systemctl`、`fuser`、`curl` 验证前五次健康检查失败、第六次返回正确身份时仍能获得控制权，并在 release 后恢复原厂 UI。用户授权修复后，已上传至机器工作区和 `/usr/local/sbin/raicom-control-handover`，旧帮助程序备份为 `/usr/local/sbin/raicom-control-handover.20260804-readiness.bak`；实机只读回归成功完成“原厂 UI 停止 → OUMAX 服务监听并返回正确 `/health` → 原厂 UI 恢复”，两端服务状态均正确，未启动键盘节点、未调用 `/command` 或发送运动命令。
- 遗留风险：不得在修复验证时启动物理键盘节点或调用 `/command`；仅允许检查 `/health`。

## 2026-08-03｜机器狗键盘控制权自动切换

- 状态：改动完成
- 目标：在宿主机上将原厂 `common/main.py` 迁移为可控服务；真实键盘控制启动时临时停止原厂程序并启用 OUMAX 手动服务，退出时恢复原厂程序。当前只在本地编写，不上传、不运行。
- 影响文件：`catkin_ws/src/robot_dog_teleop/host/`、`catkin_ws/src/robot_dog_teleop/README.md`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：开始前已确认现机原厂程序由 `/etc/rc.local` 启动且持有 `/dev/ttyAMA0`；OUMAX 服务已收紧为仅本机监听。新增可控的原厂 UI systemd 单元、控制权 acquire/release 帮助程序、交互键盘启动包装器和显式 `--cutover` 安装脚本。它只替换经精确核验的 `rc.local` 原厂启动行并保留备份，拒绝 raw/其他手控服务并在任一接管失败时恢复原厂 UI；不会重新执行包含网络清理逻辑的整个 `rc.local`。
- 验证：三个 Bash 脚本的 `bash -n` 通过；在 WSL 以 mock `systemctl`、`fuser`、`curl` 验证 acquire 后原厂服务变为停止且 OUMAX 服务变为运行、release 后顺序反转；Git 空白检查通过。用户要求上传后，新包已同步到机器 `/home/pi/ros_ws/src/robot_dog_teleop`，旧版已备份为 `/home/pi/ros_ws/backups/robot_dog_teleop-20260804-control-handover`；容器内 Catkin 构建、两个键盘 launch 节点解析、Python/launch XML 和三个宿主机脚本语法检查通过。未执行安装脚本、未停止原厂程序、未启动实控节点或发送运动命令。
- 遗留风险：部署前必须复核 `rc.local` 启动行仍与安装脚本一致，并确认没有外部路径重启 `common/main.py`。真实串口接管与首次点动仍须在用户确认电量、急停和场地条件后进行。

## 2026-08-03｜机器狗官方手动控制桥接

- 状态：改动完成
- 目标：在不抢占底盘串口的前提下，将已确认的键盘请求话题受控转发给机器现有的 OUMAX 手动控制服务，实现真实键盘点动的可部署实现；默认禁止实际运动。
- 影响文件：`catkin_ws/src/robot_dog_teleop/`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`；机器端 `ros-noetic` 容器与既有 `oumax-manual.service`。
- 实施记录：开始前确认宿主机 `oumax-manual.service` 正在独占 `/dev/ttyAMA0`，并在 `127.0.0.1:8765` 提供 `/health` 与 `/command` 接口；容器可访问健康接口。最终实现为同一进程内的 `physical_keyboard_teleop.py`：它不打开串口、也不订阅 ROS 速度话题，仅在键盘本地 `u`、`y` 双确认后调用该唯一服务。仅允许前后和原地转向，XGO 指令值硬限为 `1..8`、脉冲硬限为 `0.05..0.20 s`；零命令、超时、异常和退出均请求停止。取消了会被 ROS 话题绕过的独立 bridge，并以脉冲 ID 消除旧定时器对新命令的竞态。
- 验证：本地 WSL Catkin 构建、Python 语法、launch XML 和物理 launch 节点解析通过；机器容器内 `catkin_make`、包解析、物理 launch 节点解析、Python 语法和 XML 解析通过。新包已上传，上一版保留在 `/home/pi/ros_ws/backups/robot_dog_teleop-20260803-physical-keyboard`；在用户授权后，机器端手动服务源码已备份为 `/home/pi/oumax-xgo/manual_control_server.py.20260803-localhost.bak`，并收紧为仅监听 `127.0.0.1:8765/8766`，LAN 地址探测失败、容器健康探测成功；未启动物理控制 launch、未发送 HTTP 控制请求、未发送底盘命令。
- 遗留风险：首次真实运动尚未获现场安全确认。`/etc/rc.local` 自动启动的原厂 `common/main.py` 当前仍持有 `/dev/ttyAMA0`，不能与 OUMAX 手动服务并行使用；且应用日志显示电量为 9，须先充电。未经用户明确同意停止/替换原厂主程序、确认唯一串口持有者、急停/断电可达、站稳姿态，以及在 1 m 净空内验证首次单脉冲方向与停止行为，不得启动物理控制。

## 2026-08-03｜机器狗投影尺寸与键盘点动控制

- 状态：改动完成
- 目标：将 RViz 矩形替身及规划足迹调整为长 0.27 m、宽 0.16 m；新增默认锁定、明确确认后才可发出短时速度脉冲的键盘控制程序。实现阶段不部署或移动；后续已在机器开机后完成上传与静态核验。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`catkin_ws/src/robot_dog_teleop/`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`。
- 实施记录：矩形 Marker 与 footprint 已同步为长 0.27 m、宽 0.16 m；新增独立 `robot_dog_teleop` 包，默认只发布 `/robot_dog_teleop/requested_cmd`，不发布 `/cmd_vel`、不访问串口。程序默认锁定，按 `u` 后 5 秒内按 `y` 才解锁；`w/s/a/d` 每次仅请求 0.20 秒脉冲，空格、`x`、Ctrl-C 和退出均归零并锁定。
- 验证：WSL Catkin 构建通过并识别 `robot_dog_teleop`；Python、launch XML、Bash 和 Git 空白检查通过；本地离线节点实测 Marker 是 `base_link` 下的 CUBE，`scale.x=0.27`、`scale.y=0.16`，局部 costmap 已发布；从 `(-0.70, 1.00)` 到 `(0.40, -0.75)` 的全局路径服务仍能到达目标点。机器开机后已同步到 `/home/pi/ros_ws/src/`，容器内 Catkin 编译、包解析、launch 节点解析、Python 语法和 0.27×0.16 足迹/隔离话题检查通过；未启动节点、未解锁、未发送任何硬件命令。
- 遗留风险：当前没有经确认的 ROS 底盘 bridge；键盘程序仅完成干运行请求链路。实机底盘速度接口及安全现场条件尚未验证；不得在未经用户再次确认、机器固定检查和紧急停止准备前部署或解锁运动。

## 2026-08-03｜实机 ROS 导航可视化部署

- 状态：进行中
- 目标：将 RICAM 地图与导航可视化包部署至机器狗 ROS Noetic 容器，使本地 RViz 可显示正确起点、0.30 m × 0.25 m 矩形、全局/1 m × 1 m 局部代价地图和实时雷达点云；不发送底盘速度指令。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/start_robot_rviz.sh`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/{CHANGE_LOG,MISTAKE_LOG}.md`；机器端 `/home/pi/ros_ws/src/robot_dog_navigation/` 与 `ros-noetic` 容器。
- 实施记录：全局和局部 costmap 参数已独立，膨胀半径均为 0.10 m；局部窗口改为 1 m × 1 m、0.01 m。新增从真实 `/scan` 实时转换 `/lidar_points` 和矩形 Marker 的只读节点、实机 launch 及本地 RViz 连接脚本；`move_base` 的速度输出重映射到无订阅者的隔离话题。机器端旧导航包已备份至 `/home/pi/ros_ws/backups/robot_dog_navigation-20260803-ricam-visualization`，新包已上传并在容器内构建；容器 Ubuntu 源切换至阿里云 ports 镜像，已安装 navigation、map-server 和 tf2-ros。
- 验证：机器端实测 RICAM 地图为 300 × 250、0.01 m、原点 `(-1.5, -1.25)`；起点 TF 为 `(-0.70, 1.00)`；Marker 为 `0.30 m × 0.25 m`；全局/局部膨胀均为 0.1，局部宽高均为 1.0；真实 `/scan` 与 `/lidar_points` 均约 10 Hz，两个 costmap 话题均已发布，隔离速度话题没有订阅者。机器端已看见本机 RViz 注册为地图、点云和两张代价地图的订阅者。
- 遗留风险：已确认机器狗无法连接本机 WSL 的 RViz 动态 TCPROS/XMLRPC 端口，当前无法完成实际数据传输与目标点回传；Windows 防火墙规则创建需要管理员权限。绝不启动底盘控制节点。

## 2026-08-03｜离线定点任务切换至 RICAM 场地地图

- 状态：改动完成
- 目标：将最新版仿真 `ricam_arena` 的 3.0 m × 2.5 m 栅格地图作为本地 `robot_dog_navigation` 定点任务的默认地图；暂不上传机器狗。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/{setup_offline_navigation,start_local_rosmaster,start_offline_navigation,verify_offline_navigation}.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：将 `ricam_arena.pgm` 复制到导航包内并新增配套 YAML，默认 launch 切换至该地图；规划 footprint 统一为长 0.30 m、宽 0.25 m，附加 0.01 m 边界；安全起点设为 `(-0.70, 1.00)`，模拟雷达保留给 RViz 显示但不参与障碍层。
- 验证：地图源与导航包副本 SHA-256 均为 `F0336D936FA407548130CC6E3EBE253D7B10AD91438DEF02D57B171C6BB31488`；本地 launch 实测 `/map` 为 300 × 250、0.01 m、原点 `(-1.5, -1.25)`，全局代价地图分辨率为 0.01 m、障碍层为 `false`；`move_base/make_plan` 从 `(-0.70, 1.00)` 到 `(0.40, -0.75)` 成功生成并精确结束于目标点；YAML、launch XML、Python 和全部 WSL Bash 脚本语法检查，以及 Git 空白检查均通过。
- 遗留风险：场地地图仅用于当前离线定点验证，尚未与真实雷达、机器人坐标系或实际安全边界标定；本次没有连接或上传机器狗。

## 2026-08-03｜RViz 矩形机器狗替身

- 状态：改动完成
- 目标：在本地离线 RViz 中以长 0.30 m、宽 0.25 m 的矩形可视化标记代替缺失的机器狗 URDF 模型。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`wsl-simulation/verify_offline_navigation.sh`、`docs/local-rviz-navigation-quickstart.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：模拟雷达节点新增本地 `visualization_msgs/Marker` 发布器，在 `base_link` 下发布蓝色 `CUBE` 作为机器人矩形替身；默认长 0.30 m、宽 0.25 m、高 0.10 m，均可由 launch 参数调整。RViz 默认配置新增 Marker 显示，自动验证增加 Marker 话题与长宽断言；全程未修改或访问机器狗硬件。
- 验证：本机 Noetic 已解析 `visualization_msgs`；节点语法、Bash 语法与 Git 空白检查通过。已重启本地离线 launch，实测 `/robot_body_marker` 为 `visualization_msgs/Marker`，`base_link`、`CUBE`、`scale.x=0.3`、`scale.y=0.25`、`scale.z=0.1` 均正确，且 `/rviz` 已订阅该话题。
- 遗留风险：尺寸按用户给出的长 30、宽 25 解释为常用机器人单位厘米，即 0.30 m × 0.25 m；当前规划 `footprint` 比视觉矩形宽，后续接入真实机器人前应单独依据实测尺寸统一规划碰撞边界。

## 2026-08-03｜本地离线全局规划与 RViz 场景

- 状态：改动完成
- 目标：在本机 WSL 的独立 ROS Noetic Master 中接入官方 `global_planner/GlobalPlanner`，提供离线地图、模拟雷达点云、全局代价地图和 RViz 默认视图；不连接或改动机器狗的 ROS Master。
- 影响文件：`catkin_ws/src/robot_dog_navigation/`、`blender-maps/`、`wsl-simulation/`、`README.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：新增离线导航功能包，使用官方 `move_base + global_planner/GlobalPlanner`、`map_server`、模拟 `/scan` 与 `/lidar_points`、静态 `map → odom → base_link → laser_frame` TF 和默认 RViz 配置；新增匹配的 `PGM + YAML` 栅格地图及可再生成的 Blender 场景脚本。WSL 脚本在 `~/raicom_ws` 的 ext4 文件系统构建，并固定 `ROS_MASTER_URI`、`ROS_IP` 和 `ROS_LOCALHOST_ONLY` 为回环地址；实机 `robot_dog_lidar` 包在本地构建中被黑名单排除。
- 验证：`catkin_make -DCATKIN_BLACKLIST_PACKAGES=robot_dog_lidar` 构建成功；无界面验证确认 `/map`、`/scan`、`/lidar_points`、`/move_base/global_costmap/costmap` 和官方全局路径均可收到；`RAICOM_VERIFY_RVIZ=1 bash wsl-simulation/verify_offline_navigation.sh` 进一步确认 WSLg RViz 配置可随离线 launch 启动。
- 遗留风险：D 盘剩余空间约 9.8 GiB；当前未找到 Blender 可执行文件，仓库保存的是可生成 `.blend` 的脚本而非二进制场景。地图、TF 和雷达数据均为离线模拟，接入真实传感器、定位或底盘前仍需单独设计安全边界与验证。

## 2026-07-30｜GitHub Actions 自动更新项目结构树

- 状态：改动完成
- 目标：在目录结构变化后自动更新 README 中的项目结构树。
- 影响文件：`.github/workflows/`、`scripts/`、`README.md`、`.gitignore`
- 实施记录：新增 README 结构树生成脚本和 GitHub Actions 工作流；以唯一标记限定更新范围。
- 验证：脚本通过 Python 编译、重复运行幂等性、唯一标记、排除内部目录和 Git 差异检查；GitHub Actions 首次运行成功。
- 遗留风险：仓库 Actions 设置必须持续允许 `GITHUB_TOKEN` 具有内容写入权限，自动提交才可在结构变化后推送。

## 2026-08-02｜导入机器狗上位机源码

- 状态：改动完成
- 目标：从机器狗上位机识别并导入可公开保存的源码到本仓库对应目录。
- 影响文件：`archive/preliminary-code/xgo-cm5/`、`archive/preliminary-code/oumax-xgo/`、`archive/preliminary-code/README.md`。
- 实施记录：从 `/home/pi/RaspberryPi-CM5/common/`、`robots/Dog_LM/` 与 `/home/pi/oumax-xgo/` 导入并复核；未导入 ROS 工作区，因为设备未安装 ROS 且远程不存在 ROS 包。初次筛选与预推送复核共剔除六份含硬编码云服务凭据的语音示例，并移除 IDE、打包和模型产物；最终快照为 274 个文件、约 2.9 MiB。
- 验证：逐文件大小校验和 Python 语法检查完成；二次凭据扫描无命中；未保留虚拟环境、构建目录、模型、密钥文件或长凭据字面量。
- 遗留风险：快照依赖设备上的专有运行时、模型与硬件接口，不能在当前 Windows 环境或未安装 ROS 的设备上直接构建运行。

## 2026-08-02｜创建机器狗全量源码快照

- 状态：改动完成
- 目标：在独立目录中保存机器狗的全部非系统用户/厂商/服务源码。
- 影响文件：`archive/full-device-source/`、`archive/full-device-source/SHA256SUMS.tsv`、`docs/ai-records/CHANGE_LOG.md`。
- 实施记录：从 `/home/pi/` 导入所有可识别的应用与厂商源码，并导入 7 份引用这些程序的自定义 systemd 服务定义；经预推送复核后，完整筛选快照为 590 文件、6,529,017 字节。
- 验证：590 个清单条目的文件大小和 SHA-256 摘要全部一致；二次凭据字面量与敏感文件名扫描无命中；Python 源码语法解析通过。
- 遗留风险：自动剔除了 27 份含凭据的源码/配置、8 个超过 5 MiB 的文件、3,699 个非源码运行文件，以及打包元数据和模型文件。该目录不是整个 Debian 根文件系统，且依赖专有运行时、模型与硬件，不能在当前 Windows 环境直接运行。

## 2026-08-02｜创建机器狗 ROS 功能包

- 状态：改动完成
- 目标：在机器狗的 ROS Noetic Docker 工作区创建可构建的最小功能包，并同步至本仓库。
- 影响文件：`catkin_ws/src/CMakeLists.txt`、`catkin_ws/src/robot_dog_bringup/`、`robot-information/actual-hardware-observations.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：在机器狗的 `ros-noetic` 容器工作区创建 `robot_dog_bringup`，实现只读系统状态发布节点、launch 文件、构建规则、许可证与使用说明；将 6 个包源码文件按 SHA-256 一致性校验同步到本仓库。为本地检出提供可用的 Catkin 顶层 `CMakeLists.txt`，避免复制只能在容器内解析的绝对符号链接；同时更新部署后的存储、Docker、ROS 和功能包实机信息。
- 验证：容器内 `catkin_make` 构建成功；功能包依赖可解析；`roslaunch robot_dog_bringup robot_dog_bringup.launch` 已启动节点并在 `/robot_dog_bringup/status` 收到主机名、内核与 ROS 发行版状态消息；同步前后 6 个包源码文件的 SHA-256 摘要一致。
- 遗留风险：ROS Noetic 已结束常规支持，镜像基于 Ubuntu Focal；容器使用宿主网络与 IPC，后续接入不受信任的 ROS 节点前应限制 ROS 网络边界。功能包当前不含任何硬件控制逻辑。

## 2026-08-02｜机器狗雷达启动探测

- 状态：改动完成
- 目标：在不发送底盘、舵机或串口控制命令的前提下，为已确认的雷达驱动提供 ROS 启动与 `/scan` 数据验证入口。
- 影响文件：`catkin_ws/src/robot_dog_lidar/`、`robot-information/actual-hardware-observations.md`、`docs/ai-records/CHANGE_LOG.md`、`docs/ai-records/MISTAKE_LOG.md`。
- 实施记录：通过机器随附 SDK、CP2102 的 USB ID、厂商程序配置和设备返回信息确认 YDLIDAR Tmini Plus；新增 `robot_dog_lidar` C++ 节点，使用随附 SDK 的 Unix 源码在 Noetic 容器内构建，发布 `/scan`。容器仅映射当前雷达节点为 `/dev/ydlidar`，并只读挂载 SDK 源码；节点硬编码该容器路径，未映射或访问底盘 `ttyAMA0`，默认以墙钟限时 10 秒且退出时关闭雷达。
- 验证：容器内 `catkin_make` 成功构建供应商 SDK 静态库和节点；独立代码复核确认端口不可被 launch 覆盖、限时不受仿真时间影响；实机启动后收到有效 `sensor_msgs/LaserScan`，设备返回 Tmini Plus、230400、10 Hz，并在限时结束后记录“scanning has stopped”；测试结束后未发现残留 ROS 或雷达进程。
- 遗留风险：容器设备映射的宿主来源是当前 `/dev/ttyUSB0`；如 USB 枚举变化，节点会安全失败，但需在重新启动前重新确认稳定枚举名与映射。供应商 SDK 编译存在既有格式和宏重定义警告，当前构建与实测不受影响。

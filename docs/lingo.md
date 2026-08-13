# 项目黑话词典（project-lingo）

用户常以口语化短句下达操作指令。本文件存放词条正文；触发入口与维护规则见
`.agents/skills/project-lingo/SKILL.md`。

## 高频索引

| 黑话 | 一句话含义 | 词条 |
| --- | --- | --- |
| 机器IP / IP未变 | 机器狗当前 WiFi 下的 IP 与访问入口（192.168.137.157） | [#机器IP](#机器IP) |
| 驱动左后轮转动 N 秒 | 对左后轮通道（索引 3）发送持续单轮轮控命令，并在时长结束后归零 | [#驱动左后轮转动-n-秒](#驱动左后轮转动-n-秒) |
| 同时驱动 4 个轮子 | 四个轮子同时同速转动指定时长，用于验证四轮驱动/前进能力 | [#同时驱动-4-个轮子](#同时驱动-4-个轮子) |

## 机器IP

- **等价说法**：机器IP、狗子IP、狗IP、机器狗的IP、IP未变、连机器
- **含义**：机器狗（OUMAX XGO mini3W，树莓派 CM5）在 WiFi 网络下的 IP 与访问方式；
  "IP未变"表示仍是 192.168.137.157。
- **前置条件**：机器已开机且 WiFi 已连上；手控服务需先取得串口控制权（默认被
  raicom-original-main.service 占用，须切换）。
- **精确动作**：
  1. 连通性：`ping 192.168.137.157`（当前 WiFi 网可达，2026-08-13 实测 80ms）。
  2. SSH：`pi@192.168.137.157:22`，用户 pi / 密码 pi。
  3. 手控服务 HTTP：`http://192.168.137.157:8765`（`/health`、`/command`；服务默认
     监听 0.0.0.0:8765，UDP 游戏手柄口 8766）。
  4. 串口控制权切换：停 `raicom-original-main.service` → 起 `oumax-manual.service`
     （或用 `/usr/local/sbin/raicom-control-handover`），切换后健康检查通过再发命令。
  5. 备用 IP：10.181.117.161（另一网络，2026-08-13 实测当前不可达）。
- **不是**：WSL 的 IP（192.168.137.232，DHCP 会变，ROS master 跑在 WSL 侧，与机器 IP
  不同）；`192.168.137.157` 不等于控制服务一定在跑（8765 未监听时须先切换服务）。
- **权威来源**：`docs/message_for_my_dog.md`（ip1/ip2）、`docs/local-rviz-navigation-quickstart.md`
  （实机 192.168.137.157 部署）、`docs/ai-records/CHANGE_LOG.md`（2026-08-08 条目：
  WSL IP 迁移至 192.168.137.232，与机器 IP 区分）。

## 驱动左后轮转动 N 秒

- **等价说法**：驱动左后轮转动 N 秒、左后轮转 N 秒、让左后轮动 N 秒
- **含义**：以单轮轮控方式驱动物理左后轮指定时长，用于现场动作或诊断。
- **前置条件**：机器已开机、场地净空且可随时断电；`/health` 返回正常，手控服务已取得
  串口控制权。
- **精确动作**：
  1. 向 `http://192.168.137.157:8765/command` 发送
     `{"kind":"wheel","enabled":true,"speeds":[0,0,0,1.2]}`，其中通道顺序为
     `[左前,右前,右后,左后]`。
  2. 在指定时长内持续刷新命令；结束或出错时必须发送
     `{"kind":"wheel","enabled":true,"speeds":[0,0,0,0]}` 停止。
- **不是**：不是左后腿舵机；不是左前轮（通道 0）；HTTP ACK 不等于该轮实际转动，必须现场观察。
- **权威来源**：`robot-src/host-services/oumax-xgo/manual_control_server.py`（`handle_wheel` 与
  `send_wheel_control`）、`docs/ai-records/mistakes/2026-08-13.md`。

## 同时驱动 4 个轮子

- **等价说法**：四个轮子一起转、四轮同驱、四轮全转、同时驱动4个轮子
- **含义**：以轮控方式让四个轮子同时同速转动指定时长，用于验证四轮驱动/直线前进能力。
- **前置条件**：机器已开机、场地净空（四轮同驱机器会整体前进，注意防跑走）；`/health`
  返回正常，手控服务已取得串口控制权。
- **精确动作**：
  1. 向 `http://192.168.137.157:8765/command` 发送
     `{"kind":"wheel","enabled":true,"speeds":[1.0,1.0,1.0,1.0]}`，通道顺序为
     `[左前,右前,右后,左后]`。
  2. 在指定时长内 10Hz 持续刷新；结束或出错时必须发送
     `{"kind":"wheel","enabled":true,"speeds":[0,0,0,0]}` 停止。
- **不是**：不是 foot（dog）行走模式；不是单轮驱动；命令 ACK 不等于四轮均实际转动
  （2026-08-13 实测左后轮不转），须现场观察。
- **权威来源**：`robot-src/host-services/oumax-xgo/manual_control_server.py`（`handle_wheel` 与
  `send_wheel_control`）、`docs/ai-records/mistakes/2026-08-13.md`、2026-08-13 四轮同驱实测。

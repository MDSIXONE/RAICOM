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
- 找最大轮廓 → 最小外接矩形/最小外接圆，取圆心横坐标作为偏差。
- 偏差送入 PID（P=50、I=0、D=30）计算转向量 `z_pid`：
  - `abs(z_pid) < 8`：直行 `move_x(18)`；
  - `abs(z_pid) >= 8`：按偏差方向 `turn()` 转向 + `move_x(15)`，并按偏差调整时长；
  - 未检测到线条：`dog.stop()` 停止。
- XGO 初始化自动识别机型（`read_firmware()` 读固件首字符，`M` → xgomini，否则 xgolite）。
- 板载按钮切换状态：A 巡线 / C color / D init；B 退出程序。

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

## 相关文件

- 来源：`archive/full-device-source/home-pi/RaspberryPi-CM5/robots/Mini3W_W/demos/follow_line.py`
  （与 Dog_LM 版本 SHA-256 完全一致，均为 11864 字节；本包副本仅将 shebang
  移到文件首行并改为 `python3`，其余代码未改动）。

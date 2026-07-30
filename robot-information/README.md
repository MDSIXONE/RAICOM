# 机器狗资料

本目录用于保存统一平台规格、上位机、摄像头、下位机和接口开发参考资料。

## 重要说明

竞赛规则只明确了上位机候选为“树莓派 CM 或者地平线 X 系列”，下位机为 ESP32；规则未公开具体装机型号、相机型号、镜头参数、机械臂型号和完整通信接口。因此本目录中的厂商文档分为两类：

- **规则依据**：来自仓库内的比赛规则 PDF，表示比赛约束。
- **公开参考**：从元器件原厂或官方文档站下载，帮助做接口、算力和视觉方案预研，不代表现场实机配置。

实际开发前，应拍照记录实机标签，并向上海德克仕机器人科技有限公司或比赛技术支持确认型号和版本。

## 目录

| 目录 | 内容 |
| --- | --- |
| [`compute/raspberry-pi-cm4/`](compute/raspberry-pi-cm4/) | 树莓派 Compute Module 4 参考资料 |
| [`compute/horizon-x3/`](compute/horizon-x3/) | 地平线 RDK X3 Module 参考资料 |
| [`camera/raspberry-pi-camera-module-3/`](camera/raspberry-pi-camera-module-3/) | Raspberry Pi Camera Module 3 参考资料 |
| [`control/esp32/`](control/esp32/) | ESP32 下位机参考资料 |
| [`actual-hardware-observations.md`](actual-hardware-observations.md) | 当前实机的网络、串口、IMU 和上位机识别观测 |
| [`download-manifest.md`](download-manifest.md) | 下载来源、文件用途、校验值和确认状态 |

## 与比赛规则的对应关系

| 规则项 | 当前能确认的内容 | 需要现场确认的内容 |
| --- | --- | --- |
| 上位机 | 树莓派 CM 或地平线 X 系列 | CM4/CM4S/其他 CM 型号，或 X3/X5 具体型号；内存、存储、系统镜像、载板 |
| 摄像头 | 规则要求完成包裹图片和字母识别 | 传感器、CSI/USB 接口、分辨率、帧率、镜头视场角、安装位置和驱动 |
| 下位机 | ESP32 | 芯片具体型号、固件版本、上位机与下位机通信协议 |
| 关节舵机 | 6V、4.5 kg·cm、360°磁编码、双轴 TTL 串口舵机 | 舵机具体型号、TTL 电平、波特率、地址、协议、零位和限位 |
| 抓取机构 | 规则任务要求抓取红/蓝海绵球并保持 3 秒 | 机械臂/夹爪型号、控制接口、抓取姿态和工作空间 |

## 已确认的实机观测

当前实机的 Type-C 调试链路已在 Windows 上枚举为 `USB-SERIAL CH340 (COM3)`；以 115200、8N1、无流控读取到 ESP32 启动日志，且 ICM20948 IMU 被识别。详见 [`actual-hardware-observations.md`](actual-hardware-observations.md)。

机头的屏幕、前置摄像头和 HDMI 输出高度符合 XGO CM4/CM5 AI 模组架构，但具体上位机型号和相机接口尚未实机确认。不要把 `COM3` 当作相机或上位机终端。

## 建议下一步

1. 对实际机器狗拍摄上位机、摄像头、舵机和载板标签。
2. 记录 `uname -a`、ROS 版本、Python/C++ 版本以及设备节点。
3. 导出相机实际支持的分辨率、帧率和曝光模式。
4. 向供应方索取整机 ROS 包、启动文件、底层通信协议和机械臂 API。
5. 将确认后的实机资料放入 `robot-information/private/`（不提交敏感信息），公开资料继续放在本目录。

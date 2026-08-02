# 机器狗资料下载清单

下载日期：2026-07-30
说明：以下 PDF 均为公开原厂/官方文档的本地副本。它们是开发参考，不等同于比赛统一平台的装机确认。

## 已下载文件

| 类别 | 本地文件 | 来源 | 主要用途 | 状态 |
| --- | --- | --- | --- | --- |
| 上位机候选 | [`compute/raspberry-pi-cm4/cm4-datasheet.pdf`](compute/raspberry-pi-cm4/cm4-datasheet.pdf) | [Raspberry Pi CM4 Datasheet](https://datasheets.raspberrypi.com/cm4/cm4-datasheet.pdf) | 复核 CM4 的接口、电源、启动、内存/存储和机械尺寸 | 公开参考 |
| 上位机候选 | [`compute/horizon-x3/rdk-x3-module-datasheet.pdf`](compute/horizon-x3/rdk-x3-module-datasheet.pdf) | [D-Robotics RDK X3 Module Datasheet](https://archive.d-robotics.cc/downloads/hardware/rdk_x3_module/RDK_X3_Module_Datasheet.pdf) | 复核 X3 模组的算力、MIPI CSI、USB、GPIO 和供电 | 公开参考 |
| 摄像头候选 | [`camera/raspberry-pi-camera-module-3/camera-module-3-product-brief.pdf`](camera/raspberry-pi-camera-module-3/camera-module-3-product-brief.pdf) | [Raspberry Pi Camera Module 3 Product Brief](https://datasheets.raspberrypi.com/camera/camera-module-3-product-brief.pdf) | 视觉识别相机的传感器、分辨率、自动对焦、视场角和视频模式参考 | 公开参考 |
| 下位机 | [`control/esp32/esp32-datasheet-en.pdf`](control/esp32/esp32-datasheet-en.pdf) | [Espressif ESP32 Series Datasheet](https://www.espressif.com/sites/default/files/documentation/esp32_datasheet_en.pdf) | 复核 ESP32 的电气特性、串口、无线和供电约束 | 公开参考 |

## 课程资源

| 类别 | 本地文件 | 来源 | 主要用途 | 状态 |
| --- | --- | --- | --- | --- |
| MAX 课程资源 | [`course-resources/max/课件.zip`](course-resources/max/课件.zip) | [MAX课件资源（语雀）](https://www.yuque.com/lixupeng-rquex/rmgnub/nc9blgmpywi59k0h) | 保存原始课件、示例程序和 YOLO 数据集；需要时再按用途选择性解压 | 公开资料，原始包 |

## 文件校验

SHA-256 用于确认本地资料未被意外替换。重新下载后如校验值变化，应同时更新下载日期和来源版本说明。

| 本地文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `compute/raspberry-pi-cm4/cm4-datasheet.pdf` | 11057926 | `D6946F8BB3E0276DEFA95B99B9D402A01A4805D3DE02D53F835E93044EA7AF97` |
| `compute/horizon-x3/rdk-x3-module-datasheet.pdf` | 1548622 | `D19AA84FB30B9F6B6857CF0F20CCA91F0B566DB9324C772EA4CA0412FCF828B2` |
| `camera/raspberry-pi-camera-module-3/camera-module-3-product-brief.pdf` | 1244344 | `578EFCAD6337696A29B9C068815A01D63DDCF7BEACF584051D61CF1CDDEEAF0A` |
| `control/esp32/esp32-datasheet-en.pdf` | 989232 | `6FDFF42CCE00775643335E0CCB1DC1024070BB86208A2C734E9C09675CA3894A` |
| `course-resources/max/课件.zip` | 91749775 | `00D59076D842D145FB698C142D51EDF449F6A469A803172D4F7BD195F7C84CFA` |

## 当前不能从规则推断的资料

- 具体机器狗整机型号和 CAD/装配图。
- 具体摄像头型号、连接线和 ROS 驱动。
- 机械臂、夹爪和舵机的型号、协议、地址及标定文件。
- 上位机载板、系统镜像、网络配置和启动文件。
- ESP32 固件、上位机—下位机消息定义及故障码。

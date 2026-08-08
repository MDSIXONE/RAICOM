# robot_dog_yolo_dataset

通过本机 USB 相机采集 YOLO 训练图片。默认立即开始拍摄，每 0.5 秒保存一张，共 600 张（约 5 分钟），保存为连续编号的 JPEG 图片。

## 依赖

目标机器需安装 ROS Noetic 的 `rospy` 与 OpenCV：

```bash
sudo apt install python3-opencv
```

从 Git 或 Windows 文件系统复制到 Linux 机器后，确认脚本可执行：

```bash
chmod +x ~/catkin_ws/src/robot_dog_yolo_dataset/scripts/yolo_image_collector.py
```

## 构建与运行

在工作空间根目录执行：

```bash
catkin_make
source devel/setup.bash
roslaunch robot_dog_yolo_dataset yolo_image_collector.launch
```

默认输出目录为 `~/yolo_dataset/images`，文件名形如 `image_0001.jpg`。

指定另一台相机或输出目录：

```bash
roslaunch robot_dog_yolo_dataset yolo_image_collector.launch \
  camera_index:=1 output_dir:=/home/robot/yolo_dataset/images
```

可选分辨率参数（0 表示使用相机默认值）：

```bash
roslaunch robot_dog_yolo_dataset yolo_image_collector.launch \
  image_width:=1280 image_height:=720
```

如果相机连续 20 次无法读取帧，节点会安全退出；可通过 `max_frame_failures` 修改该上限。

采集完成后仍需为图片制作 YOLO 格式标注文件；本功能包只负责生成训练图片。

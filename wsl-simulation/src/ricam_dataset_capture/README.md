# RICAM Dataset Capture

相机连接后运行：

```bash
roslaunch ricam_dataset_capture capture_600.launch image_topic:=/camera/rgb/image_raw
```

节点每 0.5 秒保存一张新帧，保存满 600 张后自动退出。默认写入 `data/images/`，并同步生成 `metadata.csv`。可通过 `output_dir:=/absolute/path` 改为数据盘目录。

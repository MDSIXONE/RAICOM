#!/usr/bin/env python3
"""ROS ball detection node: subscribe to a camera image topic, run the YOLOv8
ONNX ball model, draw boxes on the frame and republish the annotated image.

Designed to run on the local (WSL) machine against the robot's ROS master.
"""

import sys
import time
from pathlib import Path

import cv2
import numpy as np
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ball_detector import letterbox, load_session, pick_color, postprocess


class BallDetectorNode:
    def __init__(self):
        model_path = rospy.get_param("~model")
        self._conf = rospy.get_param("~conf", 0.5)
        self._iou = rospy.get_param("~iou", 0.45)
        self._imgsz = rospy.get_param("~imgsz", 640)
        names = rospy.get_param("~names", "red,blue,green")
        self._class_names = [n.strip() for n in names.split(",") if n.strip()]
        image_topic = rospy.get_param("~image_topic", "/camera/rgb/image_raw")
        output_topic = rospy.get_param("~output_topic", "/ball_detector/image")

        self._session = load_session(Path(model_path))
        self._input_name = self._session.get_inputs()[0].name
        expected_size = tuple(self._session.get_inputs()[0].shape[2:4])
        if self._imgsz not in expected_size:
            rospy.logwarn(
                "model expects input %s, using --imgsz %s", expected_size, self._imgsz
            )
        self._bridge = CvBridge()
        self._sub = rospy.Subscriber(
            image_topic, Image, self._on_image, queue_size=1, buff_size=2**24
        )
        self._pub = rospy.Publisher(output_topic, Image, queue_size=1)
        self._infer_times = []
        self._last_log = 0.0
        rospy.loginfo(
            "ball_detector_node ready: %s -> %s (model %s, conf %.2f)",
            image_topic,
            output_topic,
            model_path,
            self._conf,
        )

    def _on_image(self, msg):
        try:
            frame = self._bridge.imgmsg_to_cv2(msg, "bgr8")
        except Exception as error:  # noqa: BLE001
            rospy.logwarn_throttle(5.0, "bad image frame: %s", error)
            return

        boxed, scale, pad_x, pad_y = letterbox(frame, (self._imgsz, self._imgsz))
        blob = cv2.dnn.blobFromImage(
            boxed, scalefactor=1.0 / 255.0, size=(self._imgsz, self._imgsz), swapRB=True
        )
        start = time.perf_counter()
        outputs = self._session.run(None, {self._input_name: blob})
        self._infer_times.append((time.perf_counter() - start) * 1000.0)
        detections = postprocess(
            outputs[0],
            self._conf,
            self._iou,
            frame.shape,
            scale,
            (pad_x, pad_y),
        )
        for det in detections:
            det["name"] = (
                self._class_names[det["cls"]]
                if det["cls"] < len(self._class_names)
                else "cls{}".format(det["cls"])
            )
            color = pick_color(det["name"])
            cv2.rectangle(
                frame,
                (int(det["x1"]), int(det["y1"])),
                (int(det["x2"]), int(det["y2"])),
                color,
                2,
            )
            label = "{} {:.2f}".format(det["name"], det["conf"])
            cv2.putText(
                frame,
                label,
                (int(det["x1"]), max(15, int(det["y1"]) - 5)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                1,
            )

        now = time.time()
        if detections and now - self._last_log > 1.0:
            summary = ", ".join(
                "{}@({:.0f},{:.0f}){:.2f}".format(
                    d["name"], d["cx"], d["cy"], d["conf"]
                )
                for d in detections
            )
            rospy.loginfo("frame %s: %d balls | %s", msg.header.seq, len(detections), summary)
            self._last_log = now

        try:
            self._pub.publish(self._bridge.cv2_to_imgmsg(frame, "bgr8"))
        except Exception as error:  # noqa: BLE001
            rospy.logwarn_throttle(5.0, "publish failed: %s", error)

    def log_rate(self):
        if len(self._infer_times) >= 30:
            avg_ms = float(np.mean(self._infer_times[-60:]))
            rospy.loginfo(
                "inference %.1f ms/frame over last %d frames",
                avg_ms,
                min(60, len(self._infer_times)),
            )
            self._infer_times = []


def main():
    rospy.init_node("ball_detector_node")
    node = BallDetectorNode()
    rate = rospy.Rate(10)
    while not rospy.is_shutdown():
        node.log_rate()
        rate.sleep()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Save the newest ROS image every configured interval until max_images."""

import csv
import threading
from datetime import datetime
from pathlib import Path

import cv2
import rospy
from cv_bridge import CvBridge, CvBridgeError
from sensor_msgs.msg import Image


class TimedImageCapture:
    def __init__(self):
        self.image_topic = rospy.get_param("~image_topic", "/camera/rgb/image_raw")
        self.interval = float(rospy.get_param("~interval", 0.5))
        self.max_images = int(rospy.get_param("~max_images", 600))
        self.jpeg_quality = int(rospy.get_param("~jpeg_quality", 95))
        self.output_dir = Path(rospy.get_param("~output_dir")).expanduser().resolve()
        self.stop_when_complete = bool(rospy.get_param("~stop_when_complete", True))

        if self.interval <= 0.0:
            raise ValueError("~interval must be greater than zero")
        if self.max_images <= 0:
            raise ValueError("~max_images must be greater than zero")
        if not 1 <= self.jpeg_quality <= 100:
            raise ValueError("~jpeg_quality must be between 1 and 100")

        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_path = self.output_dir / "metadata.csv"
        if not self.metadata_path.exists():
            with self.metadata_path.open("w", newline="", encoding="utf-8") as stream:
                csv.writer(stream).writerow(
                    ["index", "filename", "wall_time", "ros_stamp", "topic"]
                )

        self.bridge = CvBridge()
        self.lock = threading.Lock()
        self.latest_message = None
        self.latest_stamp = None
        self.last_saved_stamp = None
        self.saved_count = 0
        self.session = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.subscriber = rospy.Subscriber(
            self.image_topic, Image, self.on_image, queue_size=1, buff_size=2**24
        )
        self.timer = rospy.Timer(rospy.Duration(self.interval), self.on_timer)
        rospy.loginfo(
            "Capturing up to %d images from %s every %.3f s into %s",
            self.max_images,
            self.image_topic,
            self.interval,
            self.output_dir,
        )

    def on_image(self, message):
        stamp = message.header.stamp.to_sec()
        if stamp == 0.0:
            stamp = rospy.get_time()
        with self.lock:
            self.latest_message = message
            self.latest_stamp = stamp

    def on_timer(self, _event):
        with self.lock:
            message = self.latest_message
            stamp = self.latest_stamp

        if message is None:
            rospy.logwarn_throttle(5.0, "Waiting for images on %s", self.image_topic)
            return
        if stamp == self.last_saved_stamp:
            rospy.logwarn_throttle(5.0, "No new image frame available yet")
            return

        try:
            frame = self.bridge.imgmsg_to_cv2(message, desired_encoding="bgr8")
        except CvBridgeError as exc:
            rospy.logerr("cv_bridge conversion failed: %s", exc)
            return

        index = self.saved_count + 1
        filename = f"capture_{self.session}_{index:04d}.jpg"
        output_path = self.output_dir / filename
        ok = cv2.imwrite(
            str(output_path), frame, [int(cv2.IMWRITE_JPEG_QUALITY), self.jpeg_quality]
        )
        if not ok:
            rospy.logerr("Failed to write %s", output_path)
            return

        wall_time = datetime.now().isoformat(timespec="milliseconds")
        with self.metadata_path.open("a", newline="", encoding="utf-8") as stream:
            csv.writer(stream).writerow(
                [index, filename, wall_time, f"{stamp:.9f}", self.image_topic]
            )

        self.saved_count = index
        self.last_saved_stamp = stamp
        rospy.loginfo("Saved image %d/%d: %s", index, self.max_images, output_path)
        if self.saved_count >= self.max_images:
            self.timer.shutdown()
            rospy.loginfo("Image capture complete: %d images", self.saved_count)
            if self.stop_when_complete:
                rospy.signal_shutdown("requested image count reached")


def main():
    rospy.init_node("timed_image_capture")
    TimedImageCapture()
    rospy.spin()


if __name__ == "__main__":
    main()

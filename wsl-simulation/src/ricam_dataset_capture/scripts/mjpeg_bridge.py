#!/usr/bin/env python3
"""Publish the OUMAX camera MJPEG stream as a ROS image topic.

The camera is not a ROS device: the host service picam_mjpeg_server.py serves
``http://127.0.0.1:8090/stream.mjpg``.  This node runs inside the ROS container
and republishes the frames as ``sensor_msgs/Image`` (bgr8) on
``/camera/rgb/image_raw`` by default.
"""

import cv2
import rospy
from cv_bridge import CvBridge
from sensor_msgs.msg import Image


class MjpegBridge:
    def __init__(self):
        self._url = rospy.get_param("~mjpeg_url", "http://127.0.0.1:8090/stream.mjpg")
        self._topic = rospy.get_param("~image_topic", "/camera/rgb/image_raw")
        self._frame_id = rospy.get_param("~frame_id", "camera")
        self._max_rate = rospy.get_param("~max_rate", 0.0)
        self._bridge = CvBridge()
        self._pub = rospy.Publisher(self._topic, Image, queue_size=1)
        self._cap = cv2.VideoCapture(self._url)
        if not self._cap.isOpened():
            raise RuntimeError("cannot open MJPEG stream: {}".format(self._url))
        rospy.loginfo("mjpeg_bridge publishing %s <- %s", self._topic, self._url)

    def run(self):
        rate = rospy.Rate(self._max_rate) if self._max_rate > 0 else None
        while not rospy.is_shutdown():
            ok, frame = self._cap.read()
            if not ok or frame is None:
                rospy.logwarn_throttle(5.0, "failed to read MJPEG frame; retrying")
                rospy.sleep(0.1)
                continue
            header = rospy.Header()
            header.stamp = rospy.Time.now()
            header.frame_id = self._frame_id
            self._pub.publish(self._bridge.cv2_to_imgmsg(frame, "bgr8", header=header))
            if rate is not None:
                rate.sleep()


def main():
    rospy.init_node("mjpeg_bridge")
    try:
        MjpegBridge().run()
    except RuntimeError as error:
        rospy.logerr("MjpegBridge refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

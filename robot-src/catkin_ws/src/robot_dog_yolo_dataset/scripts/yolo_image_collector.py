#!/usr/bin/env python3
"""Capture a fixed number of images from a local camera for YOLO labeling."""

import os
import time

import cv2
import rospy


def main():
    rospy.init_node("yolo_image_collector")

    camera_index = rospy.get_param("~camera_index", 0)
    output_dir = os.path.expanduser(
        rospy.get_param("~output_dir", "~/yolo_dataset/images")
    )
    image_count = int(rospy.get_param("~image_count", 600))
    interval = float(rospy.get_param("~interval", 0.5))
    image_prefix = rospy.get_param("~image_prefix", "image")
    image_width = int(rospy.get_param("~image_width", 0))
    image_height = int(rospy.get_param("~image_height", 0))
    max_frame_failures = int(rospy.get_param("~max_frame_failures", 20))

    if image_count <= 0:
        rospy.logerr("~image_count must be greater than zero.")
        return
    if interval <= 0:
        rospy.logerr("~interval must be greater than zero.")
        return
    if max_frame_failures <= 0:
        rospy.logerr("~max_frame_failures must be greater than zero.")
        return

    os.makedirs(output_dir, exist_ok=True)
    camera = cv2.VideoCapture(camera_index)
    if image_width > 0:
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, image_width)
    if image_height > 0:
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, image_height)

    if not camera.isOpened():
        rospy.logerr("Unable to open camera index %s.", camera_index)
        return

    rospy.loginfo(
        "Starting capture: %d images, every %.2f s, saving to %s",
        image_count,
        interval,
        output_dir,
    )

    saved_count = 0
    consecutive_frame_failures = 0
    next_capture_time = time.monotonic()
    try:
        while saved_count < image_count and not rospy.is_shutdown():
            remaining = next_capture_time - time.monotonic()
            if remaining > 0:
                rospy.sleep(remaining)

            success, frame = camera.read()
            if not success or frame is None:
                consecutive_frame_failures += 1
                rospy.logwarn(
                    "Camera frame %d could not be read (%d/%d); retrying.",
                    saved_count + 1,
                    consecutive_frame_failures,
                    max_frame_failures,
                )
                if consecutive_frame_failures >= max_frame_failures:
                    rospy.logerr("Camera did not provide a usable frame; stopping capture.")
                    break
                next_capture_time += interval
                continue

            consecutive_frame_failures = 0

            filename = "{prefix}_{number:04d}.jpg".format(
                prefix=image_prefix, number=saved_count + 1
            )
            output_path = os.path.join(output_dir, filename)
            if not cv2.imwrite(output_path, frame):
                rospy.logerr("Could not write %s; stopping capture.", output_path)
                break

            saved_count += 1
            rospy.loginfo("Saved %d/%d: %s", saved_count, image_count, output_path)
            next_capture_time += interval
    except rospy.ROSInterruptException:
        pass
    finally:
        camera.release()

    if saved_count == image_count:
        rospy.loginfo("Capture complete: %d images saved to %s", saved_count, output_dir)
    elif rospy.is_shutdown():
        rospy.loginfo("Capture interrupted after %d images.", saved_count)
    else:
        rospy.logerr("Capture stopped after %d of %d images.", saved_count, image_count)


if __name__ == "__main__":
    main()

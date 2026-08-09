#!/usr/bin/env python3
"""Keyboard teleop for mapping: publishes /cmd_vel, the OUMAX bridge executes it.

Hold a key to keep moving; releasing stops after a short timeout.  The command
goes through the normal /cmd_vel path so simple_odom integrates the motion and
slam_gmapping can build the map in the odom frame.

Keys:
  w / s    forward / reverse   (linear step)
  a / d    turn left / right   (angular step)
  space/x  stop
  q        quit
"""

import select
import sys
import termios
import time
import tty

import rospy
from geometry_msgs.msg import Twist


class MappingKeyboardTeleop:
    def __init__(self):
        self._rate_hz = float(rospy.get_param("~rate_hz", 10.0))
        self._linear_step = float(rospy.get_param("~linear_step", 0.05))
        self._angular_step = float(rospy.get_param("~angular_step", 0.30))
        self._stale_after = float(rospy.get_param("~stale_after", 0.25))
        self._cmd_vel_topic = rospy.get_param("~cmd_vel_topic", "/cmd_vel")
        self._pub = rospy.Publisher(self._cmd_vel_topic, Twist, queue_size=1)
        self._vx = 0.0
        self._wz = 0.0
        self._last_event = 0.0
        self._rate = rospy.Rate(self._rate_hz)

    def _read_key(self):
        ready, _, _ = select.select([sys.stdin], [], [], 0.05)
        return sys.stdin.read(1) if ready else ""

    def _publish(self):
        twist = Twist()
        twist.linear.x = self._vx
        twist.angular.z = self._wz
        self._pub.publish(twist)

    def _stop(self):
        self._vx = 0.0
        self._wz = 0.0
        self._last_event = time.monotonic()

    @staticmethod
    def _help():
        print(
            "Keys: w/s forward/reverse  a/d turn  space/x stop  q quit "
            "(hold to keep moving, release to stop)"
        )

    def run(self):
        if not sys.stdin.isatty():
            raise RuntimeError("mapping keyboard teleop requires an interactive terminal")
        settings = termios.tcgetattr(sys.stdin)
        self._last_event = time.monotonic()
        self._help()
        try:
            tty.setraw(sys.stdin.fileno())
            while not rospy.is_shutdown():
                key = self._read_key()
                if key == "w":
                    self._vx = self._linear_step
                    self._last_event = time.monotonic()
                elif key == "s":
                    self._vx = -self._linear_step
                    self._last_event = time.monotonic()
                elif key == "a":
                    self._wz = self._angular_step
                    self._last_event = time.monotonic()
                elif key == "d":
                    self._wz = -self._angular_step
                    self._last_event = time.monotonic()
                elif key in (" ", "x"):
                    self._stop()
                elif key in ("q", "\x03"):
                    self._stop()
                    break
                elif key:
                    self._help()
                if time.monotonic() - self._last_event > self._stale_after:
                    self._stop()
                self._publish()
                self._rate.sleep()
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._stop()
            self._publish()


def main():
    rospy.init_node("mapping_keyboard_teleop")
    try:
        MappingKeyboardTeleop().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("mapping keyboard teleop refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

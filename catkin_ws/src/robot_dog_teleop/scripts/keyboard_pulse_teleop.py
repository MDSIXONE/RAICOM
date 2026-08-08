#!/usr/bin/env python3
"""Deliberate keyboard teleoperation requests using bounded velocity pulses.

The node starts locked.  A user must press ``m`` then ``y`` to arm it.  Each
motion key sends only one short pulse and a timer always publishes zero again.
Space and ``x`` stop and lock the node; Ctrl-C stops on the first press and
exits the process on the second.
"""

import select
import sys
import termios
import threading
import time
import tty

import rospy
from geometry_msgs.msg import Twist


class KeyboardPulseTeleop:
    """A low-speed, explicit-arm keyboard controller with a dead-man timeout."""

    def __init__(self):
        self._command_topic = rospy.get_param(
            "~command_topic", "/robot_dog_teleop/requested_cmd"
        )
        self._mode_label = str(rospy.get_param("~mode_label", "DRY-RUN REQUESTS"))
        self._linear_speed = self._bounded_param("~linear_speed", 0.05, 0.01, 0.05)
        self._angular_speed = self._bounded_param("~angular_speed", 0.20, 0.05, 0.20)
        self._pulse_duration = self._bounded_param("~pulse_duration_sec", 0.20, 0.05, 0.50)
        self._publisher = rospy.Publisher(self._command_topic, Twist, queue_size=1)
        self._armed = False
        self._arm_requested_until = 0.0
        self._ctrl_c_exit_armed = False
        self._stop_timer = None
        self._lock = threading.Lock()

    @staticmethod
    def _bounded_param(name, default, minimum, maximum):
        value = float(rospy.get_param(name, default))
        if not minimum <= value <= maximum:
            raise ValueError("{} must be within [{}, {}]".format(name, minimum, maximum))
        return value

    def _publish_stop(self):
        self._publisher.publish(Twist())

    def _lock_and_stop(self, reason):
        with self._lock:
            self._armed = False
            self._arm_requested_until = 0.0
            if self._stop_timer is not None:
                self._stop_timer.cancel()
                self._stop_timer = None
            self._publish_stop()
        rospy.logwarn("Keyboard teleop locked and stopped: %s", reason)

    def _stop_after_pulse(self):
        with self._lock:
            self._publish_stop()
            self._stop_timer = None

    def _request_arm(self):
        self._arm_requested_until = time.monotonic() + 5.0
        print("ARM REQUESTED: prepare for movement; confirm clear space, people away and emergency stop reachable. Press y within 5 seconds.")

    def _confirm_arm(self):
        if time.monotonic() > self._arm_requested_until:
            print("Arm request expired. Press u, then y within 5 seconds.")
            return
        self._armed = True
        self._arm_requested_until = 0.0
        print("ARMED ({}): w/s move, a/d rotate. Every key is a {:.2f}s pulse. Space or x stops and locks.".format(
            self._mode_label, self._pulse_duration
        ))

    def _pulse(self, label, linear=0.0, angular=0.0):
        if not self._armed:
            print("LOCKED: press u, then y before any motion command can be sent.")
            return
        command = Twist()
        command.linear.x = linear
        command.angular.z = angular
        with self._lock:
            if self._stop_timer is not None:
                self._stop_timer.cancel()
            self._publisher.publish(command)
            self._stop_timer = threading.Timer(self._pulse_duration, self._stop_after_pulse)
            self._stop_timer.daemon = True
            self._stop_timer.start()
        print("MOTION PULSE: {} for {:.2f}s (linear={:.2f} m/s, angular={:.2f} rad/s)".format(
            label, self._pulse_duration, linear, angular
        ))

    @staticmethod
    def _read_key():
        ready, _, _ = select.select([sys.stdin], [], [], 0.1)
        return sys.stdin.read(1) if ready else ""

    def run(self):
        bindings = {
            "w": ("forward", self._linear_speed, 0.0),
            "s": ("reverse", -self._linear_speed, 0.0),
            "a": ("rotate left", 0.0, self._angular_speed),
            "d": ("rotate right", 0.0, -self._angular_speed),
        }
        if not sys.stdin.isatty():
            raise RuntimeError("keyboard teleop requires an interactive terminal")
        settings = termios.tcgetattr(sys.stdin)
        print("Keyboard teleop is LOCKED. Press u, then y to arm; space/x stop and lock; Ctrl-C stops, twice to exit.")
        try:
            tty.setraw(sys.stdin.fileno())
            while not rospy.is_shutdown():
                key = self._read_key()
                if not key:
                    continue
                if key == "\x03":
                    self._lock_and_stop("emergency stop")
                    if self._ctrl_c_exit_armed:
                        print("Ctrl-C pressed twice: exiting keyboard teleop.")
                        break
                    self._ctrl_c_exit_armed = True
                    print("Emergency stop sent. Press Ctrl-C again to exit the program.")
                elif key in (" ", "x"):
                    self._lock_and_stop("emergency stop")
                elif key == "u":
                    self._request_arm()
                elif key == "y":
                    self._confirm_arm()
                elif key in bindings:
                    self._pulse(*bindings[key])
                else:
                    print("Keys: u then y arm; w/s move; a/d rotate; space/x stop and lock; Ctrl-C stops, twice to exit.")
        finally:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
            self._lock_and_stop("node exit")


def main():
    rospy.init_node("robot_dog_keyboard_teleop")
    try:
        KeyboardPulseTeleop().run()
    except (RuntimeError, ValueError) as error:
        rospy.logerr("Keyboard teleop refused to start: %s", error)
        raise SystemExit(2)


if __name__ == "__main__":
    main()

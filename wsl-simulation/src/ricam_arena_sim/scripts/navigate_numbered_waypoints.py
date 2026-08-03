#!/usr/bin/env python3
"""Navigate numbered map vertices sequentially through move_base."""

import json
import math
from pathlib import Path

import actionlib
import rospy
import rospkg
import tf2_ros
from actionlib_msgs.msg import GoalStatus
from geometry_msgs.msg import Point, PoseStamped
from move_base_msgs.msg import MoveBaseAction, MoveBaseGoal
from nav_msgs.srv import GetPlan
from std_msgs.msg import Int32, String
from visualization_msgs.msg import Marker, MarkerArray


class NumberedWaypointNavigator:
    def __init__(self):
        self.frame_id = rospy.get_param("~frame_id", "map")
        self.base_frame = rospy.get_param("~base_frame", "base_link")
        self.primary_point_numbers = [
            int(number) for number in rospy.get_param("~point_numbers", [91, 711, 694])
        ]
        self.via_point_numbers = {
            str(segment): [int(number) for number in numbers]
            for segment, numbers in rospy.get_param(
                "~via_point_numbers",
                {
                    "91->711": [400, 392, 640],
                    "711->694": [741, 708, 702],
                },
            ).items()
        }
        self.point_numbers = self.expand_point_numbers()
        self.expected_global_planner = rospy.get_param(
            "~expected_global_planner", "navfn/NavfnROS"
        )
        self.expected_local_planner = rospy.get_param(
            "~expected_local_planner", "cym_planner/CymPlanner"
        )
        self.require_expected_planners = bool(
            rospy.get_param("~require_expected_planners", True)
        )
        self.preflight = bool(rospy.get_param("~preflight", True))
        self.plan_tolerance_m = float(rospy.get_param("~plan_tolerance_m", 0.05))
        self.server_timeout_sec = float(rospy.get_param("~server_timeout_sec", 20.0))
        self.goal_timeout_sim_sec = float(
            rospy.get_param("~goal_timeout_sim_sec", 120.0)
        )
        self.pass_through_intermediate = bool(
            rospy.get_param("~pass_through_intermediate", True)
        )
        self.waypoint_position_tolerance_m = float(
            rospy.get_param("~waypoint_position_tolerance_m", 0.12)
        )
        self.via_position_tolerance_m = float(
            rospy.get_param("~via_position_tolerance_m", 0.06)
        )
        self.position_tolerance_overrides = {
            int(number): float(tolerance)
            for number, tolerance in rospy.get_param(
                "~position_tolerance_overrides", {741: 0.11}
            ).items()
        }

        default_grid_json = (
            Path(rospkg.RosPack().get_path("ricam_arena_sim"))
            / "maps"
            / "ricam_arena_10cm_full_grid_all_numbered.json"
        )
        self.grid_json = Path(
            rospy.get_param("~grid_json", str(default_grid_json))
        ).resolve()

        self.status_publisher = rospy.Publisher("~status", String, queue_size=1, latch=True)
        self.current_waypoint_publisher = rospy.Publisher(
            "~current_waypoint", Int32, queue_size=1, latch=True
        )
        self.marker_publisher = rospy.Publisher(
            "~route_markers", MarkerArray, queue_size=1, latch=True
        )
        self.tf_buffer = tf2_ros.Buffer()
        self.tf_listener = tf2_ros.TransformListener(self.tf_buffer)
        self.move_base_client = actionlib.SimpleActionClient(
            "/move_base", MoveBaseAction
        )
        self.points = self.load_points()
        self.yaws = []

    def expand_point_numbers(self):
        if not self.primary_point_numbers:
            raise RuntimeError("point_numbers must contain at least one vertex number")
        expanded = [self.primary_point_numbers[0]]
        for previous, current in zip(
            self.primary_point_numbers, self.primary_point_numbers[1:]
        ):
            expanded.extend(self.via_point_numbers.get(f"{previous}->{current}", []))
            expanded.append(current)
        return expanded

    def publish_status(self, text):
        rospy.loginfo(text)
        self.status_publisher.publish(String(data=text))

    def load_points(self):
        data = json.loads(self.grid_json.read_text(encoding="utf-8"))
        mapping = data.get("number_to_coordinate_m", {})
        points = []
        for number in self.point_numbers:
            coordinate = mapping.get(str(number))
            if coordinate is None:
                raise RuntimeError(f"Vertex {number} is missing from {self.grid_json}")
            points.append((float(coordinate["x_m"]), float(coordinate["y_m"])))
        return points

    def compute_goal_yaws(self, start_x_m, start_y_m, start_yaw):
        yaws = []
        previous_x, previous_y = start_x_m, start_y_m
        for index, (number, (x_m, y_m)) in enumerate(
            zip(self.point_numbers, self.points)
        ):
            incoming_yaw = math.atan2(y_m - previous_y, x_m - previous_x)
            first_goal_distance = math.hypot(x_m - start_x_m, y_m - start_y_m)
            if index == 0 and first_goal_distance <= self.plan_tolerance_m:
                yaw = start_yaw
            elif number in self.primary_point_numbers:
                yaw = incoming_yaw
            elif index + 1 < len(self.points):
                next_x, next_y = self.points[index + 1]
                outgoing_yaw = math.atan2(next_y - y_m, next_x - x_m)
                vector_x = math.cos(incoming_yaw) + math.cos(outgoing_yaw)
                vector_y = math.sin(incoming_yaw) + math.sin(outgoing_yaw)
                if math.hypot(vector_x, vector_y) < 1e-9:
                    yaw = outgoing_yaw
                else:
                    yaw = math.atan2(vector_y, vector_x)
            else:
                yaw = incoming_yaw
            yaws.append(yaw)
            previous_x, previous_y = x_m, y_m
        return yaws

    @staticmethod
    def quaternion_yaw(orientation):
        return math.atan2(
            2.0
            * (
                orientation.w * orientation.z
                + orientation.x * orientation.y
            ),
            1.0
            - 2.0
            * (
                orientation.y * orientation.y
                + orientation.z * orientation.z
            ),
        )

    def verify_planners(self):
        global_planner = rospy.get_param("/move_base/base_global_planner", "")
        local_planner = rospy.get_param("/move_base/base_local_planner", "")
        self.publish_status(
            f"Planner check: global={global_planner}, local={local_planner}"
        )
        if not self.require_expected_planners:
            return
        if global_planner != self.expected_global_planner:
            raise RuntimeError(
                f"Expected global planner {self.expected_global_planner}, got {global_planner}"
            )
        if local_planner != self.expected_local_planner:
            raise RuntimeError(
                f"Expected local planner {self.expected_local_planner}, got {local_planner}"
            )

    def pose_stamped(self, x_m, y_m, yaw):
        pose = PoseStamped()
        pose.header.frame_id = self.frame_id
        pose.header.stamp = rospy.Time.now()
        pose.pose.position.x = x_m
        pose.pose.position.y = y_m
        pose.pose.orientation.z = math.sin(yaw / 2.0)
        pose.pose.orientation.w = math.cos(yaw / 2.0)
        return pose

    def current_pose(self):
        transform = self.tf_buffer.lookup_transform(
            self.frame_id,
            self.base_frame,
            rospy.Time(0),
            rospy.Duration(self.server_timeout_sec),
        )
        pose = PoseStamped()
        pose.header = transform.header
        pose.pose.position.x = transform.transform.translation.x
        pose.pose.position.y = transform.transform.translation.y
        pose.pose.position.z = transform.transform.translation.z
        pose.pose.orientation = transform.transform.rotation
        return pose

    def verify_plans(self, start):
        if not self.preflight:
            return
        rospy.wait_for_service("/move_base/make_plan", timeout=self.server_timeout_sec)
        make_plan = rospy.ServiceProxy("/move_base/make_plan", GetPlan)
        for number, (x_m, y_m), yaw in zip(
            self.point_numbers, self.points, self.yaws
        ):
            goal = self.pose_stamped(x_m, y_m, yaw)
            response = make_plan(start, goal, self.plan_tolerance_m)
            if not response.plan.poses:
                raise RuntimeError(f"Navfn preflight returned no path to vertex {number}")
            self.publish_status(
                f"Preflight vertex {number}: {len(response.plan.poses)} plan poses"
            )
            start = response.plan.poses[-1]

    def publish_route_markers(self):
        markers = MarkerArray()
        stamp = rospy.Time.now()

        line = Marker()
        line.header.frame_id = self.frame_id
        line.header.stamp = stamp
        line.ns = "numbered_waypoint_route"
        line.id = 0
        line.type = Marker.LINE_STRIP
        line.action = Marker.ADD
        line.scale.x = 0.025
        line.color.r = 0.10
        line.color.g = 0.85
        line.color.b = 0.25
        line.color.a = 0.95
        line.pose.orientation.w = 1.0
        for x_m, y_m in self.points:
            line.points.append(Point(x=x_m, y=y_m, z=0.04))
        markers.markers.append(line)

        for index, (number, (x_m, y_m)) in enumerate(
            zip(self.point_numbers, self.points), 1
        ):
            is_primary = number in self.primary_point_numbers
            sphere = Marker()
            sphere.header.frame_id = self.frame_id
            sphere.header.stamp = stamp
            sphere.ns = "numbered_waypoint_points"
            sphere.id = index
            sphere.type = Marker.SPHERE
            sphere.action = Marker.ADD
            sphere.pose.position.x = x_m
            sphere.pose.position.y = y_m
            sphere.pose.position.z = 0.05
            sphere.pose.orientation.w = 1.0
            sphere.scale.x = sphere.scale.y = sphere.scale.z = (
                0.10 if is_primary else 0.07
            )
            sphere.color.r = 0.10 if is_primary else 1.00
            sphere.color.g = 0.45 if is_primary else 0.55
            sphere.color.b = 1.00 if is_primary else 0.05
            sphere.color.a = 0.95
            markers.markers.append(sphere)

            label = Marker()
            label.header.frame_id = self.frame_id
            label.header.stamp = stamp
            label.ns = "numbered_waypoint_labels"
            label.id = index
            label.type = Marker.TEXT_VIEW_FACING
            label.action = Marker.ADD
            label.pose.position.x = x_m
            label.pose.position.y = y_m
            label.pose.position.z = 0.18
            label.pose.orientation.w = 1.0
            label.scale.z = 0.13
            label.color.r = label.color.g = label.color.b = label.color.a = 1.0
            label.text = str(number)
            markers.markers.append(label)

        self.marker_publisher.publish(markers)

    def wait_for_waypoint(
        self, number, x_m, y_m, allow_pass_through, position_tolerance_m
    ):
        start_time = rospy.Time.now()
        terminal_failure_states = {
            GoalStatus.PREEMPTED,
            GoalStatus.ABORTED,
            GoalStatus.REJECTED,
            GoalStatus.RECALLED,
            GoalStatus.LOST,
        }
        rate = rospy.Rate(10)
        while not rospy.is_shutdown():
            state = self.move_base_client.get_state()
            if state == GoalStatus.SUCCEEDED:
                return "goal"
            if state in terminal_failure_states:
                raise RuntimeError(
                    f"Navigation to vertex {number} failed with action state {state}"
                )

            if allow_pass_through:
                pose = self.current_pose()
                distance = math.hypot(
                    pose.pose.position.x - x_m,
                    pose.pose.position.y - y_m,
                )
                if distance <= position_tolerance_m:
                    self.move_base_client.cancel_goal()
                    self.move_base_client.wait_for_result(rospy.Duration(2.0))
                    return "pass-through"

            if (
                rospy.Time.now() - start_time
            ).to_sec() >= self.goal_timeout_sim_sec:
                self.move_base_client.cancel_goal()
                raise RuntimeError(f"Timed out navigating to vertex {number}")
            rate.sleep()

        raise rospy.ROSInterruptException()

    def run(self):
        self.verify_planners()
        start = self.current_pose()
        self.yaws = self.compute_goal_yaws(
            start.pose.position.x,
            start.pose.position.y,
            self.quaternion_yaw(start.pose.orientation),
        )
        self.verify_plans(start)
        self.publish_route_markers()
        if not self.move_base_client.wait_for_server(
            rospy.Duration(self.server_timeout_sec)
        ):
            raise RuntimeError("Timed out waiting for /move_base action server")

        for index, (number, (x_m, y_m), yaw) in enumerate(
            zip(self.point_numbers, self.points, self.yaws), 1
        ):
            point_kind = "primary" if number in self.primary_point_numbers else "via"
            self.current_waypoint_publisher.publish(Int32(data=number))
            self.publish_status(
                f"Navigating {index}/{len(self.points)} to {point_kind} vertex {number} "
                f"at ({x_m:.2f}, {y_m:.2f}), yaw={yaw:.3f}"
            )
            goal = MoveBaseGoal()
            goal.target_pose = self.pose_stamped(x_m, y_m, yaw)
            self.move_base_client.send_goal(goal)
            allow_pass_through = (
                self.pass_through_intermediate and index < len(self.points)
            )
            position_tolerance_m = (
                self.waypoint_position_tolerance_m
                if number in self.primary_point_numbers
                else self.via_position_tolerance_m
            )
            position_tolerance_m = self.position_tolerance_overrides.get(
                number, position_tolerance_m
            )
            completion_mode = self.wait_for_waypoint(
                number,
                x_m,
                y_m,
                allow_pass_through,
                position_tolerance_m,
            )
            self.publish_status(
                f"Reached {point_kind} vertex {number} ({completion_mode})"
            )

        self.current_waypoint_publisher.publish(Int32(data=0))
        self.publish_status(
            "Completed numbered route "
            + " -> ".join(map(str, self.primary_point_numbers))
            + " using expanded path "
            + " -> ".join(map(str, self.point_numbers))
        )
        rospy.sleep(1.0)


def main():
    rospy.init_node("numbered_waypoint_navigation")
    try:
        NumberedWaypointNavigator().run()
    except (RuntimeError, OSError, ValueError, KeyError, rospy.ROSException) as error:
        rospy.logfatal(str(error))
        raise SystemExit(1)
    except rospy.ROSInterruptException:
        pass


if __name__ == "__main__":
    main()

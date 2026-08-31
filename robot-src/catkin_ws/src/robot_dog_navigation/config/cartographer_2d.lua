-- Cartographer 2D configuration for the RICAM dog as a laser odometry layer
-- (odom -> base_link).  The M-7.0.0b8 firmware exposes no raw accel/gyro
-- stream and the foot gait has no wheel encoders, so this is laser-only:
-- use_imu_data=false（固件无原始 accel/gyro）；use_odometry=true（/odom_imu，
-- simple_odom yaw_only 仅 IMU 朝向先验）。The scan is /scan_filtered
-- (10 Hz, range filtered to the 3.0 x 2.5 m arena, 0.25 m near-field cut).
include "map_builder.lua"
include "trajectory_builder.lua"

options = {
  map_builder = MAP_BUILDER,
  trajectory_builder = TRAJECTORY_BUILDER,
  map_frame = "map",
  tracking_frame = "base_link",
  published_frame = "base_link",
  odom_frame = "odom",
  provide_odom_frame = true,
  publish_frame_projected_to_2d = false,
  -- 运动先验：use_odometry=true 订阅 /odom（launch 中 remap 到 /odom_imu），
  -- 该 odom 由 simple_odom 以 yaw_only 模式发布：仅含 IMU 朝向（yaw + IMU
  -- 差分角速度），位置恒等、vx=0——朝向用 IMU（可靠），位置全交给激光匹配。
  -- use_imu_data=false：M-7.0.0b8 固件无原始 accel/gyro，无法提供重力向量。
  use_odometry = true,
  use_nav_sat = false,
  use_landmarks = false,
  num_laser_scans = 1,
  num_multi_echo_laser_scans = 0,
  -- ydlidar 的 scan 点无有效 per-point 时间偏移，subdivision 段间时间恒等，
  -- cartographer 报 "previous subdivision time ... is not before current" 并
  -- 忽略大部分 scan（建图停滞）；且 1.0.0 要求 >=1（0 会 CHECK 崩溃）。
  -- 设 1 = 整帧一段不细分，跨帧按 header.stamp 比较即可正常推进。
  num_subdivisions_per_laser_scan = 1,
  num_point_clouds = 0,
  lookup_transform_timeout_sec = 0.2,
  submap_publish_period_sec = 0.3,
  pose_publish_period_sec = 5e-3,
  trajectory_publish_period_sec = 30e-3,
  rangefinder_sampling_ratio = 1.,
  odometry_sampling_ratio = 1.,
  fixed_frame_pose_sampling_ratio = 1.,
  imu_sampling_ratio = 1.,
  landmarks_sampling_ratio = 1.,
}

MAP_BUILDER.use_trajectory_builder_2d = true
MAP_BUILDER.num_background_threads = 2

TRAJECTORY_BUILDER_2D.use_imu_data = false
-- Near-field cut of scan_circle_filter (0.25 m) and arena far wall (~3.5 m).
TRAJECTORY_BUILDER_2D.min_range = 0.25
TRAJECTORY_BUILDER_2D.max_range = 8.0
TRAJECTORY_BUILDER_2D.min_z = -0.5
TRAJECTORY_BUILDER_2D.max_z = 0.5
TRAJECTORY_BUILDER_2D.missing_data_ray_length = 3.0
-- 10 Hz scan: accumulate 3 frames (0.3 s) before matching.
TRAJECTORY_BUILDER_2D.num_accumulated_range_data = 3
TRAJECTORY_BUILDER_2D.voxel_filter_size = 0.025

TRAJECTORY_BUILDER_2D.motion_filter.max_time_seconds = 5.
TRAJECTORY_BUILDER_2D.motion_filter.max_distance_meters = 0.2
TRAJECTORY_BUILDER_2D.motion_filter.max_angle_radians = math.rad(1.)

TRAJECTORY_BUILDER_2D.submaps.num_range_data = 90
TRAJECTORY_BUILDER_2D.submaps.grid_options_2d.resolution = 0.05
TRAJECTORY_BUILDER_2D.submaps.range_data_inserter.range_data_inserter_type =
    "PROBABILITY_GRID_INSERTER_2D"

POSE_GRAPH.optimize_every_n_nodes = 20

return options

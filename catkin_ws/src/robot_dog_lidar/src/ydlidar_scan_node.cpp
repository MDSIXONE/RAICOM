#include <cmath>
#include <limits>
#include <string>

#include <ros/ros.h>
#include <sensor_msgs/LaserScan.h>

#include <CYdLidar.h>

namespace {

class YDLidarScanNode {
 public:
  YDLidarScanNode()
      : nh_(),
        private_nh_("~"),
        publisher_(nh_.advertise<sensor_msgs::LaserScan>("/scan", 1)),
        started_(false),
        consecutive_failures_(0) {
    port_ = "/dev/ydlidar";
    private_nh_.param("baudrate", baudrate_, 230400);
    private_nh_.param("frame_id", frame_id_, std::string("laser_frame"));
    private_nh_.param("test_duration_sec", test_duration_sec_, 10.0);
    private_nh_.param("max_consecutive_failures", max_consecutive_failures_, 3);
  }

  ~YDLidarScanNode() { Stop(); }

  bool Start() {
    if (test_duration_sec_ < 0.0) {
      ROS_ERROR("test_duration_sec 只能为 0（持续扫描）或正数（限时测试）。");
      return false;
    }
    if (max_consecutive_failures_ < 1) {
      ROS_ERROR("max_consecutive_failures 必须大于或等于 1。");
      return false;
    }
    ConfigureVendorDriver();

    if (!lidar_.initialize()) {
      ROS_ERROR("YDLIDAR 初始化失败（端口 %s）：%s", port_.c_str(),
                lidar_.DescribeError());
      return false;
    }

    if (!lidar_.turnOn()) {
      ROS_ERROR("YDLIDAR 启动扫描失败：%s", lidar_.DescribeError());
      lidar_.disconnecting();
      return false;
    }

    started_ = true;
    ROS_INFO("YDLIDAR 已启动：port=%s, baudrate=%d, test_duration_sec=%.1f",
             port_.c_str(), baudrate_, test_duration_sec_);
    return true;
  }

  void Run() {
    const ros::WallTime deadline =
        test_duration_sec_ > 0.0
            ? ros::WallTime::now() + ros::WallDuration(test_duration_sec_)
            : ros::WallTime();

    while (ros::ok()) {
      if (test_duration_sec_ > 0.0 && ros::WallTime::now() >= deadline) {
        ROS_INFO("YDLIDAR 限时测试结束，正在关闭雷达。");
        break;
      }

      LaserScan vendor_scan;
      if (!lidar_.doProcessSimple(vendor_scan)) {
        ++consecutive_failures_;
        ROS_WARN_THROTTLE(1.0, "未收到有效雷达数据（%d/%d）：%s",
                          consecutive_failures_, max_consecutive_failures_,
                          lidar_.DescribeError());
        if (consecutive_failures_ >= max_consecutive_failures_) {
          ROS_ERROR("连续读取雷达数据失败，停止以保护设备。");
          break;
        }
        continue;
      }

      consecutive_failures_ = 0;
      Publish(vendor_scan);
    }
  }

  void Stop() {
    if (started_) {
      lidar_.turnOff();
      started_ = false;
    }
    lidar_.disconnecting();
  }

 private:
  void ConfigureVendorDriver() {
    const std::string ignore_array;
    int lidar_type = TYPE_TRIANGLE;
    int device_type = YDLIDAR_TYPE_SERIAL;
    int sample_rate = 4;
    int abnormal_check_count = 4;
    int intensity_bits = 8;
    bool fixed_resolution = true;
    bool disabled = false;
    bool auto_reconnect = true;
    float max_angle = 180.0F;
    float min_angle = -180.0F;
    float max_range = 64.0F;
    float min_range = 0.05F;
    float scan_frequency = 10.0F;

    lidar_.setlidaropt(LidarPropSerialPort, port_.c_str(),
                       port_.size());
    lidar_.setlidaropt(LidarPropIgnoreArray, ignore_array.c_str(),
                       ignore_array.size());
    lidar_.setlidaropt(LidarPropSerialBaudrate, &baudrate_,
                       sizeof(baudrate_));
    lidar_.setlidaropt(LidarPropLidarType, &lidar_type,
                       sizeof(lidar_type));
    lidar_.setlidaropt(LidarPropDeviceType, &device_type,
                       sizeof(device_type));
    lidar_.setlidaropt(LidarPropSampleRate, &sample_rate,
                       sizeof(sample_rate));
    lidar_.setlidaropt(LidarPropAbnormalCheckCount,
                       &abnormal_check_count, sizeof(abnormal_check_count));
    lidar_.setlidaropt(LidarPropIntenstiyBit, &intensity_bits,
                       sizeof(intensity_bits));
    lidar_.setlidaropt(LidarPropFixedResolution, &fixed_resolution,
                       sizeof(fixed_resolution));
    lidar_.setlidaropt(LidarPropReversion, &disabled,
                       sizeof(disabled));
    lidar_.setlidaropt(LidarPropInverted, &disabled,
                       sizeof(disabled));
    lidar_.setlidaropt(LidarPropAutoReconnect, &auto_reconnect,
                       sizeof(auto_reconnect));
    lidar_.setlidaropt(LidarPropSingleChannel, &disabled,
                       sizeof(disabled));
    lidar_.setlidaropt(LidarPropIntenstiy, &fixed_resolution,
                       sizeof(fixed_resolution));
    // 厂商 Dog_LM 示例同样关闭 DTR 电机控制，避免额外串口控制线动作。
    lidar_.setlidaropt(LidarPropSupportMotorDtrCtrl, &disabled,
                       sizeof(disabled));
    lidar_.setlidaropt(LidarPropSupportHeartBeat, &disabled,
                       sizeof(disabled));
    lidar_.setlidaropt(LidarPropMaxAngle, &max_angle,
                       sizeof(max_angle));
    lidar_.setlidaropt(LidarPropMinAngle, &min_angle,
                       sizeof(min_angle));
    lidar_.setlidaropt(LidarPropMaxRange, &max_range,
                       sizeof(max_range));
    lidar_.setlidaropt(LidarPropMinRange, &min_range,
                       sizeof(min_range));
    lidar_.setlidaropt(LidarPropScanFrequency, &scan_frequency,
                       sizeof(scan_frequency));
    lidar_.enableGlassNoise(false);
    lidar_.enableSunNoise(false);
  }

  void Publish(const LaserScan& vendor_scan) {
    const float angle_increment = vendor_scan.config.angle_increment;
    if (angle_increment <= 0.0F) {
      ROS_ERROR_THROTTLE(1.0, "雷达返回了无效角度分辨率。");
      return;
    }

    sensor_msgs::LaserScan message;
    if (vendor_scan.stamp != 0U) {
      message.header.stamp.fromNSec(vendor_scan.stamp);
    } else {
      message.header.stamp = ros::Time::now();
    }
    message.header.frame_id = frame_id_;
    message.angle_min = vendor_scan.config.min_angle;
    message.angle_max = vendor_scan.config.max_angle;
    message.angle_increment = angle_increment;
    message.scan_time = vendor_scan.config.scan_time;
    message.time_increment = vendor_scan.config.time_increment;
    message.range_min = vendor_scan.config.min_range;
    message.range_max = vendor_scan.config.max_range;

    const std::size_t range_count = static_cast<std::size_t>(
        std::ceil((message.angle_max - message.angle_min) /
                  message.angle_increment)) +
                                    1U;
    message.ranges.assign(range_count,
                          std::numeric_limits<float>::infinity());
    message.intensities.assign(range_count, 0.0F);

    for (const auto& point : vendor_scan.points) {
      if (!std::isfinite(point.range) || point.range < message.range_min ||
          point.range > message.range_max) {
        continue;
      }
      const int index = static_cast<int>(std::ceil(
          (point.angle - message.angle_min) / message.angle_increment));
      if (index < 0 || static_cast<std::size_t>(index) >= range_count) {
        continue;
      }
      message.ranges[static_cast<std::size_t>(index)] = point.range;
      message.intensities[static_cast<std::size_t>(index)] = point.intensity;
    }

    publisher_.publish(message);
  }

  ros::NodeHandle nh_;
  ros::NodeHandle private_nh_;
  ros::Publisher publisher_;
  CYdLidar lidar_;
  std::string port_;
  std::string frame_id_;
  int baudrate_;
  double test_duration_sec_;
  int max_consecutive_failures_;
  bool started_;
  int consecutive_failures_;
};

}  // namespace

int main(int argc, char** argv) {
  ros::init(argc, argv, "ydlidar_scan");
  YDLidarScanNode node;
  if (!node.Start()) {
    return 1;
  }
  node.Run();
  node.Stop();
  return 0;
}

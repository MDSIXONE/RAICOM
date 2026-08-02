#include <iostream>
#include <string>
#include <map>
#include "CYdLidar.h"
#include "core/common/ydlidar_help.h"
#include <opencv2/opencv.hpp>

using namespace std;
using namespace ydlidar;
using namespace ydlidar::core::common;

#if defined(_MSC_VER)
#pragma comment(lib, "ydlidar_sdk.lib")
#endif

int main(int argc, char *argv[]) 
{
    printLogo();
    os_init();

    // 1. 自动检测雷达端口
    std::string port;
    std::map<std::string, std::string> ports = ydlidar::lidarPortList();
    std::map<std::string, std::string>::iterator it;

    if (ports.size() == 1) {
        port = ports.begin()->second;
    } else {
        int id = 0;
        for (it = ports.begin(); it != ports.end(); it++) {
            printf("[%d] %s %s\n", id, it->first.c_str(), it->second.c_str());
            id++;
        }

        if (ports.empty()) {
            printf("No Lidar was detected. Please enter the lidar serial port:");
            std::cin >> port;
        } else {
            while (ydlidar::os_isOk()) {
                printf("Please select the lidar port:");
                std::string number;
                std::cin >> number;

                if ((size_t)atoi(number.c_str()) >= ports.size()) {
                    continue;
                }

                it = ports.begin();
                id = atoi(number.c_str());

                while (id) {
                    id--;
                    it++;
                }

                port = it->second;
                break;
            }
        }
    }

    // 2. 配置雷达参数
    int baudrate = 230400;
    bool isSingleChannel = false;
    float frequency = 10.0f;

    CYdLidar laser;

    // 2.1 字符串参数
    laser.setlidaropt(LidarPropSerialPort, port.c_str(), port.size());
    std::string ignore_array;
    laser.setlidaropt(LidarPropIgnoreArray, ignore_array.c_str(), ignore_array.size());

    // 2.2 整数参数
    laser.setlidaropt(LidarPropSerialBaudrate, &baudrate, sizeof(int));
    int optval = TYPE_TRIANGLE; // Tmini Pro/Plus 雷达类型
    laser.setlidaropt(LidarPropLidarType, &optval, sizeof(int));
    optval = YDLIDAR_TYPE_SERIAL;
    laser.setlidaropt(LidarPropDeviceType, &optval, sizeof(int));
    optval = isSingleChannel ? 3 : 4; // 采样率
    laser.setlidaropt(LidarPropSampleRate, &optval, sizeof(int));
    optval = 8; // 强度位数
    laser.setlidaropt(LidarPropIntenstiyBit, &optval, sizeof(int));

    // 2.3 布尔参数
    bool b_optvalue = true;
    laser.setlidaropt(LidarPropFixedResolution, &b_optvalue, sizeof(bool));
    b_optvalue = false;
    laser.setlidaropt(LidarPropReversion, &b_optvalue, sizeof(bool));
    laser.setlidaropt(LidarPropInverted, &b_optvalue, sizeof(bool));
    b_optvalue = true;
    laser.setlidaropt(LidarPropAutoReconnect, &b_optvalue, sizeof(bool));
    laser.setlidaropt(LidarPropSingleChannel, &isSingleChannel, sizeof(bool));
    laser.setlidaropt(LidarPropIntenstiy, &b_optvalue, sizeof(bool));
    b_optvalue = false;
    laser.setlidaropt(LidarPropSupportMotorDtrCtrl, &b_optvalue, sizeof(bool));
    laser.setlidaropt(LidarPropSupportHeartBeat, &b_optvalue, sizeof(bool));

    // 2.4 浮点参数
    float f_optvalue = 180.0f;
    laser.setlidaropt(LidarPropMaxAngle, &f_optvalue, sizeof(float));
    f_optvalue = -180.0f;
    laser.setlidaropt(LidarPropMinAngle, &f_optvalue, sizeof(float));
    f_optvalue = 64.0f;
    laser.setlidaropt(LidarPropMaxRange, &f_optvalue, sizeof(float));
    f_optvalue = 0.05f;
    laser.setlidaropt(LidarPropMinRange, &f_optvalue, sizeof(float));
    laser.setlidaropt(LidarPropScanFrequency, &frequency, sizeof(float));

    // 3. 禁用噪声过滤（可选）
    laser.enableGlassNoise(false);
    laser.enableSunNoise(false);

    // 4. 初始化雷达
    bool ret = laser.initialize();
    if (!ret) {
        fprintf(stderr, "Fail to initialize: %s\n", laser.DescribeError());
        return -1;
    }

    // 5. 获取俯仰角（仅森合雷达支持）
    float pitch = 0.0f;
    if (!laser.getPitchAngle(pitch)) {
        fprintf(stderr, "Fail to get pitch angle\n");
    } else {
        printf("Pitch angle: %.02f°\n", pitch);
    }

    // 6. 启动扫描
    ret = laser.turnOn();
    if (!ret) {
        fprintf(stderr, "Fail to start: %s\n", laser.DescribeError());
        return -1;
    }

    // 7. OpenCV 可视化窗口
    const int WINDOW_SIZE = 800;
    cv::namedWindow("Lidar Point Cloud", cv::WINDOW_AUTOSIZE);
    cv::Mat pointCloudImg(WINDOW_SIZE, WINDOW_SIZE, CV_8UC3, cv::Scalar(0, 0, 0));

    // 8. 主循环：获取数据并显示
    LaserScan scan;
    while (ydlidar::os_isOk()) {
    if (laser.doProcessSimple(scan)) {
        // 8.1 清空画布
        pointCloudImg.setTo(cv::Scalar(0, 0, 0));

        // 8.2 绘制坐标轴（红色 X 轴，绿色 Y 轴）
        cv::line(pointCloudImg, cv::Point(WINDOW_SIZE/2, 0), cv::Point(WINDOW_SIZE/2, WINDOW_SIZE), cv::Scalar(0, 0, 255), 1);
        cv::line(pointCloudImg, cv::Point(0, WINDOW_SIZE/2), cv::Point(WINDOW_SIZE, WINDOW_SIZE/2), cv::Scalar(0, 255, 0), 1);

        // 8.3 绘制点云（调整缩放比例，使点云更清晰）
        float scale = 50.0f;  // 缩放比例（可调整）
        float offset = WINDOW_SIZE / 2.0f;

        for (size_t i = 0; i < scan.points.size(); ++i) {
            const LaserPoint &p = scan.points.at(i);
            float x = p.range * cos(p.angle);
            float y = p.range * sin(p.angle);
            
            // 调整缩放比例
            int imgX = static_cast<int>(x * scale + offset);
            int imgY = static_cast<int>(-y * scale + offset);
            
            // 检查点是否在窗口范围内
            if (imgX >= 0 && imgX < WINDOW_SIZE && imgY >= 0 && imgY < WINDOW_SIZE) {
                // 设置点的大小（5 像素）和颜色（绿色）
                cv::circle(pointCloudImg, cv::Point(imgX, imgY), 1, cv::Scalar(0, 255, 0), -1);
            }
        }

        // 8.4 显示图像
        cv::imshow("Lidar Point Cloud", pointCloudImg);
        if (cv::waitKey(10) == 27) break; // ESC 退出
    } else {
        fprintf(stderr, "Failed to get Lidar Data\n");
    }
}

    // 9. 关闭雷达
    laser.turnOff();
    laser.disconnecting();
    cv::destroyAllWindows();

    return 0;
}

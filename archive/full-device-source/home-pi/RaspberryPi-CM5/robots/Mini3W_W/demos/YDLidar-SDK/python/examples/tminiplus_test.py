import os
import ydlidar
import time
import cv2
import numpy as np
import math

def main():
    # 初始化操作系统
    print("Initializing LiDAR...")
    ydlidar.os_init()
    
    # 1. 自动检测雷达端口
    ports = ydlidar.lidarPortList()
    port = ""
    
    if not ports:
        # 没有检测到雷达端口
        print("No LiDAR ports detected.")
        port = input("Please enter the LiDAR serial port: ")
    elif len(ports) == 1:
        # 只有一个端口，自动选择
        port = list(ports.values())[0]
        print(f"Auto-selected LiDAR port: {port}")
    else:
        # 多个端口，让用户选择
        print("Detected LiDAR ports:")
        port_list = list(ports.values())
        for i, port_value in enumerate(port_list):
            print(f"[{i}] {port_value}")
        
        while True:
            try:
                selection = int(input("Please select the LiDAR port number: "))
                if 0 <= selection < len(port_list):
                    port = port_list[selection]
                    print(f"Selected LiDAR port: {port}")
                    break
                else:
                    print("Invalid selection. Please try again.")
            except ValueError:
                print("Please enter a valid number.")
    
    # 2. 配置雷达参数
    baudrate = 230400
    isSingleChannel = False
    frequency = 10.0
    
    laser = ydlidar.CYdLidar()
    
    # 2.1 字符串参数
    laser.setlidaropt(ydlidar.LidarPropSerialPort, port)
    
    # 忽略数组 - 在Python SDK中传递空字符串
    ignore_array = ""
    laser.setlidaropt(ydlidar.LidarPropIgnoreArray, ignore_array)
    
    # 2.2 整数参数
    laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, baudrate)
    laser.setlidaropt(ydlidar.LidarPropLidarType, ydlidar.TYPE_TRIANGLE)  # Tmini Pro/Plus雷达类型
    laser.setlidaropt(ydlidar.LidarPropDeviceType, ydlidar.YDLIDAR_TYPE_SERIAL)
    laser.setlidaropt(ydlidar.LidarPropSampleRate, 4)  # 采样率 (False: 4, True: 3)
    laser.setlidaropt(ydlidar.LidarPropIntenstiyBit, 8)  # 强度位数
    
    # 2.3 布尔参数
    laser.setlidaropt(ydlidar.LidarPropFixedResolution, True)
    laser.setlidaropt(ydlidar.LidarPropReversion, False)
    laser.setlidaropt(ydlidar.LidarPropInverted, False)
    laser.setlidaropt(ydlidar.LidarPropAutoReconnect, True)
    laser.setlidaropt(ydlidar.LidarPropSingleChannel, isSingleChannel)
    laser.setlidaropt(ydlidar.LidarPropIntenstiy, True)
    laser.setlidaropt(ydlidar.LidarPropSupportMotorDtrCtrl, False)
    laser.setlidaropt(ydlidar.LidarPropSupportHeartBeat, False)
    
    # 2.4 浮点参数
    laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
    laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)
    laser.setlidaropt(ydlidar.LidarPropMaxRange, 64.0)
    laser.setlidaropt(ydlidar.LidarPropMinRange, 0.05)
    laser.setlidaropt(ydlidar.LidarPropScanFrequency, frequency)
    
    # 3. 禁用噪声过滤
    # Python SDK中可能有不同的方法名称，尝试使用等效方法
    try:
        # 尝试使用C++风格的方法
        laser.enableGlassNoise(False)
        laser.enableSunNoise(False)
    except AttributeError:
        try:
            # 尝试使用Python SDK的替代方法
            laser.setGlassNoise(False)
            laser.setSunNoise(False)
        except AttributeError:
            print("Warning: Noise filtering methods not available in Python SDK")
    
    # 4. 初始化雷达
    ret = laser.initialize()
    if not ret:
        print(f"Failed to initialize LiDAR: {laser.DescribeError()}")
        return
    

    
    # 6. 启动扫描
    ret = laser.turnOn()
    if not ret:
        print(f"Failed to start scanning: {laser.DescribeError()}")
        laser.disconnecting()
        return
    
    # 7. OpenCV 可视化窗口
    WINDOW_SIZE = 800
    window_name = "LiDAR Point Cloud"
    cv2.namedWindow(window_name, cv2.WINDOW_AUTOSIZE)
    
    # 8. 主循环：获取数据并显示
    print("Starting LiDAR visualization. Press ESC to exit.")
    
    try:
        while ydlidar.os_isOk():
            # 创建新的扫描对象
            scan = ydlidar.LaserScan()
            
            # 获取扫描数据
            if laser.doProcessSimple(scan):
                # 8.1 创建黑色画布
                point_cloud_img = np.zeros((WINDOW_SIZE, WINDOW_SIZE, 3), dtype=np.uint8)
                
                # 8.2 绘制坐标轴（红色X轴，绿色Y轴）
                # X轴 (红色)
                cv2.line(point_cloud_img, 
                         (WINDOW_SIZE//2, 0), 
                         (WINDOW_SIZE//2, WINDOW_SIZE), 
                         (0, 0, 255), 1)
                # Y轴 (绿色)
                cv2.line(point_cloud_img, 
                         (0, WINDOW_SIZE//2), 
                         (WINDOW_SIZE, WINDOW_SIZE//2), 
                         (0, 255, 0), 1)
                
                # 8.3 绘制点云（调整缩放比例，使点云更清晰）
                scale = 50.0  # 与C++相同的缩放比例
                offset = WINDOW_SIZE // 2
                
                for point in scan.points:
                    # 跳过无效点
                    if point.range <= 0:
                        continue
                    
                    # 与C++完全相同的坐标转换
                    x = point.range * math.cos(point.angle)
                    y = point.range * math.sin(point.angle)
                    
                    # 转换为图像坐标（与C++相同）
                    imgX = int(x * scale + offset)
                    imgY = int(-y * scale + offset)  # 反转Y轴
                    
                    # 检查点是否在窗口范围内（与C++相同）
                    if 0 <= imgX < WINDOW_SIZE and 0 <= imgY < WINDOW_SIZE:
                        # 绘制绿色点（与C++相同）
                        cv2.circle(point_cloud_img, (imgX, imgY), 1, (0, 255, 0), -1)
                
                # 8.4 显示图像
                cv2.imshow(window_name, point_cloud_img)
                
                # ESC键退出（与C++相同）
                key = cv2.waitKey(10)
                if key == 27:  # 27是ESC键的ASCII码
                    break
            else:
                print("Failed to get LiDAR data")
                time.sleep(0.05)
    except KeyboardInterrupt:
        print("Program interrupted by user")
    finally:
        # 9. 关闭雷达
        print("Turning off LiDAR...")
        laser.turnOff()
        laser.disconnecting()
        cv2.destroyAllWindows()
        print("LiDAR disconnected. Program exited.")

if __name__ == "__main__":
    main()

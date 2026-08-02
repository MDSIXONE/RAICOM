#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
二维雷达显示程序
在SPI屏幕上显示雷达扫描数据
通过串口接收雷达数据，按B键退出
"""

import sys,os,time,threading,math
sys.path.append('/home/pi/RaspberryPi-CM5/robots/Dog_LM/demos/YDLidar-SDK/build/python')
import ydlidar
from PIL import Image, ImageDraw, ImageFont
from xgoscreen.LCD_2inch import LCD_2inch
from pathlib import Path

p = Path(__file__).resolve()
    
from uiutils import Button,language

la=language()
class RadarDisplay:
    def __init__(self):
        self.screen_width = 320
        self.screen_height = 240
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
        self.max_display_range = 5.0 
        

        try:
            print("正在初始化LCD屏幕...")
            self.lcd = LCD_2inch()
            self.lcd.Init()
            print("LCD屏幕初始化成功")
        except Exception as e:
            print(f"LCD初始化失败: {e}")
            import traceback
            traceback.print_exc()
            raise
        

        try:
            self.button = Button()
            print("按键初始化成功")
        except Exception as e:
            print(f"按键初始化失败: {e}")
            self.button = None
        
        self.radar_points = []
        self.running = True
        
        self.laser = None
        self.radar_connected = False 
        
        self.init_radar()
        
        print("雷达显示系统初始化完成")
    
    def get_distance_color(self, distance):
        """根据距离返回颜色 (R, G, B)"""
        if distance < 1.5:
            return (255, 0, 0)    # 红色 - 近距离
        elif distance < 3.0:
            return (255, 255, 0)  # 黄色 - 中距离
        else:
            return (0, 255, 0)    # 绿色 - 远距离
    
    def polar_to_cartesian(self, distance, angle):
        """极坐标转笛卡尔坐标"""
        angle_rad = math.radians(angle)
        
        x = distance * math.cos(angle_rad)
        y = distance * math.sin(angle_rad)
        
        screen_x = int(self.center_x + (x / self.max_display_range) * (self.screen_width / 2 - 20))
        screen_y = int(self.center_y - (y / self.max_display_range) * (self.screen_height / 2 - 20))
        
        return screen_x, screen_y
    
    def draw_coordinate_system(self, draw):
        """绘制坐标系统"""
        for i in range(1, 6):
            radius = int((i * min(self.screen_width, self.screen_height) / 2 - 20) / 5)
            draw.ellipse([
                self.center_x - radius, self.center_y - radius,
                self.center_x + radius, self.center_y + radius
            ], outline=(128, 128, 128), width=1)
            
            distance_label = f"{i}m"
            draw.text((self.center_x + radius - 15, self.center_y - 8), 
                     distance_label, fill=(255, 255, 255))
        

        draw.line([(0, self.center_y), (self.screen_width, self.center_y)], 
                 fill=(100, 100, 100), width=1)

        draw.line([(self.center_x, 0), (self.center_x, self.screen_height)], 
                 fill=(100, 100, 100), width=1)
        

        for angle in range(0, 360, 30):
            angle_rad = math.radians(angle)
            end_x = self.center_x + int((self.screen_width / 2 - 20) * math.cos(angle_rad))
            end_y = self.center_y - int((self.screen_height / 2 - 20) * math.sin(angle_rad))
            draw.line([(self.center_x, self.center_y), (end_x, end_y)], 
                     fill=(64, 64, 64), width=1)
        

        draw.ellipse([
            self.center_x - 3, self.center_y - 3,
            self.center_x + 3, self.center_y + 3
        ], fill=(255, 0, 0), outline=(255, 0, 0))
    
    def draw_radar_points(self, draw):
        """绘制雷达点"""
        for point in self.radar_points:
            distance, angle = point
            
            if distance > self.max_display_range:
                continue
            
            screen_x, screen_y = self.polar_to_cartesian(distance, angle)
            
            if 0 <= screen_x < self.screen_width and 0 <= screen_y < self.screen_height:
                color = self.get_distance_color(distance)
                
                # 绘制点
                draw.ellipse([
                    screen_x - 1, screen_y - 1,
                    screen_x + 1, screen_y + 1
                ], fill=color, outline=color)
    
    def init_radar(self):
        """初始化雷达"""
        try:
            print("正在初始化雷达...")

            ydlidar.os_init()
            
            port = "/dev/ttyUSB0"
            print(f"使用指定雷达端口: {port}")
            
            self.laser = ydlidar.CYdLidar()
            
            # 配置雷达参数 
            baudrate = 230400
            isSingleChannel = False
            frequency = 10.0
            
            self.laser.setlidaropt(ydlidar.LidarPropSerialPort, port)
            ignore_array = ""
            self.laser.setlidaropt(ydlidar.LidarPropIgnoreArray, ignore_array)
            
            self.laser.setlidaropt(ydlidar.LidarPropSerialBaudrate, baudrate)
            self.laser.setlidaropt(ydlidar.LidarPropLidarType, ydlidar.TYPE_TRIANGLE)
            self.laser.setlidaropt(ydlidar.LidarPropDeviceType, ydlidar.YDLIDAR_TYPE_SERIAL)
            self.laser.setlidaropt(ydlidar.LidarPropSampleRate, 4)
            self.laser.setlidaropt(ydlidar.LidarPropIntenstiyBit, 8)
            

            self.laser.setlidaropt(ydlidar.LidarPropFixedResolution, True)
            self.laser.setlidaropt(ydlidar.LidarPropReversion, False)
            self.laser.setlidaropt(ydlidar.LidarPropInverted, False)
            self.laser.setlidaropt(ydlidar.LidarPropAutoReconnect, True)
            self.laser.setlidaropt(ydlidar.LidarPropSingleChannel, isSingleChannel)
            self.laser.setlidaropt(ydlidar.LidarPropIntenstiy, True)
            self.laser.setlidaropt(ydlidar.LidarPropSupportMotorDtrCtrl, False)
            self.laser.setlidaropt(ydlidar.LidarPropSupportHeartBeat, False)
            
            self.laser.setlidaropt(ydlidar.LidarPropMaxAngle, 180.0)
            self.laser.setlidaropt(ydlidar.LidarPropMinAngle, -180.0)
            self.laser.setlidaropt(ydlidar.LidarPropMaxRange, 64.0)
            self.laser.setlidaropt(ydlidar.LidarPropMinRange, 0.05)
            self.laser.setlidaropt(ydlidar.LidarPropScanFrequency, frequency)
            
            # 禁用噪声过滤
            try:
                self.laser.enableGlassNoise(False)
                self.laser.enableSunNoise(False)
            except AttributeError:
                try:
                    self.laser.setGlassNoise(False)
                    self.laser.setSunNoise(False)
                except AttributeError:
                    print("警告: 噪声过滤方法在Python SDK中不可用")
            
            ret = self.laser.initialize()
            if not ret:
                print(f"雷达初始化失败: {self.laser.DescribeError()}")
                self.laser = None
                self.radar_connected = False
                return
            
            ret = self.laser.turnOn()
            if not ret:
                print(f"雷达启动扫描失败: {self.laser.DescribeError()}")
                self.laser.disconnecting()
                self.laser = None
                self.radar_connected = False
                return
            
            print("雷达初始化和启动成功")
            self.radar_connected = True  
                
        except Exception as e:
            print(f"雷达初始化错误: {e}")
            if self.laser:
                try:
                    self.laser.disconnecting()
                except:
                    pass
            self.laser = None
            self.radar_connected = False 
    
    def radar_reader_thread(self):
        """雷达数据读取线程"""
        if not self.laser:
            print("雷达未初始化，等待重连")
            return
            
        try:
            while self.running and ydlidar.os_isOk():
                try:
                    
                    scan = ydlidar.LaserScan()
                    
                 
                    if self.laser.doProcessSimple(scan):
                       
                        self.radar_points.clear()
                        
                     
                        for point in scan.points:
                          
                            if point.range <= 0:
                                continue
                                
                            angle_deg = math.degrees(point.angle)
                            distance = point.range
                            
                           
                            if 0.05 <= distance <= self.max_display_range:
                                self.radar_points.append((distance, angle_deg))
                    else:
                        print("获取雷达数据失败")
                        time.sleep(0.05)
                    
                    time.sleep(0.01) 
                    
                except Exception as e:
                    print(f"雷达数据读取错误: {e}")
                    time.sleep(0.1)
                    
        except Exception as e:
            print(f"雷达线程错误: {e}")
            self.running = False
    

    
    def update_display(self):
        """更新显示"""
        try:
            image = Image.new('RGB', (self.screen_width, self.screen_height), (0, 0, 0))
            draw = ImageDraw.Draw(image)
            
            
            if not self.radar_connected:
              
                try:
                    font = ImageFont.truetype("/home/pi/RaspberryPi-CM5/common/model/msyh.ttc", 24)
                except:
                    font = ImageFont.load_default()
                if la=="cn":
                  text = "雷达未连接"
                else:
                  text = "Lidar not connected"
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                text_x = (self.screen_width - text_width) // 2
                text_y = (self.screen_height - text_height) // 2
                
                

                draw.text((text_x, text_y), text, fill=(255, 255, 255), font=font)
                
            else:

                self.draw_coordinate_system(draw)
                
           
                self.draw_radar_points(draw)
                
                info_text = f"Points: {len(self.radar_points)} Range: {self.max_display_range}m"
                draw.text((5, 5), info_text, fill=(255, 255, 255))
            
        
            self.lcd.ShowImage(image)
            
        except Exception as e:
            print(f"显示更新错误: {e}")
            import traceback
            traceback.print_exc()
    
    def run(self):
        """主运行循环"""
        print("雷达显示程序启动")
        print("按B键退出程序")
        

        radar_thread = threading.Thread(target=self.radar_reader_thread)
        radar_thread.daemon = True
        radar_thread.start()
        
        try:
            while self.running:

                if self.button.press_b():
                    print("检测到B键按下，退出程序")
                    self.running = False
                    break
                

                self.update_display()
                

                time.sleep(0.05)  # 20 FPS
                
        except KeyboardInterrupt:
            print("\n程序被中断")
        
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源"""
        print("正在清理资源...")
        self.running = False
        
        if self.laser:
            try:
                print("正在关闭雷达...")
                self.laser.turnOff()
                self.laser.disconnecting()
                print("雷达已关闭")
            except Exception as e:
                print(f"关闭雷达时出错: {e}")
        
        
        print("资源清理完成")

def main():
    """主函数"""
    try:
        radar = RadarDisplay()
        radar.run()
    except Exception as e:
        print(f"程序运行错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
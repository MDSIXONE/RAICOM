import argparse
import time
import logging
import sys
import signal
import subprocess  # 新增
import requests  # 新增网络检测
import threading  # 新增线程支持
import os
from src.application import Application
from src.utils.logging_config import get_logger
from uiutils import language,Button
from PIL import Image, ImageDraw, ImageFont
import xgoscreen.LCD_2inch as LCD_2inch
splash_theme_color = (15, 21, 46)
SPLASH_COLOR = (15, 21, 46)  
TEST_NETWORK_URL = "http://www.baidu.com"  
la=language()

#version=2.0

# Display Init
display = LCD_2inch.LCD_2inch()
display.clear()
if la=="cn":
  background_image_path = "/home/pi/RaspberryPi-CM5/robots/Rider_R/demos/xiaozhi_test/src/xiaozhi_cn.png" 
else:
  background_image_path = "/home/pi/RaspberryPi-CM5/robots/Rider_R/demos/xiaozhi_test/src/xiaozhi_en.png"  

splash = Image.open(background_image_path)
draw = ImageDraw.Draw(splash)
text_color = (255, 255, 255)
color = (102, 178, 255)
gray_color = (128, 128, 128)
rectangle_x = (display.width - 120) // 2  
rectangle_y = 50  
rectangle_width = 200
rectangle_height = 30
draw.rectangle((rectangle_x, rectangle_y, rectangle_x + rectangle_width, rectangle_y + rectangle_height), fill=color)
font2 = ImageFont.truetype("/home/pi/RaspberryPi-CM5/common/model/msyh.ttc", 16)
if la=="cn":
  draw.text((rectangle_x + 70, rectangle_y + 5), '启动中...', fill=text_color, font=font2)
else:
  draw.text((rectangle_x + 50, rectangle_y + 5), 'Starting up...', fill=text_color, font=font2)
display.ShowImage(splash)

# 加载无网络图片
try:
    nowifi_image_path = "/home/pi/RaspberryPi-CM5/common/pics/offline.png"
    wifi_img = Image.open(nowifi_image_path)
    nowifi_image = Image.new("RGB", wifi_img.size, SPLASH_COLOR)
    nowifi_image.paste(wifi_img, (0, 0), wifi_img)
except Exception as e:
    print(f"加载图片失败: {e}")
    nowifi_image = Image.new('RGB', (100, 100), color=(255, 0, 0))

logger = get_logger(__name__)

# 全局按键检测线程控制
button_thread_running = True
button = Button()

def start_button_thread():
    """启动独立的按键检测线程"""
    def check_button():
        global button_thread_running
        while button_thread_running:
            if button.press_b():
                try:
                    print("B键按下, 退出程序")
                    start_pulseaudio()  # 恢复音频服务
                    os._exit(0)
                except Exception as e:
                    logger.error(f"退出时出错: {e}")
                    os._exit(1)
            time.sleep(0.1)
    
    thread = threading.Thread(target=check_button, daemon=True)
    thread.start()
    logger.info("按键检测线程已启动")
'''
def kill_pulseaudio():
    """关闭 PulseAudio 服务"""
    try:
        subprocess.run(["pulseaudio", "--kill"], check=True)
        logger.info("已关闭 PulseAudio")
    except subprocess.CalledProcessError as e:
        logger.warning(f"关闭 PulseAudio 失败: {e}")
'''
def kill_pulseaudio():
    try:
        result = subprocess.run(["pgrep", "-x", "pulseaudio"], capture_output=True, text=True)
        
        if result.returncode == 0:
            try:
                subprocess.run(["pulseaudio", "--kill"], check=True, timeout=5)
                logger.info("已正常关闭 PulseAudio")
            except subprocess.TimeoutExpired:
                subprocess.run(["pkill", "-9", "-x", "pulseaudio"])
                logger.warning("强制终止 PulseAudio")
            except Exception as e:
                logger.warning(f"关闭 PulseAudio 时出错: {e}")
                return False
            
            time.sleep(1)
            check_result = subprocess.run(["pgrep", "-x", "pulseaudio"], stdout=subprocess.DEVNULL)
            if check_result.returncode == 0:
                logger.error("PulseAudio 仍然在运行")
                return False
            
            return True
        else:
            logger.info("PulseAudio 没有运行")
            return True
            
    except Exception as e:
        logger.error(f"检查/关闭 PulseAudio 时发生异常: {e}")
        return False

def check_network():
    """检查网络连接状态"""
    max_attempts = 5
    attempt = 0
    color_white = (255, 255, 255)
    
    while attempt < max_attempts:
        try:
            requests.get(TEST_NETWORK_URL, timeout=1)
            print("Net is connected")
            return True 
        except:
            print(f"Network connection attempt {attempt + 1} failed")
            attempt += 1
            time.sleep(1)
    
    print("Network connection failed after 5 attempts")
    # 显示无网络提示
    while True:
        try:
            # 重新创建splash和draw对象
            network_splash = Image.new("RGB", (display.height, display.width), SPLASH_COLOR)
            network_draw = ImageDraw.Draw(network_splash)
            
            # 显示无网络图片
            img_width, img_height = nowifi_image.size
            x_pos = (display.height - img_width) // 2
            y_pos = 40
            network_splash.paste(nowifi_image, (x_pos, y_pos))
            
            # 显示文字提示
            if la == "cn":
                text = "WIFI未连接或无网络"
            else:
                text = "WIFI is not connected"
            text_width = network_draw.textlength(text, font=font2)
            x_position = (display.height - text_width) // 2
            network_draw.text((x_position, 170), text, fill=color_white, font=font2)
            display.ShowImage(network_splash)
            
            # 再次尝试网络连接
            time.sleep(2)
            try:
                requests.get(TEST_NETWORK_URL, timeout=1)
                print("Network connection restored")
                return True
            except:
                continue
                
        except KeyboardInterrupt:
            # 处理Ctrl+C中断信号
            print("\n用户中断，正在退出...")
            start_pulseaudio()  # 恢复音频服务
            sys.exit(0)
        except Exception as e:
            logger.error(f"显示无网络提示时出错: {e}")
            time.sleep(2)
            continue

def start_pulseaudio():
    try:
        # 先尝试正常关闭
        subprocess.run(["pulseaudio", "--kill"], check=True)
        time.sleep(1)  
        
        # 检查是否真的关闭
        result = subprocess.run(["pgrep", "-x", "pulseaudio"], stdout=subprocess.DEVNULL)
        if result.returncode == 0:
            subprocess.run(["pkill", "-9", "-x", "pulseaudio"])  
        
        # 重新启动 PulseAudio
        subprocess.run(["pulseaudio", "--start"], check=True)
        time.sleep(2)  
        return True
    except Exception as e:
        print(f"重启 PulseAudio 失败: {e}")
        return False

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    logger.info("接收到中断信号，正在关闭...")
    app = Application.get_instance()
    app.shutdown()
    start_pulseaudio()  
    sys.exit(0)

def main():
    """程序入口点"""
    signal.signal(signal.SIGINT, signal_handler)
    
    # 启动按键检测线程
    start_button_thread()
    
    kill_pulseaudio() 
    
    if not check_network():
        logger.error("网络连接失败，程序退出")
        return 1

    try:
        app = Application.get_instance()
        logger.info("应用程序已启动，按 Ctrl+C 退出")
        app.run()
    except Exception as e:
        logger.error(f"程序发生错误: {e}", exc_info=True)
        start_pulseaudio()  
        return 1
    finally:
        start_pulseaudio()  

    return 0

if __name__ == "__main__":
    sys.exit(main())

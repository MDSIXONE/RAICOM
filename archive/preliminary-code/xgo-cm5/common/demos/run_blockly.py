#!/usr/bin/env python3

import os
import sys
import socket
import fcntl
import struct
import threading
import subprocess
import time
import signal
from PIL import Image
from uiutils import lcd_rect, display_cjk_string, draw, display, splash, font2, color_white, color_bg, Button,get_path
language_ini_path = get_path("language_ini_path")

# --- 端口检测辅助函数 ---
def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """检测端口是否已被占用（不修改端口，仅检测）。"""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.5)
            return s.connect_ex((host, port)) == 0
    except Exception:
        # 若检测异常，保守返回占用，避免继续启动导致错误
        return True

def describe_port_occupants_linux(port: int) -> str:
    """尝试使用 ss 列出占用端口的进程信息（Linux）。"""
    try:
        result = subprocess.run(["ss", "-ltnp"], capture_output=True, text=True)
        lines = []
        for line in result.stdout.splitlines():
            if f":{port} " in line:
                lines.append(line.strip())
        return "\n".join(lines) if lines else ""
    except Exception:
        return ""
def get_ip_address(ifname):
    """
    获取指定网络接口的IP地址
    """
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ip = socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
        return ip
    except:
        return None

def get_local_ip():
    """
    获取本地IP地址
    """
    # 尝试获取wlan0接口的IP
    for iface in ['wlan0', 'eth0']:
        try:
            ip = get_ip_address(iface)
            if ip:
                return ip
        except:
            continue
    
    # 如果获取不到，返回默认值
    return "127.0.0.1"

def display_access_info(ip, port=8000):
    """
    在LCD屏幕上显示访问信息
    """
    # 清空整个屏幕
    lcd_rect(0, 0, 320, 240, color=color_bg, thickness=-1)
    
    # 获取脚本所在目录
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 加载并显示图片
    try:
        # 构建图片文件路径
        ai_icon_path = os.path.join(script_dir, "/home/pi/RaspberryPi-CM5/common/pics", "icon_ai.png")
        blockly_icon_path = os.path.join(script_dir, "/home/pi/RaspberryPi-CM5/common/pics", "icon_blockly.png")
        wifi_icon_path = os.path.join(script_dir, "/home/pi/RaspberryPi-CM5/common/pics", "wifi@2x.jpg")
        
        # 检查文件是否存在
        if os.path.exists(ai_icon_path) and os.path.exists(blockly_icon_path):
            # 加载AI图标
            ai_icon = Image.open(ai_icon_path)
            # 调整图片大小
            ai_icon = ai_icon.resize((60, 60))
            # 在屏幕上显示AI图标 (左侧)
            splash.paste(ai_icon, (170, 40))
            
            # 加载Blockly图标
            blockly_icon = Image.open(blockly_icon_path)
            # 调整图片大小
            blockly_icon = blockly_icon.resize((60, 60))
            # 在屏幕上显示Blockly图标 (右侧)
            splash.paste(blockly_icon, (90, 40))
        else:
            print("图片文件未找到，请检查 pics 目录下的图片文件")
            
        # 加载并显示WiFi图标
        if os.path.exists(wifi_icon_path):
            # 加载WiFi图标
            wifi_icon = Image.open(wifi_icon_path)
            # 调整图片大小
            wifi_icon = wifi_icon.resize((30, 26))
            # 在屏幕上显示WiFi图标 (在IP地址和端口号文字的前面/左侧)
            splash.paste(wifi_icon, (26, 160))
        else:
            print("WiFi图标文件未找到，请检查 pics 目录下的 wifi@2x.jpg 文件")
    except Exception as e:
        print(f"加载图片时出错: {e}")
    
    # 显示IP地址和端口号
    display_cjk_string(
        draw,
        60,
        160,
        f"{ip}:{port}",
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )
    
    display.ShowImage(splash)
    
def restart_application():
    os.system("python /home/pi/RaspberryPi-CM5/common/kill.py")
    os._exit(0)  
    
class GracefulBlocklyService:
    """
    优雅的Blockly服务管理器
    """
    def __init__(self):
        self.process = None
        self.is_running = False
        
    def start_service(self):
        """
        启动Blockly服务（使用独立虚拟环境，不影响当前环境）
        """
        try:
            # xgo-blockly虚拟环境路径（根据项目配置）
            xgo_venv_path = "/home/pi/RaspberryPi-CM5/blocklyvenv"
            python_exe = f"{xgo_venv_path}/bin/python"
            
            # 检查虚拟环境是否存在
            if not os.path.exists(python_exe):
                print(f"错误: 虚拟环境不存在 {python_exe}")
                print("请确保已在正确路径安装xgo-blockly")
                self.is_running = False
                return
            
            # 验证xgo-blockly是否已安装
            check_cmd = [python_exe, "-c", "import xgo_blockly; print('xgo-blockly已安装')"]
            try:
                result = subprocess.run(check_cmd, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    print(f"错误: xgo-blockly未在虚拟环境中安装")
                    print(f"请在 {xgo_venv_path} 环境中执行: pip install xgo-blockly")
                    self.is_running = False
                    return
                else:
                    print("验证通过: xgo-blockly已正确安装")
            except subprocess.TimeoutExpired:
                print("警告: 验证超时，但继续尝试启动服务")
            except Exception as e:
                print(f"验证时出错: {e}，但继续尝试启动服务")
            
            print(f"正在使用虚拟环境启动xgo-blockly: {xgo_venv_path}")
            
            # 直接使用虚拟环境的Python解释器启动xgo-blockly
            # 这样完全不影响当前进程的环境
            # 清理环境中的 FLASK_ENV，避免弃用警告；设置 FLASK_DEBUG（若由 Flask 使用则生效）
            child_env = os.environ.copy()
            child_env.pop("FLASK_ENV", None)
            child_env.setdefault("FLASK_DEBUG", "1")

            self.process = subprocess.Popen(
                [python_exe, "-m", "xgo_blockly.cli"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=child_env
            )
            
            self.is_running = True
            print(f"Blockly服务已启动 PID: {self.process.pid}")
            print(f"使用Python解释器: {python_exe}")
            
            # 等待进程结束
            return_code = self.process.wait()
            self.is_running = False
            
            if return_code != 0:
                stderr_output = self.process.stderr.read() if self.process.stderr else ""
                print(f"服务异常退出，返回码: {return_code}")
                if stderr_output:
                    print(f"错误信息: {stderr_output}")
            else:
                print("服务正常退出")
            
        except FileNotFoundError as e:
            print(f"错误: 找不到Python解释器或xgo-blockly模块: {e}")
            print(f"请检查虚拟环境路径: {xgo_venv_path}")
            self.is_running = False
        except Exception as e:
            print(f"启动Blockly服务时出错: {e}")
            self.is_running = False
    
    def stop_service(self):
        """
        优雅地停止Blockly服务
        """
        if not self.process or not self.is_running:
            print("服务未运行")
            return True
        
        try:
            print("正在停止Blockly服务...")
            
            # 方法1: 发送SIGTERM信号，给进程优雅退出的机会
            self.process.send_signal(signal.SIGTERM)
            
            # 等待最多5秒让进程自己退出
            try:
                self.process.wait(timeout=5)
                print("服务已优雅停止")
                self.is_running = False
                return True
            except subprocess.TimeoutExpired:
                print("服务未在5秒内响应SIGTERM，尝试强制终止...")
                
                # 方法2: 如果还没退出，发送SIGKILL强制终止
                self.process.kill()
                self.process.wait(timeout=2)
                print("服务已强制停止")
                self.is_running = False
                return True
                
        except ProcessLookupError:
            # 进程已经不存在了
            print("进程已经结束")
            self.is_running = False
            return True
        except Exception as e:
            print(f"停止服务时出错: {e}")
            return False
    
    def is_service_running(self):
        """
        检查服务是否正在运行
        """
        if not self.process:
            return False
        
        # 检查进程是否还在运行
        poll_result = self.process.poll()
        if poll_result is not None:
            self.is_running = False
            return False
        
        return self.is_running

def verify_current_environment():
    """
    验证当前环境不受影响
    """
    print("=== 当前环境验证 ===")
    print(f"当前Python路径: {sys.executable}")
    print(f"当前VIRTUAL_ENV: {os.environ.get('VIRTUAL_ENV', '未设置')}")
    print(f"当前工作目录: {os.getcwd()}")
    print("===================")

def main():
    # 验证当前环境
    verify_current_environment()
    
    # 初始化按钮
    button = Button()
    
    # 创建服务管理器
    service_manager = GracefulBlocklyService()
    
    # 获取本地IP地址
    local_ip = get_local_ip()
    print(f"Local IP: {local_ip}")
    
    # 显示访问信息
    display_access_info(local_ip, 8000)

    # 在启动服务前检查端口占用（不改端口，等待释放）
    target_port = 8000
    if port_in_use(target_port):
        print(f"端口 {target_port} 已被占用，无法立即启动服务。")
        info = describe_port_occupants_linux(target_port)
        if info:
            print("占用详情(来自 ss):\n" + info)
        print("请释放该端口。例如：sudo fuser -n tcp -k 8000 或 sudo kill <PID>。")
        print("等待端口释放中……按B按钮退出。")
        # 初始化按钮（已创建）并等待端口释放
        while port_in_use(target_port):
            if button.press_b():
                restart_application()
                return
            time.sleep(1)
        print("检测到端口已释放，继续启动服务。")
    
    # 在后台线程中运行Blockly服务
    service_thread = threading.Thread(target=service_manager.start_service)
    service_thread.daemon = True
    service_thread.start()
    
    # 等待服务启动
    time.sleep(3)
    
    # 保持程序运行，直到用户按下B按钮
    print("服务运行中，按B按钮退出...")
    print("注意: xgo-blockly运行在独立虚拟环境中，不影响当前环境")
    
    while True:
        # 检查是否按下了B按钮（左下角）
        if button.press_b():
            restart_application()
            print("B按钮被按下，正在停止服务...")
            # 优雅地停止Blockly服务
            if service_manager.stop_service():
                break
            else:
                print("停止服务失败，强制退出...")
                break
        
        # 检查服务是否意外退出
        if not service_manager.is_service_running() and not service_thread.is_alive():
            print("服务意外退出")
            break
        
        # 短暂延迟以减少CPU使用率
        time.sleep(0.1)
    
    # 清理屏幕
    lcd_rect(0, 0, 320, 240, color=color_bg, thickness=-1)
    display.ShowImage(splash)
    print("程序已退出")
    
    # 最终验证当前环境未被影响
    print("\n=== 退出后环境验证 ===")
    verify_current_environment()

if __name__ == "__main__":
    main()
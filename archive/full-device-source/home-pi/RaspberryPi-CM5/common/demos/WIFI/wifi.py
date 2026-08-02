#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import time
import subprocess
import threading
import logging
import qrcode
import netifaces
import signal
import atexit
from flask import Flask, render_template_string, request, jsonify
from PIL import Image, ImageDraw, ImageFont
import io
import base64

# 延迟导入LCD硬件模块，避免在非树莓派环境下导入失败
LCD_2inch = None
def _import_lcd_module():
    try:
        import xgoscreen.LCD_2inch as LCD_2inch_mod
        return LCD_2inch_mod
    except Exception as e:
        logging.getLogger(__name__).info(f"LCD module not available: {e}")
        return None
from uiutils import Button, language, load_language, get_path

# 字体缓存系统
_font_cache = {}

def get_font(size, is_chinese=False):
    """获取字体，支持中英文字体缓存"""
    key = f"{size}_{is_chinese}"
    if key not in _font_cache:
        try:
            if is_chinese:
                _font_cache[key] = ImageFont.truetype("/home/pi/RaspberryPi-CM5/common/model/msyh.ttc", size)
            else:
                _font_cache[key] = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size)
        except:
            _font_cache[key] = ImageFont.load_default()
    return _font_cache[key]

# 文本改为从语言包加载（NETWORK_NEW）

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class WiFiHotspotManager:
    def __init__(self, config_file='config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.app = Flask(__name__)
        self.display = None
        self.button = None
        self.running = True
        self.current_language = 'en'  
        # 连接与热点抑制状态
        self.connecting_wifi = False
        self.suppress_hotspot_until = 0
        # 互联网探测与热点防抖计数
        self.internet_fail_streak = 0
        self.internet_success_streak = 0
        self.hotspot_started_at = 0
        self.hotspot_hold_seconds = 30  # 热点启动后至少保持 30s，避免频繁启停
        self.hotspot_retry_not_before = 0  # 下次允许尝试开启热点的时间戳
        self.hotspot_retry_backoff_seconds = 30  # 开启失败后的回退等待
        self.init_display()
        self.init_button()
        self.setup_routes()
        
        self.network_monitor_thread = None
        self.hotspot_active = False
        
        self.connection_stable_count = 0  
        self.connection_stable_threshold = 3 
        self.last_network_state = None  
        self.last_wifi_state = None  
        
        self.setup_exit_handlers()
    
    def setup_exit_handlers(self):
        """设置退出处理器，确保程序退出时关闭热点"""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.running = False
            self.cleanup()
            sys.exit(0)
        

        signal.signal(signal.SIGINT, signal_handler) 
        signal.signal(signal.SIGTERM, signal_handler)  
        

        atexit.register(self.cleanup)
        
    def init_button(self):
        """初始化按键控制"""
        try:
            detected_lang = language()
            if detected_lang:
                self.current_language = detected_lang
                logger.info(f"Language detected from config: {self.current_language}")
            else:
                self.current_language = 'cn' 
                logger.info("Language config not found, using default: cn")
            

            self.button = Button()
            logger.info("Button initialized successfully")
        except Exception as e:
            logger.error(f"Failed to detect language or initialize button: {e}")
            self.current_language = 'cn' 
            self.button = None
            
    def get_text(self, key):
        """根据当前语言从语言包读取文本（NETWORK_NEW）"""
        pack = load_language() or {}
        network_new = pack.get('NETWORK_NEW', {})
        return network_new.get(key, key)
    
    def has_internet_connection(self):
        """检测是否有网络连接"""
        import socket
        endpoints = [
            ("8.8.8.8", 53),
            ("1.1.1.1", 53),
            ("114.114.114.114", 53),
        ]
        for host, port in endpoints:
            try:
                socket.create_connection((host, port), timeout=2)
                return True
            except OSError:
                continue
            except Exception:
                continue
        return False
        
    def is_wifi_connected(self):
        """检测WiFi是否已连接"""
        try:
            result = subprocess.run(['iwgetid'], capture_output=True, text=True, timeout=5)
            return result.returncode == 0 and result.stdout.strip()
        except:
             return False

    def is_wifi_connecting(self):
        """检测WiFi是否处于连接中状态（NetworkManager device state）"""
        try:
            interface = self.config['hotspot']['interface']
            result = self.run_command(f"nmcli -t -f GENERAL.STATE device show {interface}", check=False)
            return 'connecting' in result.stdout.lower()
        except Exception:
            return False
    
    def network_monitor(self):
        """网络状态监控线程"""
        while self.running:
            try:
                has_internet = self.has_internet_connection()
                wifi_connected = self.is_wifi_connected()
                wifi_connecting = self.is_wifi_connecting()
                now = time.time()
                
                # 维护探测计数器
                if has_internet:
                    self.internet_success_streak += 1
                    self.internet_fail_streak = 0
                else:
                    self.internet_fail_streak += 1
                    self.internet_success_streak = 0

                if (self.last_network_state != has_internet or
                    self.last_wifi_state != wifi_connected):
                    logger.info(
                        f"Network state changed: Internet={has_internet}, WiFi={wifi_connected}, "
                        f"Connecting={wifi_connecting}, Hotspot={self.hotspot_active}"
                    )
                    self.last_network_state = has_internet
                    self.last_wifi_state = wifi_connected
                
                # Hotspot 已启动的情况下，加入保持时间窗口，避免频繁停止
                if self.hotspot_active:
                    if (now - self.hotspot_started_at) < self.hotspot_hold_seconds:
                        logger.info(
                            f"Hotspot hold window active ({int(now - self.hotspot_started_at)}/{self.hotspot_hold_seconds}s), skip stopping"
                        )
                    else:
                        if has_internet and wifi_connected:
                            self.connection_stable_count += 1
                            logger.info(f"Stable connection detected ({self.connection_stable_count}/{self.connection_stable_threshold})")
                            if self.connection_stable_count >= self.connection_stable_threshold:
                                logger.info("Network connection stable, stopping hotspot")
                                self.stop_hotspot()
                                self.hotspot_active = False
                                self.update_display("wifi_connected")
                                self.connection_stable_count = 0
                        else:
                            if self.connection_stable_count > 0:
                                logger.info("Network connection unstable, resetting stability counter")
                                self.connection_stable_count = 0
                else:
                    # 尚未开启热点的情况下，只有连续探测失败达到阈值才开启，加入连接抑制与回退
                    if not has_internet:
                        if self.connecting_wifi or wifi_connecting or (now < self.suppress_hotspot_until):
                            logger.info("WiFi connecting or suppression active, skip starting hotspot")
                        elif now < self.hotspot_retry_not_before:
                            logger.info("Hotspot retry backoff active, waiting before next start attempt")
                        elif self.internet_fail_streak >= 3:
                            logger.info("Internet probe failed consecutively, starting hotspot")
                            if self.start_hotspot():
                                self.hotspot_active = True
                                self.hotspot_started_at = now
                                self.update_display("hotspot")
                            else:
                                # 启动失败则加入回退期，避免循环尝试
                                self.hotspot_retry_not_before = now + self.hotspot_retry_backoff_seconds
                                logger.warning(
                                    f"Hotspot start failed; backoff {self.hotspot_retry_backoff_seconds}s before next attempt"
                                )
                    
                time.sleep(5)
                
            except Exception as e:
                logger.error(f"Network monitor error: {e}")

                self.connection_stable_count = 0
                time.sleep(5)
    
    def start_network_monitor(self):
        """启动网络监控线程"""
        if self.network_monitor_thread is None or not self.network_monitor_thread.is_alive():
            self.network_monitor_thread = threading.Thread(target=self.network_monitor, daemon=True)
            self.network_monitor_thread.start()
            logger.info("Network monitor started")
    
    def button_monitor(self):
        """按键监控线程"""
        if self.button is None:
            logger.info("Button monitoring disabled - button not initialized")
            return
            
        logger.info("Starting button monitoring...")
        
        while self.running:
            try:
               
                if self.button.press_b():
                    logger.info("B button pressed, shutting down...")
                    self.running = False
                    self.stop_hotspot() 
                    self.cleanup()
                    logger.info("Forcing exit...")
                    os._exit(0)  
                
                
                if self.button.press_c():  
                    logger.info("C button pressed, connecting to XGO2 network")
                    self.connect_to_xgo2()
                    
                time.sleep(0.05) 
            except Exception as e:
                logger.error(f"Button monitor error: {e}")
                time.sleep(0.5) 
    
    def start_button_monitor(self):
        """启动按键监控线程"""
        button_thread = threading.Thread(target=self.button_monitor, daemon=True)
        button_thread.start()
        logger.info("Button monitor started")
    
    def connect_to_xgo2(self):
        """连接到XGO2网络"""
        try:
            logger.info("Attempting to connect to XGO2 network...")
            self.update_display("wifi_connecting")
            

            success = self.connect_to_wifi("XGO2", "LuwuDynamics")
            
            if success:
                logger.info("Successfully connected to XGO2 network")
                self.update_display("wifi_connected")
             
                if self.hotspot_active:
                    self.stop_hotspot()
                    self.hotspot_active = False
            else:
                logger.error("Failed to connect to XGO2 network")
                self.update_display("connection_failed")
                
        except Exception as e:
            logger.error(f"Error connecting to XGO2: {e}")
            self.update_display("connection_failed")
    
    def load_config(self):
        default_config = {
            "hotspot": {
                "ssid": "RaspberryPi5-Setup",
                "password": "",  
                "interface": "wlan0",
                "channel": 6,
                "ip": "10.42.0.1",
                "dhcp_start": "10.42.0.10",
                "dhcp_end": "10.42.0.50"
            },
            "web_server": {
                "port": 5241,
                "host": "0.0.0.0"
            },
            "country": "CN"
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                for key, value in default_config.items():
                    if key not in config:
                        config[key] = value
                    elif isinstance(value, dict):
                        for subkey, subvalue in value.items():
                            if subkey not in config[key]:
                                config[key][subkey] = subvalue
                return config
            else:
                with open(self.config_file, 'w', encoding='utf-8') as f:
                    json.dump(default_config, f, indent=2, ensure_ascii=False)
                return default_config
        except Exception as e:
            logger.error(f"Failed to load config: {e}")
            return default_config
    
    def save_config(self):
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def init_display(self):
        try:
            display_config = self.config.get('display', {})
            if not display_config.get('enabled', True):
                logger.info("LCD display disabled")
                return
            
            lcd_mod = _import_lcd_module()
            if not lcd_mod:
                logger.info("Skipping LCD init; hardware module unavailable")
                self.display = None
                return
            self.display = lcd_mod.LCD_2inch()
            self.display.Init()
            logger.info("LCD 2inch display initialized successfully")
                
        except Exception as e:
            logger.error(f"Failed to initialize LCD display: {e}")
            self.display = None
    
    def show_startup_message(self):
        if not self.display:
            return
        
        try:
            img = Image.new('RGB', (320, 240), color='blue')
            draw = ImageDraw.Draw(img)
            
            is_chinese = self.current_language == 'cn'
            font = get_font(24, is_chinese)
            
            text = self.get_text('starting')
            draw.multiline_text((160, 120), text, font=font, fill='white', anchor='mm', align='center')
            self.display.ShowImage(img)
            
        except Exception as e:
            logger.error(f"Failed to show startup message: {e}")
    
    def run_command(self, command, check=True):
        try:
            logger.info(f"Executing command: {command}")
            result = subprocess.run(
                command, 
                shell=True, 
                capture_output=True, 
                text=True,
                timeout=30
            )
            
            if result.stdout:
                logger.info(f"Command output: {result.stdout.strip()}")
            if result.stderr:
                logger.warning(f"Command error: {result.stderr.strip()}")
                
            if check and result.returncode != 0:
                raise subprocess.CalledProcessError(result.returncode, command, result.stderr)
                
            return result
        except subprocess.TimeoutExpired:
            logger.error(f"Command timeout: {command}")
            raise
        except Exception as e:
            logger.error(f"Command failed: {command}, error: {e}")
            raise
    
    def is_hotspot_running(self):
        try:
            result = self.run_command("nmcli connection show --active", check=False)
            hotspot_name = f"Hotspot-{self.config['hotspot']['ssid']}"
            return hotspot_name in result.stdout
        except Exception as e:
            logger.error(f"Failed to check hotspot status: {e}")
            return False
    
    def stop_hotspot(self):
        try:
            logger.info("Stopping hotspot...")
            
            # 仅删除本程序创建或明确为 AP 模式的热点连接，避免误删普通 Wi‑Fi
            hotspot_ssid = self.config['hotspot']['ssid']
            hotspot_name = f"Hotspot-{hotspot_ssid}"

            # 获取所有连接的名称与类型（更易解析）
            result = self.run_command("nmcli -t -f NAME,TYPE connection show", check=False)
            hotspot_connections_found = False

            # 获取当前激活的连接列表，便于先 down 再删除
            active_result = self.run_command("nmcli -t -f NAME connection show --active", check=False)
            active_names = set([n.strip() for n in active_result.stdout.split('\n') if n.strip()])

            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue

                parts = line.split(':')
                connection_name = parts[0].strip()
                connection_type = parts[1].strip() if len(parts) > 1 else ''

                # 只考虑本程序创建的热点名，或名称中明显包含“hotspot”的连接
                name_looks_like_hotspot = (
                    connection_name == hotspot_name or
                    connection_name == hotspot_ssid or
                    ('hotspot' in connection_name.lower())
                )

                if not name_looks_like_hotspot:
                    # 普通 Wi‑Fi（如手机热点保存的 SSID: test）直接跳过
                    continue

                # 进一步确认是否为 AP 模式（802-11-wireless.mode == ap）
                mode = ''
                try:
                    mode_result = self.run_command(
                        f"nmcli -g 802-11-wireless.mode connection show '{connection_name}'",
                        check=False
                    )
                    mode = mode_result.stdout.strip().lower()
                except Exception:
                    mode = ''

                if (mode == 'ap') or (connection_name == hotspot_name):
                    logger.info(f"Found hotspot/AP connection: {connection_name} (mode={mode or 'unknown'})")

                    if connection_name in active_names:
                        logger.info(f"Deactivating hotspot connection: {connection_name}")
                        self.run_command(f"nmcli connection down '{connection_name}'", check=False)

                    logger.info(f"Deleting hotspot connection: {connection_name}")
                    self.run_command(f"nmcli connection delete '{connection_name}'", check=False)
                    hotspot_connections_found = True
                else:
                    logger.info(f"Skip non-AP connection: {connection_name} (mode={mode or 'unknown'})")
            
            if not hotspot_connections_found:
                logger.info("No hotspot connections found to remove")
            

            interface = self.config['hotspot']['interface']
            self.run_command(f"nmcli device set {interface} managed yes", check=False)
            
           
            device_result = self.run_command(f"nmcli device show {interface}", check=False)
            if 'ap' in device_result.stdout.lower() or 'hotspot' in device_result.stdout.lower():
                logger.info(f"Resetting {interface} from AP mode to station mode")
              
                self.run_command(f"nmcli device disconnect {interface}", check=False)
                time.sleep(1)
              
                self.run_command(f"nmcli device connect {interface}", check=False)
            
            logger.info("Hotspot stopped, normal WiFi connections preserved")
            return True
        except Exception as e:
            logger.error(f"Failed to stop hotspot: {e}")
            return False
    
    def start_hotspot(self):
        try:
            logger.info("Starting hotspot...")
            
            self.stop_hotspot()
            time.sleep(2)
            
            hotspot_config = self.config['hotspot']
            interface = hotspot_config['interface']
            ssid = hotspot_config['ssid']
            password = hotspot_config['password']
            channel = hotspot_config['channel']
            ip = hotspot_config['ip']
            
    
            logger.info(f"Preparing WiFi interface {interface}...")
            # 设置国家码，避免因监管域导致 AP 受限
            try:
                country = self.config.get('country', 'CN')
                self.run_command(f"iw reg set {country}", check=False)
            except Exception:
                pass
            self.run_command(f"nmcli device set {interface} managed yes", check=False)
            time.sleep(1)
            
       
            self.run_command(f"nmcli device disconnect {interface}", check=False)
            time.sleep(1)
            
         
            self.run_command(f"nmcli radio wifi on", check=False)
            time.sleep(1)
            
            hotspot_name = f"Hotspot-{ssid}"
            
      
            try:
                logger.info("Method 1: Creating hotspot with detailed configuration...")
                
                cmd = f"nmcli connection add type wifi ifname {interface} con-name '{hotspot_name}' autoconnect yes ssid '{ssid}'"
                self.run_command(cmd)
                
                self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless.mode ap")
                self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless.band bg")
                self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless.channel {channel}")
                # 关闭 Wi-Fi 省电，提升 AP 稳定性
                self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless.powersave 2", check=False)
                
             
                if password and password.strip():
                    logger.info("Creating secured hotspot with password")
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.key-mgmt wpa-psk")
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.psk '{password}'")
                else:
                    logger.info("Creating open hotspot without password")
                  
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.key-mgmt ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.psk ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.auth-alg ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.proto ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.pairwise ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.group ''", check=False)
                
                self.run_command(f"nmcli connection modify '{hotspot_name}' ipv4.method shared")
                self.run_command(f"nmcli connection modify '{hotspot_name}' ipv4.addresses {ip}/24")
                
                self.run_command(f"nmcli connection up '{hotspot_name}'")
                
                # 等待接口获取到共享IP，确保DHCP就绪
                for _ in range(8):
                    ip_ready = self.get_hotspot_ip()
                    if ip_ready:
                        break
                    time.sleep(1)
                
                if self.is_hotspot_running() and self.get_hotspot_ip():
                    logger.info(f"Hotspot started successfully: {ssid}")
                    self.update_display("hotspot")
                    return True
                    
            except Exception as e1:
                logger.warning(f"Method 1 failed: {e1}")
                
         
            try:
                logger.info("Method 2: Using simplified hotspot command...")
                
                
                if password and password.strip():
                    logger.info("Creating secured hotspot with password (Method 2)")
                    cmd = f"nmcli device wifi hotspot ifname {interface} ssid '{ssid}' password '{password}'"
                else:
                    logger.info("Creating open hotspot without password (Method 2)")
                    cmd = f"nmcli device wifi hotspot ifname {interface} ssid '{ssid}'"
                
                self.run_command(cmd)
                time.sleep(3)
                
                # 获取真正的热点连接名（通常为 'Hotspot'），并应用必要配置
                active_con_name = None
                try:
                    active_list = self.run_command("nmcli -t -f NAME connection show --active", check=False)
                    for name in [n.strip() for n in active_list.stdout.split('\n') if n.strip()]:
                        mode_res = self.run_command(
                            f"nmcli -g 802-11-wireless.mode connection show '{name}'",
                            check=False
                        )
                        if mode_res.stdout.strip().lower() == 'ap':
                            active_con_name = name
                            break
                except Exception:
                    active_con_name = None
                # 若未取到，用常见默认名兜底
                if not active_con_name:
                    active_con_name = 'Hotspot'

                # 关闭省电、设置共享与地址，确保DHCP与NAT
                self.run_command(f"nmcli connection modify '{active_con_name}' 802-11-wireless.powersave 2", check=False)
                self.run_command(f"nmcli connection modify '{active_con_name}' ipv4.method shared", check=False)
                self.run_command(f"nmcli connection modify '{active_con_name}' ipv4.addresses {ip}/24", check=False)
                
                if not (password and password.strip()):
                    logger.info("Ensuring open network configuration (Method 2)")
                    self.run_command(f"nmcli connection modify '{active_con_name}' 802-11-wireless-security.key-mgmt ''", check=False)
                    self.run_command(f"nmcli connection modify '{active_con_name}' 802-11-wireless-security.psk ''", check=False)
                
                time.sleep(2)
                
                # 等待接口获取到共享IP，确保DHCP就绪
                for _ in range(8):
                    ip_ready = self.get_hotspot_ip()
                    if ip_ready:
                        break
                    time.sleep(1)
                
                if self.is_hotspot_running() and self.get_hotspot_ip():
                    logger.info("Hotspot started successfully using simplified method")
                    self.update_display("hotspot")
                    return True
                    
            except Exception as e2:
                logger.warning(f"Method 2 failed: {e2}")
                
         
            try:
                logger.info("Method 3: Force creating hotspot without network dependency...")
                
                
                self.run_command(f"ip link set {interface} up", check=False)
                time.sleep(1)
                
               
                cmd = f"nmcli connection add type wifi ifname {interface} con-name '{hotspot_name}' ssid '{ssid}'"
                self.run_command(cmd, check=False)
                
               
                self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless.mode ap", check=False)
                self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless.band bg", check=False)
                
               
                if password and password.strip():
                    logger.info("Creating secured hotspot with password (Method 3)")
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.key-mgmt wpa-psk", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.psk '{password}'", check=False)
                else:
                    logger.info("Creating open hotspot without password (Method 3)")
                  
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.key-mgmt ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.psk ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.auth-alg ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.proto ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.pairwise ''", check=False)
                    self.run_command(f"nmcli connection modify '{hotspot_name}' 802-11-wireless-security.group ''", check=False)
                
               
                # 使用共享模式，确保DHCP服务与NAT由NetworkManager管理
                self.run_command(f"nmcli connection modify '{hotspot_name}' ipv4.method shared", check=False)
                self.run_command(f"nmcli connection modify '{hotspot_name}' ipv4.addresses {ip}/24", check=False)
                
                
                self.run_command(f"nmcli connection up '{hotspot_name}'", check=False)
                # 等待接口获取到共享IP，确保DHCP就绪
                for _ in range(8):
                    ip_ready = self.get_hotspot_ip()
                    if ip_ready:
                        break
                    time.sleep(1)
                
                if self.is_hotspot_running() and self.get_hotspot_ip():
                    logger.info("Hotspot started successfully using force method")
                    self.update_display("hotspot")
                    return True
                    
            except Exception as e3:
                logger.error(f"Method 3 also failed: {e3}")
            
            logger.error("All hotspot startup methods failed")
            self.update_display("error")
            return False
                
        except Exception as e:
            logger.error(f"Failed to start hotspot: {e}")
            self.update_display("error")
            return False
    
    def get_hotspot_ip(self):
        try:
            interface = self.config['hotspot']['interface']
            configured_ip = self.config['hotspot']['ip']
            
           
            try:
                interfaces = netifaces.interfaces()
                if interface in interfaces:
                    addrs = netifaces.ifaddresses(interface)
                    if netifaces.AF_INET in addrs:
                        for addr_info in addrs[netifaces.AF_INET]:
                            ip = addr_info['addr']
                            if ip == configured_ip:
                                logger.info(f"Found configured IP on {interface}: {ip}")
                                return ip
                            if (ip.startswith('10.42.0.') or 
                                ip.startswith('192.168.4.') or 
                                ip.startswith('192.168.1.') or
                                ip.startswith('192.168.12.')):
                                logger.info(f"Found hotspot IP on {interface}: {ip}")
                                return ip
            except Exception as e:
                logger.warning(f"Method 1 failed: {e}")
            
          
            try:
                result = subprocess.run(['nmcli', 'connection', 'show', '--active'], 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    for line in result.stdout.split('\n'):
                        if 'RaspberryPi5-Setup' in line or interface in line:
                            
                            conn_name = line.split()[0]
                            detail_result = subprocess.run(['nmcli', 'connection', 'show', conn_name], 
                                                         capture_output=True, text=True, timeout=10)
                            if detail_result.returncode == 0:
                                for detail_line in detail_result.stdout.split('\n'):
                                    if 'IP4.ADDRESS' in detail_line:
                                        ip_part = detail_line.split(':')[-1].strip()
                                        if '/' in ip_part:
                                            ip = ip_part.split('/')[0]
                                            logger.info(f"Found IP from nmcli: {ip}")
                                            return ip
            except Exception as e:
                logger.warning(f"Method 2 failed: {e}")
            
           
            try:
                for iface in netifaces.interfaces():
                    if iface.startswith('wl') or iface == interface:
                        addrs = netifaces.ifaddresses(iface)
                        if netifaces.AF_INET in addrs:
                            for addr_info in addrs[netifaces.AF_INET]:
                                ip = addr_info['addr']
                                if (ip.startswith('10.42.0.') or 
                                    ip.startswith('192.168.4.') or 
                                    ip.startswith('192.168.1.') or
                                    ip.startswith('192.168.12.')):
                                    logger.info(f"Found hotspot IP on {iface}: {ip}")
                                    return ip
            except Exception as e:
                logger.warning(f"Method 3 failed: {e}")
            
            logger.warning(f"Using configured IP as fallback: {configured_ip}")
            return configured_ip
        except Exception as e:
            logger.error(f"Failed to get hotspot IP: {e}")
            return self.config['hotspot']['ip']
    
    def get_wifi_connected_ip(self):
        try:
            for interface in netifaces.interfaces():
                if interface.startswith('wlan') or 'wifi' in interface.lower():
                    try:
                        addrs = netifaces.ifaddresses(interface)
                        if netifaces.AF_INET in addrs:
                            for addr_info in addrs[netifaces.AF_INET]:
                                ip = addr_info['addr']
                                if (not ip.startswith('127.') and 
                                    not ip.startswith('10.42.0.') and
                                    not ip.startswith('192.168.4.') and
                                    not ip.startswith('169.254.')):
                                    return ip
                    except Exception:
                        continue
            return None
        except Exception as e:
            logger.error(f"Failed to get WiFi connected IP: {e}")
            return None
    
    def is_connected_to_wifi(self):
        try:
            result = self.run_command("nmcli connection show --active", check=False)
            for line in result.stdout.split('\n'):
                if 'wifi' in line.lower() and 'hotspot' not in line.lower():
                    return True
            return False
        except Exception:
            return False
    
    def connect_to_wifi(self, ssid, password):
        try:
            logger.info(f"Connecting to WiFi: {ssid}")
            
            self.update_display("connecting")
            # 连接过程开启热点抑制，避免监控线程中途启动热点
            self.connecting_wifi = True
            self.suppress_hotspot_until = time.time() + 40
            
            self.stop_hotspot()
            time.sleep(2)
            
            interface = self.config['hotspot']['interface']
            
            self.run_command(f"nmcli device wifi rescan ifname {interface}", check=False)
            time.sleep(2)
            # 保留已保存的连接配置（不再删除目标 SSID 的连接）
            
            if password:
                cmd = f"nmcli device wifi connect '{ssid}' password '{password}' ifname {interface}"
            else:
                cmd = f"nmcli device wifi connect '{ssid}' ifname {interface}"
            
            self.run_command(cmd)
            # 轮询等待连接建立，最多等待30秒
            connected = False
            for _ in range(30):
                if self.is_connected_to_wifi():
                    connected = True
                    break
                time.sleep(1)
            
            if connected:
                logger.info(f"Successfully connected to WiFi: {ssid}")
                self.update_display("wifi_connected")
                
                # WiFi连接成功后，自动关闭热点
                logger.info("WiFi connected successfully, stopping hotspot...")
                self.stop_hotspot()
                # 连接完成，短暂保持抑制，避免误触发热点
                self.connecting_wifi = False
                self.suppress_hotspot_until = time.time() + 10
                
                return True
            else:
                logger.error(f"Failed to connect to WiFi: {ssid}")
                self.update_display("error")
        
                logger.info("WiFi connection failed, restarting hotspot...")
                # 连接失败，解除抑制再开启热点
                self.connecting_wifi = False
                self.suppress_hotspot_until = 0
                self.start_hotspot()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to WiFi: {e}")
            self.connecting_wifi = False
            self.suppress_hotspot_until = 0
            return False
    
    def generate_qr_code(self, url):
        try:
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_str = base64.b64encode(buffer.getvalue()).decode()
            
            return img_str
        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            return None
    
    def update_display(self, mode="hotspot"):
        if not self.display:
            return
        
        try:
            if mode == "hotspot":
                hotspot_ip = self.get_hotspot_ip()
                ssid = self.config['hotspot']['ssid']
                
           
                web_url = f"http://{hotspot_ip}:{self.config['web_server']['port']}"
                self.display_single_qr_code(web_url)
                logger.info(f"Display updated - Hotspot mode with single QR code: {ssid} ({hotspot_ip}) - URL: {web_url}")
                
            elif mode == "wifi_connected":
                wifi_ip = self.get_wifi_connected_ip()
                if wifi_ip:
                    web_url = f"http://{wifi_ip}:{self.config['web_server']['port']}"
                    self.display_qr_with_info(web_url, self.get_text('wifi_connected'), f"IP: {wifi_ip}", f"Config: {web_url}")
                    logger.info(f"Display updated - WiFi connected mode: {wifi_ip}")
                else:
                    self.display_text_message(self.get_text('wifi_connecting'))
                    
            elif mode == "connecting":
                self.display_text_message(self.get_text('connecting_wait'))
                
            elif mode == "error":
                self.display_text_message(self.get_text('connection_failed'))
                
        except Exception as e:
            logger.error(f"Failed to update display: {e}")
    
    def display_qr_with_info(self, qr_data, title, line1, line2):
        if not self.display:
            return
        
        try:
            
            img = Image.new('RGB', (320, 240), color='white')
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            is_chinese = self.current_language == 'cn'
            title_font = get_font(20, is_chinese)
            text_font = get_font(16, is_chinese)
            large_font = get_font(16, is_chinese)
            
         
            qr = qrcode.QRCode(version=1, box_size=3, border=1)
            qr.add_data(qr_data)
            qr.make(fit=True)
            qr_img = qr.make_image(fill_color="black", back_color="white")
            
           
            qr_size = 120
            qr_img = qr_img.resize((qr_size, qr_size))
            
           
            qr_x = (320 - qr_size) // 2
            
            qr_y = 30
            img.paste(qr_img, (qr_x, qr_y))
            
         
            draw.text((160, 10), title, font=title_font, fill='black', anchor='mt')
            
        
            y_offset = qr_y + qr_size + 10
            draw.text((160, y_offset), line1, font=text_font, fill='black', anchor='mt')
            draw.text((160, y_offset + 20), line2, font=text_font, fill='black', anchor='mt')
            
        
            network_y = y_offset + 40
            draw.text((160, network_y), self.get_text('same_network'), font=large_font, fill='black', anchor='mt')
            
            self.display.ShowImage(img)
            
        except Exception as e:
            logger.error(f"Failed to display QR code: {e}")
    
    def display_single_qr_code(self, web_url):
        """显示单个二维码：网址访问"""
        if not self.display:
            return
        
        try:
           
            img = Image.new('RGB', (320, 240), color='white')
            draw = ImageDraw.Draw(img)
            
            is_chinese = self.current_language == 'cn'
            title_font = get_font(18, is_chinese)
            text_font = get_font(15, is_chinese)
            large_font = get_font(16, is_chinese)
            
           
            web_qr = qrcode.QRCode(version=1, box_size=3, border=1)
            web_qr.add_data(web_url)
            web_qr.make(fit=True)
            web_qr_img = web_qr.make_image(fill_color="black", back_color="white")
            
           
            qr_size = 120
            web_qr_img = web_qr_img.resize((qr_size, qr_size))
            
           
            qr_x = (320 - qr_size) // 2
          
            qr_y = 35
            
            
            img.paste(web_qr_img, (qr_x, qr_y))
            
         
            draw.text((160, 8), self.get_text('wifi_hotspot_setup'), font=title_font, fill='black', anchor='mt')
            
          
            label_y = qr_y + qr_size + 8
            draw.text((160, label_y), self.get_text('scan_to_access'), font=text_font, fill='black', anchor='mt')
            
        
            network_y = label_y + 20
            draw.text((160, network_y), self.get_text('same_network'), font=large_font, fill='black', anchor='mt')
            
          
            instruction_y = network_y + 18
            draw.text((160, instruction_y), self.get_text('connect_first'), font=text_font, fill='black', anchor='mt')
            
            self.display.ShowImage(img)
            logger.info("Single QR code displayed successfully")
            
        except Exception as e:
            logger.error(f"Failed to display single QR code: {e}")
    
    def display_text_message(self, message, bg_color='white'):
        if not self.display:
            return
        
        try:
           
            img = Image.new('RGB', (320, 240), color='white')
            from PIL import ImageDraw, ImageFont
            draw = ImageDraw.Draw(img)
            
            is_chinese = self.current_language == 'cn'
            font = get_font(22, is_chinese)
            large_font = get_font(16, is_chinese)
            
           
            draw.multiline_text((160, 100), message, font=font, fill='black', anchor='mm', align='center')
            
           
            draw.text((160, 140), self.get_text('same_network'), font=large_font, fill='black', anchor='mm')
            
            self.display.ShowImage(img)
            
        except Exception as e:
            logger.error(f"Failed to display text message: {e}")
    
    def setup_routes(self):
        @self.app.route('/')
        def index():
           
            current_lang = request.args.get('lang', self.current_language)
            if current_lang not in ['cn', 'en']:
                current_lang = self.current_language
            
            hotspot_ip = self.get_hotspot_ip()
            qr_url = f"http://{hotspot_ip}:{self.config['web_server']['port']}"
            qr_code = self.generate_qr_code(qr_url)
            
           
            # 每次渲染依据当前语言加载对应语言包，避免缓存不一致
            texts = {}
            try:
                language_dir = get_path("language_dir")
                lang_file = os.path.join(language_dir, 'cn.la' if current_lang == 'cn' else 'en.la')
                with open(lang_file, 'r', encoding='utf-8') as f:
                    pack = json.load(f) or {}
                    texts = pack.get('NETWORK_NEW', {})
            except Exception as e:
                logger.warning(f"Failed to load language pack for {current_lang}, fallback: {e}")
                pack = load_language() or {}
                texts = pack.get('NETWORK_NEW', {})
            
            html_template = """
<!DOCTYPE html>
<html lang="{{ 'zh-CN' if current_lang == 'cn' else 'en' }}">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ texts.web_title }}</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            margin-bottom: 20px;
        }
        h1 {
            color: #333;
            margin: 0;
            text-align: center;
        }
        .language-selector {
            background-color: #6c757d;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-size: 14px;
            min-width: 80px;
        }
        .language-selector:hover {
            background-color: #5a6268;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input[type="text"], input[type="password"], select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            box-sizing: border-box;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 12px 30px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            width: 100%;
            margin-top: 10px;
        }
        button:hover {
            background-color: #0056b3;
        }
        .qr-code {
            text-align: center;
            margin: 20px 0;
        }
        .qr-code img {
            max-width: 200px;
            height: auto;
        }
        .info {
            background-color: #e7f3ff;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
            border-left: 4px solid #007bff;
        }
        .status {
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            text-align: center;
        }
        .success { background-color: #d4edda; color: #155724; }
        .error { background-color: #f8d7da; color: #721c24; }
        .loading { background-color: #fff3cd; color: #856404; }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>{{ texts.web_title }}</h1>
        </div>
        
        <div style="text-align: center; margin-bottom: 20px;">
            <button class="language-selector" onclick="switchLanguage()">
                {{ texts.chinese if current_lang == 'en' else texts.english }}
            </button>
        </div>
        
        <div class="info">
            <strong>{{ texts.current_hotspot }}:</strong> {{ ssid }}<br>
            <strong>{{ texts.ip_address }}:</strong> {{ hotspot_ip }}<br>
            <strong>{{ texts.config_url }}:</strong> <a href="{{ qr_url }}">{{ qr_url }}</a>
        </div>
        
        <div id="status"></div>
        
        <form id="wifiForm">
            <div class="form-group">
                <label for="ssid">{{ texts.wifi_name }}:</label>
                <input type="text" id="ssid" name="ssid" required>
            </div>
            
            <div class="form-group">
                <label for="password">{{ texts.wifi_password }}:</label>
                <div style="position: relative;">
                    <input type="password" id="password" name="password" style="padding-right: 40px;">
                    <span id="togglePassword" style="position: absolute; right: 10px; top: 50%; transform: translateY(-50%); cursor: pointer; font-size: 14px; color: #007bff;">{{ texts.show }}</span>
                </div>
                <small>{{ texts.password_empty_hint }}</small>
            </div>
            
            <button type="submit">{{ texts.connect_wifi }}</button>
        </form>
        
        <button onclick="scanNetworks()" style="background-color: #28a745; margin-top: 10px;">
            {{ texts.scan_networks }}
        </button>
        
        <div id="networks" style="margin-top: 20px;"></div>
    </div>

    <script>
        // 存储当前语言的文本
        const texts = {
            show: "{{ texts.show }}",
            hide: "{{ texts.hide }}",
            connecting_please_wait: "{{ texts.connecting_please_wait }}",
            available_networks: "{{ texts.available_networks }}",
            scan_failed: "{{ texts.scan_failed }}",
            scanning_networks: "{{ texts.scanning_networks }}",
            secured: "{{ texts.secured }}",
            open: "{{ texts.open }}"
        };
        
        // 语言切换功能（仅影响网页，不修改language.ini）
        function switchLanguage() {
            const currentLang = "{{ current_lang }}";
            const newLang = currentLang === 'cn' ? 'en' : 'cn';
            window.location.href = `/?lang=${newLang}`;
        }
        
        // 密码可见性切换
        document.getElementById('togglePassword').addEventListener('click', function() {
            const passwordInput = document.getElementById('password');
            const toggleIcon = document.getElementById('togglePassword');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                toggleIcon.innerHTML = texts.hide;
            } else {
                passwordInput.type = 'password';
                toggleIcon.innerHTML = texts.show;
            }
        });
        
        document.getElementById('wifiForm').addEventListener('submit', function(e) {
            e.preventDefault();
            
            const ssid = document.getElementById('ssid').value;
            const password = document.getElementById('password').value;
            const statusDiv = document.getElementById('status');
            
            statusDiv.innerHTML = '<div class="status loading">' + texts.connecting_please_wait + '</div>';
            
            fetch('/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ssid: ssid,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    statusDiv.innerHTML = '<div class="status success">' + data.message + '</div>';
                    setTimeout(() => {
                        window.location.reload();
                    }, 3000);
                } else {
                    statusDiv.innerHTML = '<div class="status error">' + data.message + '</div>';
                }
            })
            .catch(error => {
                statusDiv.innerHTML = '<div class="status error">Connection failed: ' + error.message + '</div>';
            });
        });
        
        function scanNetworks() {
            const networksDiv = document.getElementById('networks');
            networksDiv.innerHTML = '<div class="status loading">' + texts.scanning_networks + '</div>';
            
            fetch('/scan')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    let html = '<h3>' + texts.available_networks + ':</h3>';
                    data.networks.forEach(network => {
                        html += `<div style="padding: 10px; border: 1px solid #ddd; margin: 5px 0; border-radius: 5px; cursor: pointer;" 
                                onclick="selectNetwork('${network.ssid}')">
                                <strong>${network.ssid}</strong>
                                <span style="color: ${network.security ? '#dc3545' : '#28a745'}; font-size: 12px; margin-left: 10px;">
                                [${network.security ? texts.secured : texts.open}]
                                </span>
                                </div>`;
                    });
                    networksDiv.innerHTML = html;
                } else {
                    networksDiv.innerHTML = '<div class="status error">' + texts.scan_failed + ': ' + data.message + '</div>';
                }
            })
            .catch(error => {
                networksDiv.innerHTML = '<div class="status error">Scan failed: ' + error.message + '</div>';
            });
        }
        
        function selectNetwork(ssid) {
            document.getElementById('ssid').value = ssid;
        }
    </script>
</body>
</html>
            """
            
            return render_template_string(
                html_template,
                ssid=self.config['hotspot']['ssid'],
                hotspot_ip=hotspot_ip,
                qr_url=qr_url,
                texts=texts,
                current_lang=current_lang
            )
        
        @self.app.route('/set_language', methods=['POST'])
        def set_language():
            try:
                data = request.get_json()
                new_lang = data.get('language', 'cn')
                
                if new_lang in ['cn', 'en']:
                    # 仅用于网页渲染，不修改系统语言或SPI显示
                    return jsonify({'success': True, 'language': new_lang})
                else:
                    return jsonify({'success': False, 'message': 'Invalid language'})
            except Exception as e:
                logger.error(f"Error setting language: {e}")
                return jsonify({'success': False, 'message': str(e)})
        
        @self.app.route('/config', methods=['POST'])
        def config_wifi():
            try:
                data = request.get_json()
                ssid = data.get('ssid', '').strip()
                password = data.get('password', '').strip()
                
                if not ssid:
                    return jsonify({'success': False, 'message': 'Please enter WiFi network name'})
                
                success = self.connect_to_wifi(ssid, password)
                
                if success:
                    return jsonify({
                        'success': True, 
                        'message': f'Successfully connected to WiFi: {ssid}. Device will restart hotspot mode in 3 seconds.'
                    })
                else:
                    self.start_hotspot()
                    return jsonify({
                        'success': False, 
                        'message': f'Failed to connect to WiFi: {ssid}. Hotspot mode has been restarted.'
                    })
                    
            except Exception as e:
                logger.error(f"WiFi configuration failed: {e}")
                return jsonify({'success': False, 'message': f'Configuration failed: {str(e)}'})
        
        @self.app.route('/scan')
        def scan_networks():
            try:
                interface = self.config['hotspot']['interface']
                
                self.run_command(f"nmcli device wifi rescan ifname {interface}", check=False)
                time.sleep(2)
                
                # 采用紧凑模式输出，使用冒号作为字段分隔，避免 SECURITY 字段包含空格导致解析错误
                result = self.run_command(
                    f"nmcli -t -f SSID,SIGNAL,SECURITY device wifi list ifname {interface}",
                    check=False
                )
                
                networks = []
                lines = result.stdout.split('\n')
                
                seen_ssids = set() 
                
                for line in lines:
                    if not line.strip():
                        continue
                    parts = line.strip().split(':')
                    if len(parts) < 3:
                        continue
                    ssid, signal, security_info = parts[0], parts[1], parts[2]
                    ssid = (ssid or '').strip()
                    signal = (signal or '').strip()
                    security_info = (security_info or '').strip()
                    if ssid == '--' or ssid == '':
                        ssid = 'Hidden Network'
                    security = bool(security_info and security_info != '--')
                    # 过滤条件：
                    # 1. SSID不为空
                    # 2. 不是当前热点
                    # 3. 不是重复的SSID
                    # 4. 不是明显的IP地址或网段
                    if (ssid and 
                        ssid != self.config['hotspot']['ssid'] and 
                        ssid not in seen_ssids and
                        not ssid.startswith('10.') and
                        not ssid.startswith('192.168.') and
                        not ssid.startswith('172.') and
                        (ssid != 'Hidden Network' or len([n for n in networks if n['ssid'] == 'Hidden Network']) == 0)):
                        
                        seen_ssids.add(ssid)
                        networks.append({
                            'ssid': ssid,
                            'signal': signal,
                            'security': security
                        })
                
            
                networks.sort(key=lambda x: int(x['signal']) if x['signal'].isdigit() else 0, reverse=True)
                
                return jsonify({'success': True, 'networks': networks})
                
            except Exception as e:
                logger.error(f"Network scan failed: {e}")
                return jsonify({'success': False, 'message': f'Scan failed: {str(e)}'})
    
    def run_web_server(self):
        try:
            if self.is_connected_to_wifi():
                display_ip = self.get_wifi_connected_ip() or "0.0.0.0"
            else:
                display_ip = self.get_hotspot_ip()
            
            port = self.config['web_server']['port']
            
            logger.info(f"Starting web server: http://{display_ip}:{port}")
            
            self.app.run(
                host="0.0.0.0",
                port=port,
                debug=False,
                threaded=True
            )
        except Exception as e:
            logger.error(f"Web server failed to start: {e}")
    
    def start(self):
        try:
            logger.info("Starting WiFi Hotspot Manager...")
            
       
            self.start_button_monitor()
            
      
            self.start_network_monitor()
          
            has_internet = self.has_internet_connection()
            wifi_connected = self.is_wifi_connected()
            
            if has_internet and wifi_connected:
                logger.info("Internet connection detected, starting in WiFi mode...")
                self.hotspot_active = False
                self.update_display("wifi_connected")
            else:
                logger.info("No internet connection, starting hotspot mode...")
                if self.start_hotspot():
                    self.hotspot_active = True
                    self.hotspot_started_at = time.time()
                    hotspot_ip = self.get_hotspot_ip()
                    url = f"http://{hotspot_ip}:{self.config['web_server']['port']}"
                    logger.info(f"Hotspot config URL: {url}")
                    self.update_display("hotspot")
                else:
                    logger.error("Hotspot failed to start")
                    return False
            
           
            web_thread = threading.Thread(target=self.run_web_server, daemon=True)
            web_thread.start()
            
           
            while self.running:
                time.sleep(1)
                
            logger.info("Shutting down...")
            self.cleanup()
            
        except KeyboardInterrupt:
            logger.info("Interrupt received, shutting down...")
            self.running = False
            self.cleanup()
        except Exception as e:
            logger.error(f"Startup failed: {e}")
            self.running = False
            self.cleanup()
            return False
    
    def cleanup(self):
        try:
            logger.info("Starting cleanup process...")
            
            
            logger.info("Ensuring hotspot is stopped during cleanup...")
            self.stop_hotspot()
            if hasattr(self, 'hotspot_active'):
                self.hotspot_active = False
            
          
            if self.display:
                self.display.clear()
                logger.info("LCD display cleaned up")
                
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Failed to cleanup: {e}")

def main():
    if os.geteuid() != 0:
        print("Error: This program requires root privileges")
        print("Please use: sudo python3 wifi_hotspot_manager.py")
        sys.exit(1)
    
    manager = WiFiHotspotManager()
    manager.start()

if __name__ == "__main__":
    main()
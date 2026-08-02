from xgolib import XGO
import sys
from pathlib import Path
p = Path(__file__).resolve()

from uiutils import Button, font2, draw, display, splash, la, lal,dog
import time
import socket
import json
import sys
import select  

# 初始化

button = Button()
dog.attitude('p', 15)
dog.translation('z', 75)

# 网络设置
UDP_IP = "255.255.255.255"  # 广播地址
UDP_PORT = 5005
UDP_TIMEOUT = 0.1 

def send_arm_angles(angles):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.settimeout(UDP_TIMEOUT)
        data = json.dumps({"arm_angles": angles}).encode('utf-8')
        sock.sendto(data, (UDP_IP, UDP_PORT))
        print(lal["SHIJIAO_UDP"]["HOST_SENT"].format(angles))
    except Exception as e:
        print(lal["SHIJIAO_UDP"]["HOST_SEND_FAILED"].format(e))
    finally:
        if 'sock' in locals():
            sock.close()
            
def receive_arm_angles():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(UDP_TIMEOUT)  
        sock.bind(('0.0.0.0', UDP_PORT))  
        
        data, addr = sock.recvfrom(1024)
        print(lal["SHIJIAO_UDP"]["CLIENT_RAW"].format(data))  
        try:
            data = json.loads(data.decode('utf-8'))
            if "arm_angles" in data:
                print(lal["SHIJIAO_UDP"]["CLIENT_PARSE_SUCCESS"].format(data['arm_angles'], addr[0]))
                return data["arm_angles"], "success"
            else:
                print(lal["SHIJIAO_UDP"]["CLIENT_MISSING_FIELD"]) 
                return None, "invalid_data"
        except json.JSONDecodeError as e:
            print(lal["SHIJIAO_UDP"]["CLIENT_JSON_ERROR"].format(e))
            return None, "json_error"
    except socket.timeout:
        print(lal["SHIJIAO_UDP"]["CLIENT_TIMEOUT"]) 
        return None, "timeout"
    except Exception as e:
        print(lal["SHIJIAO_UDP"]["CLIENT_ERROR"].format(e))
        return None, "error"
    finally:
        if 'sock' in locals():
            sock.close()


def check_exit_buttons():
    """检查退出按钮（B强制退出，C返回）"""
    if button.press_b():
        dog.reset()
        sys.exit(0)
    if button.press_c():
        return True
    return False

def host_mode():
    """主机模式"""
    dog.unload_motor(5)
    while True:
        
        draw.rectangle((0, 0, display.height, display.width), fill="BLACK")
        draw.text((20, 80), lal["SHIJIAO_UDP"]["HOST_RUNNING"], fill="CYAN", font=font2)
        draw.text((20, 120), lal["SHIJIAO_UDP"]["HELP_BACK"], fill="WHITE", font=font2)
        draw.text((20, 160), lal["SHIJIAO_UDP"]["HELP_FORCE_EXIT"], fill="WHITE", font=font2)
        display.ShowImage(splash)
        
        
        motor_data = dog.read_motor()
        if motor_data:
            send_arm_angles(motor_data[-3:])
        
        
        if check_exit_buttons():
            break
            
        time.sleep(0.1)

def client_mode():
    """从机模式"""
    dog.load_allmotor()
    while True:
   
        draw.rectangle((0, 0, display.height, display.width), fill="BLACK")
        draw.text((20, 80), lal["SHIJIAO_UDP"]["CLIENT_RUNNING"], fill="CYAN", font=font2)
        draw.text((20, 120), lal["SHIJIAO_UDP"]["HELP_BACK"], fill="WHITE", font=font2)
        draw.text((20, 160), lal["SHIJIAO_UDP"]["HELP_FORCE_EXIT"], fill="WHITE", font=font2)
        display.ShowImage(splash)
  
        angles, status = receive_arm_angles()
        if status == "success":
            dog.motor([51, 52, 53], angles)
        
     
        if check_exit_buttons():
            break
            
        time.sleep(0.1)


while True:

    draw.rectangle((0, 0, display.height, display.width), fill="BLACK")
    draw.text((35, 80), lal["SHIJIAO_UDP"]["HELP_HOST"], fill="WHITE", font=font2)
    draw.text((35, 120), lal["SHIJIAO_UDP"]["HELP_CLIENT"], fill="WHITE", font=font2)
    draw.text((35, 160), lal["SHIJIAO_UDP"]["HELP_FORCE_EXIT"], fill="RED", font=font2)
    display.ShowImage(splash)
    

    if button.press_b():
        dog.reset()
        sys.exit(0)
    

    if button.press_a():
        host_mode()
    elif button.press_d():
        client_mode()
    
    time.sleep(0.1)
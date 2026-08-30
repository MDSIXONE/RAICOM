# -*- coding: utf-8 -*-
import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
import json
import uuid
import random
import string
import time
import os
import sys

# --- 引入 UI 和 按键库 ---
try:
    import xgoscreen.LCD_2inch as LCD_2inch
    from PIL import Image, ImageDraw, ImageFont
    from uiutils import Button
except ImportError:
    print("❌ 缺少 UI 或按键库，请确保在机器狗环境中运行")
    sys.exit(1)

# --- 引入机器狗驱动库 ---
try:
    from xgolib import XGO
except ImportError:
    print("[WARN] xgolib library not found")
    XGO = None

# ================= 1. 配置与动作定义 =================

# 字体路径
FONT_PATH = "/home/pi/RaspberryPi-CM5/common/model/msyh.ttc"

# --- ������ UI 配色方案 ---
COLOR_BG        = (15, 21, 46)    # 深空蓝背景
COLOR_CARD_BG   = (30, 38, 69)    # 卡片背景
COLOR_TEXT_MAIN = (255, 255, 255) # 主文字白
COLOR_TEXT_SUB  = (143, 155, 179) # 副文字灰
COLOR_ACCENT_1  = (0, 255, 209)   # 亮青色 (用户名/指令)
COLOR_ACCENT_2  = (255, 193, 7)   # 琥珀色 (密码)
COLOR_BTN_EXIT  = (231, 76, 60)   # 退出红
# ---------------------

# 配置文件路径
CONFIG_FILE = "mqtt_config.json"

# 动作映射表 (中文)
ACTION_MAP_CN = {
    '趴下': 1, '站起': 2, '匍匐前进': 3, '转圈': 4, '原地踏步': 5, '蹲起': 6, 
    '坐下': 12, '招手': 13, '握手': 19, '展示机械臂': 20, '俯卧撑': 21, 
    '跳舞': 23, '调皮': 24, '向上抓取': 128, '向中抓取': 129, '向下抓取': 130
}

# 英文兼容映射
ACTION_MAP_EN = {
    "lie down": 1, "stand up": 2, "crawl": 3, "sit": 12, "wave": 13,
    "handshake": 19, "pushups": 21, "dance": 23, "reset": 255
}

# 构建鲁棒的查找表
ROBUST_ACTION_MAP = {}
ROBUST_ACTION_MAP.update(ACTION_MAP_CN)
for key, val in ACTION_MAP_EN.items():
    ROBUST_ACTION_MAP[key] = val
    clean_key = key.lower().replace(" ", "").replace("_", "")
    ROBUST_ACTION_MAP[clean_key] = val

# 动作时间表
TIME_LIST = [0] * 131
TIME_LIST[1:25] = [3, 3, 5, 5, 4, 4, 4, 4, 4, 7, 7, 5, 7, 10, 6, 6, 6, 6, 10, 9, 8, 8, 6, 7]
TIME_LIST[128:131] = [10, 10, 10]

# 全局变量
dog = None
DOG_TYPE = 'M' 
MY_USERNAME = "" # 用于UI显示
MY_TOPIC = ""    # 用于MQTT订阅
MY_PASSWORD = ""

# ================= 2. 硬件初始化 =================

# 初始化 LCD
display = LCD_2inch.LCD_2inch()
display.Init()
# 初始化按键
button = Button()

print("-" * 30)
print("Initializing XGO Hardware...")
try:
    if XGO:
        dog = XGO(port='/dev/ttyAMA0', version="xgomini")
        fm = dog.read_firmware()
        if fm[0] == 'M':
            DOG_TYPE = 'M'
        else:
            dog = XGO(port='/dev/ttyAMA0', version="xgolite")
            DOG_TYPE = 'L'
        print("[INFO] Hardware Init Success")
    else:
        raise Exception("xgolib missing")
except Exception as e:
    print(f"[WARN] Hardware Init Failed: {e}")
    dog = None
print("-" * 30)

# ================= 3. UI 显示函数 (美化版) =================

def show_interface(username, password, status="Running...", cmd_name=None):
    """ 美化版 UI 绘制 """
    try:
        # 创建画布
        image = Image.new("RGB", (display.height, display.width), COLOR_BG)
        draw = ImageDraw.Draw(image)
        
        # 加载字体 (尝试加载不同大小)
        def load_font(size):
            try:
                return ImageFont.truetype(FONT_PATH, size)
            except:
                return ImageFont.load_default()

        font_label = load_font(14)  # 标签小字
        font_val   = load_font(22)  # 用户名/密码大字
        font_cmd   = load_font(32)  # 指令超大字
        font_wait  = load_font(24)  # 等待中文字
        font_st    = load_font(14)  # 状态栏

        # --- 顶部信息栏 (卡片式布局) ---
        # 左卡片：用户名
        draw.rectangle([(10, 10), (155, 75)], fill=COLOR_CARD_BG)
        draw.text((20, 15), "USER ID", fill=COLOR_TEXT_SUB, font=font_label)
        draw.text((20, 38), username, fill=COLOR_ACCENT_1, font=font_val)

        # 右卡片：密码
        draw.rectangle([(165, 10), (310, 75)], fill=COLOR_CARD_BG)
        draw.text((175, 15), "PASSWORD", fill=COLOR_TEXT_SUB, font=font_label)
        draw.text((175, 38), password, fill=COLOR_ACCENT_2, font=font_val)

        # --- 中央指令区 (视觉焦点) ---
        # 绘制一个略微亮一点的背景框
        draw.rectangle([(10, 85), (310, 190)], fill=COLOR_CARD_BG, outline=COLOR_BG)
        
        if cmd_name:
            # 绘制 "RUNNING" 标签
            draw.rectangle([(130, 95), (190, 110)], fill=COLOR_ACCENT_1)
            draw.text((140, 95), "RUNNING", fill=(0,0,0), font=font_label)
            
            # 居中计算指令文字
            text_bbox = draw.textbbox((0, 0), cmd_name, font=font_cmd)
            text_w = text_bbox[2] - text_bbox[0]
            text_h = text_bbox[3] - text_bbox[1]
            x_pos = 160 - (text_w / 2)
            y_pos = 138 - (text_h / 2)
            
            draw.text((x_pos, y_pos), cmd_name, fill=COLOR_TEXT_MAIN, font=font_cmd)
        else:
            # 等待状态
            wait_text = "Waiting for CMD..."
            text_bbox = draw.textbbox((0, 0), wait_text, font=font_wait)
            text_w = text_bbox[2] - text_bbox[0]
            x_pos = 160 - (text_w / 2)
            draw.text((x_pos, 125), wait_text, fill=COLOR_TEXT_SUB, font=font_wait)

        # --- 底部状态栏 ---
        # 状态文字
        draw.text((15, 205), f"Status: {status}", fill=COLOR_TEXT_MAIN, font=font_st)
        
        # 退出按钮 (右下角)
        btn_x = 240
        btn_y = 200
        draw.rectangle([(btn_x, btn_y), (btn_x + 70, btn_y + 30)], fill=COLOR_BTN_EXIT)
        draw.text((btn_x + 13, btn_y + 5), "EXIT (B)", fill=COLOR_TEXT_MAIN, font=font_st)

        display.ShowImage(image)
        
    except Exception as e:
        print(f"UI Draw Error: {e}")

# ================= 4. 辅助算法 & 执行逻辑 =================

def adaptive_move(distance):
    distance = abs(distance)
    if distance < 15: return 10
    elif distance < 30: return 15
    else: return 20

def adaptive_turn(yaw):
    yaw = abs(yaw)
    if DOG_TYPE == 'M':
        if yaw < 20: return 10
        elif yaw < 50: return 20
        else: return 30
    else: return 30

def execute_command(cmd):
    global dog, DOG_TYPE, MY_USERNAME, MY_PASSWORD

    c_type = str(cmd.get("type", "")).lower()
    c_val = cmd.get("value", 0)
    c_name = cmd.get("name", "")

    log_info = f"{c_name}" if c_name else f"{c_type}:{c_val}"
    print(f"\n[CMD] 执行指令: {log_info} (Type={c_type}, Val={c_val})")
    show_interface(MY_USERNAME, MY_PASSWORD, "Executing...", cmd_name=c_name if c_name else c_type)

    if not dog:
        print(f"[SIM] Simulation Mode - Action Triggered")
        return

    try:
        if isinstance(c_val, list):
            val_list = c_val; int_val = 0
        else:
            num_val = float(c_val) if c_val is not None else 0
            int_val = int(num_val); val_list = []
    except:
        int_val = 0; val_list = []

    if c_type in ['x', 'move', 'y']:
        axis = 'x' if c_type in ['x', 'move'] else 'y'
        if int_val == 0: return
        speed = adaptive_move(int_val)
        dir_sign = 1 if int_val > 0 else -1
        dog.move(axis, speed * dir_sign)
        time.sleep(abs(int_val / speed))
        dog.stop()
        time.sleep(0.5)

    elif c_type == 'turn':
        if int_val == 0: return
        t_angle = int_val if DOG_TYPE == 'M' else int(1.5 * int_val)
        speed = adaptive_turn(t_angle)
        dir_sign = 1 if t_angle > 0 else -1
        dog.turn(speed * dir_sign)
        time.sleep(abs(t_angle / speed))
        dog.stop()
        time.sleep(0.5)

    elif c_type in ['action', 'raw']:
        raw_str = str(c_val)
        act_id = 0
        if isinstance(c_val, int) or raw_str.isdigit():
            act_id = int(c_val)
        else:
            clean_str = raw_str.lower().replace(" ", "").replace("_", "")
            if clean_str in ROBUST_ACTION_MAP:
                act_id = ROBUST_ACTION_MAP[clean_str]
        
        if act_id != 0:
            if act_id == 255: dog.reset()
            else:
                dog.action(act_id)
                dur = TIME_LIST[act_id] if act_id < len(TIME_LIST) else 3
                time.sleep(dur)
        else:
            print(f"[WARN] 无法识别的动作 ID: {c_val}")

    elif c_type in ['reset', 'stop']: 
        dog.reset()
        time.sleep(1)

    show_interface(MY_USERNAME, MY_PASSWORD, "Ready", cmd_name="Done")

# ================= 5. MQTT 通信 =================

def get_device_credentials():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
                username = config.get('username')
                topic = config.get('topic')
                password = config.get('password')
                if username and topic and password:
                    print(f"[INIT] Loaded config from {CONFIG_FILE}")
                    return topic, username, password
    except Exception as e:
        print(f"[WARN] Config load failed: {e}, generating new credentials...")

    uid_suffix = str(uuid.uuid4()).split('-')[0].upper()
    username = f"LW{uid_suffix}"
    topic = f"cmd/dog/{username}"
    chars = string.ascii_uppercase + string.digits
    password = ''.join(random.choice(chars) for _ in range(6))
    
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump({'topic': topic, 'username': username, 'password': password}, f)
        print(f"[INIT] New credentials generated and saved to {CONFIG_FILE}")
    except Exception as e:
        print(f"[ERROR] Failed to save config: {e}")

    return topic, username, password

MY_TOPIC, MY_USERNAME, MY_PASSWORD = get_device_credentials()

def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        print(f"[MQTT] Connected to {MY_TOPIC}")
        client.subscribe(MY_TOPIC)
        if dog: dog.reset()
        show_interface(MY_USERNAME, MY_PASSWORD, "Connected")
    else:
        print(f"[MQTT] Connect Failed: {rc}")
        show_interface(MY_USERNAME, MY_PASSWORD, "Connect Failed")

def on_message(client, userdata, msg):
    try:
        payload_str = msg.payload.decode('utf-8')
        print(f"[DEBUG] Raw Payload: {payload_str}")
        
        try:
            data = json.loads(payload_str)
        except:
            print("[WARN] Payload is not JSON")
            return

        if data.get("token") != MY_PASSWORD: 
            print("[AUTH] Token mismatch")
            return

        ack_topic = f"{MY_TOPIC}/ack"
        ack_payload = json.dumps({"status": "received", "ts": time.time()})
        client.publish(ack_topic, ack_payload, qos=0)

        raw_action = data.get("action")
        commands = []

        if isinstance(raw_action, list):
            if len(raw_action) > 0 and isinstance(raw_action[0], str):
                 try:
                     commands = [json.loads(raw_action[0])]
                 except:
                     commands = [{"type": "raw", "value": raw_action[0]}]
            else:
                commands = raw_action
        elif isinstance(raw_action, str):
            clean_str = raw_action.replace("```json", "").replace("```", "").replace("`", "").strip()
            try:
                parsed = json.loads(clean_str)
                if isinstance(parsed, list):
                    commands = parsed
                else:
                    commands = [parsed]
            except:
                commands = [{"type": "raw", "value": clean_str}]
        elif isinstance(raw_action, dict):
            commands = [raw_action]

        print(f"[DEBUG] Parsed Commands: {commands}")

        for cmd in commands: 
            execute_command(cmd)

    except Exception as e:
        print(f"[ERROR] Logic Error: {e}")
        import traceback
        traceback.print_exc()

# ================= 6. 主程序 =================

BROKER = "broker.emqx.io"
PORT = 1883

def main():
    client = mqtt.Client(CallbackAPIVersion.VERSION2)
    client.on_connect = on_connect
    client.on_message = on_message
    
    print("Connecting Broker...")
    show_interface(MY_USERNAME, MY_PASSWORD, "Connecting...", "Init...")
    
    try:
        client.connect(BROKER, PORT, 60)
        client.loop_start() 
    except Exception as e:
        print(f"Network Error: {e}")
        show_interface("无网络", "Error", "Connection Failed")
        time.sleep(5)
        return

    show_interface(MY_USERNAME, MY_PASSWORD, "Waiting...", "Ready")

    print("\n" + "="*40)
    print(f"User:     {MY_USERNAME}")
    print(f"Topic:    {MY_TOPIC}")
    print(f"Password: {MY_PASSWORD}")
    print("="*40 + "\n")
    print(">>> Press 'B' button to EXIT <<<")
    
    try:
        while True:
            if button.press_b():
                print("\n[USER] Button B Pressed. Exiting...")
                show_interface(MY_USERNAME, MY_PASSWORD, "Closing...")
                client.loop_stop()
                client.disconnect()
                if dog:
                    print("Resetting Robot...")
                    dog.reset()
                    time.sleep(1)
                break
            time.sleep(0.1)

    except KeyboardInterrupt:
        pass
    finally:
        if dog: dog.reset()
        print("Program Terminated.")
        sys.exit(0)

if __name__ == "__main__":
    main()
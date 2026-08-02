import os, sys, time, signal, threading, asyncio, aiohttp, socket, json
from subprocess import Popen, DEVNULL
from pathlib import Path
from flask import Flask, request, jsonify
from PIL import Image, ImageDraw
import requests
# === 路径与模块初始化 ===
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
p = Path(__file__).resolve()
for anc in [p] + list(p.parents):
    if anc.name == 'RaspberryPi-CM5':
        sys.path.append(str(anc / 'common'))
        break

from uiutils import language,Button,display,lal,font2,dog

# === 自动识别设备型号 ===
try:
    fm1 = dog.read_firmware()
    if isinstance(fm1, str):
        candidate = fm1.split('-')[0].upper()
        dog_type = candidate if candidate in ["R", "L", "M", "W", "B"] else "R"
    else:
        dog_type = "R"
except:
    dog_type = "R"

import threading

# === 全局配置 ===
HTTP_PORT = 8080
SPLASH_COLOR = (15, 21, 46)
SYNCHRONIZATION_DELAY = 1.0
exitmark = False
group_perform = False
start_timestamp = None
proc = None
proc_lock = threading.Lock()  # 新增：用于保护 proc 的访问
master_ip = None          # 当前表演的协调者 IP
last_master_ping = 0      # 上次成功 ping master 的时间
# 设备发现配置 (改为字典 + TTL超时机制，解决数量不一致)
known_devices = {}  # 格式: {ip: last_seen_timestamp}
known_devices_lock = threading.Lock()
DEVICE_TTL = 30.0   # 30秒无响应视为离线

# === 动作组配置（按 dog_type 区分）===
ACTION_GROUPS = {
    "R": [
        {"id": 1, "name": "趴下", "duration": 3},
        {"id": 2, "name": "站立", "duration": 3},
        
    ],
    "L": [
        {"id": 1, "name": "趴下", "duration": 3},
        {"id": 2, "name": "站立", "duration": 3},
        {"id": 6, "name": "蹲起", "duration": 4},
        {"id": 129, "name": "中抓", "duration": 10},
        {"id": 7, "name": "转动Roll", "duration": 4},
        {"id": 8, "name": "转动Pitch", "duration": 4},
        {"id": 9, "name": "转动Yaw", "duration": 4},
        {"id": 10, "name": "三轴转动", "duration": 7},
        {"id": 11, "name": "撒尿", "duration": 7},
        {"id": 130, "name": "下抓", "duration": 10},
        {"id": 12, "name": "坐下", "duration": 5},
        {"id": 13, "name": "招手", "duration": 7},
        {"id": 14, "name": "伸懒腰", "duration": 10},
        {"id": 15, "name": "波浪", "duration": 6},
        {"id": 19, "name": "握手", "duration": 10},
        {"id": 22, "name": "张望", "duration": 8},
        {"id": 128, "name": "上抓", "duration": 10},
    ],
    "M": [
        {"id": 1, "name": "趴下", "duration": 3},
        {"id": 2, "name": "站立", "duration": 3},
        {"id": 6, "name": "蹲起", "duration": 4},
        {"id": 129, "name": "中抓", "duration": 10},
        {"id": 7, "name": "转动Roll", "duration": 4},
        {"id": 8, "name": "转动Pitch", "duration": 4},
        {"id": 9, "name": "转动Yaw", "duration": 4},
        {"id": 10, "name": "三轴转动", "duration": 7},
        {"id": 11, "name": "撒尿", "duration": 7},
        {"id": 130, "name": "下抓", "duration": 10},
        {"id": 12, "name": "坐下", "duration": 5},
        {"id": 13, "name": "招手", "duration": 7},
        {"id": 14, "name": "伸懒腰", "duration": 10},
        {"id": 15, "name": "波浪", "duration": 6},
        {"id": 19, "name": "握手", "duration": 10},
        {"id": 22, "name": "张望", "duration": 8},
        {"id": 128, "name": "上抓", "duration": 10},
    ],
    "W": [
        {"id": 1, "name": "趴下", "duration": 3},
        {"id": 2, "name": "站立", "duration": 3},
        {"id": 6, "name": "蹲起", "duration": 4},
        {"id": 129, "name": "中抓", "duration": 10},
        {"id": 7, "name": "转动Roll", "duration": 4},
        {"id": 8, "name": "转动Pitch", "duration": 4},
        {"id": 9, "name": "转动Yaw", "duration": 4},
        {"id": 10, "name": "三轴转动", "duration": 7},
        {"id": 11, "name": "撒尿", "duration": 7},
        {"id": 130, "name": "下抓", "duration": 10},
        {"id": 12, "name": "坐下", "duration": 5},
        {"id": 13, "name": "招手", "duration": 7},
        {"id": 14, "name": "伸懒腰", "duration": 10},
        {"id": 15, "name": "波浪", "duration": 6},
        {"id": 19, "name": "握手", "duration": 10},
        {"id": 22, "name": "张望", "duration": 8},
        {"id": 128, "name": "上抓", "duration": 10},
    ],
    "B": [
        {"id": 0, "name": "待机", "duration": 1},  # B 型可能无复杂动作
    ]
}

# === 表情包路径配置（按 dog_type 区分）===
EXPRESSION_DIRS = {
    "R": "dog_LM",      
    "L": "dog_LM",   
    "M": "dog_LM",
    "W": "dog_W",
    "B": "dog_B",
}

# 默认回退
expression_dir = EXPRESSION_DIRS.get(dog_type, "dog_LM")
pic_path = "/home/pi/RaspberryPi-CM5/common/demos/expression/"


# 默认回退到 R 型动作（可选）
if dog_type not in ACTION_GROUPS:
    print(f"警告: 未知 dog_type '{dog_type}'，使用默认动作组")
    dog_type = "R"

actions_to_perform = ACTION_GROUPS[dog_type]

# === 表情动画序列（按 dog_type 区分）===
EXPRESSION_SEQUENCES = {
    "R": [
        ("sad", 85),
        ("naughty", 105),
        ("angry", 96),
        ("shy", 85),
        ("surprise", 72),
        ("happy", 82),
        ("sleepy", 88),
        ("wake", 58),
        ("lookaround", 107),
        ("love", 84),
        ("awkwardness", 80),
        ("eyes", 77),
        ("guffaw", 51),
        ("query", 81),
        ("Shakehead", 64),
        ("dizzy", 56),
        ("wronged", 136),
    ],
    "L": [
        ("sad", 85),
        ("naughty", 105),
        ("angry", 96),
        ("shy", 85),
        ("surprise", 72),
        ("happy", 82),
        ("sleepy", 88),
        ("wake", 58),
        ("lookaround", 107),
        ("love", 84),
        ("awkwardness", 80),
        ("eyes", 77),
        ("guffaw", 51),
        ("query", 81),
        ("Shakehead", 64),
        ("dizzy", 56),
        ("wronged", 136),
    ],
    "M": [
        ("sad", 85),
        ("naughty", 105),
        ("angry", 96),
        ("shy", 85),
        ("surprise", 72),
        ("happy", 82),
        ("sleepy", 88),
        ("wake", 58),
        ("lookaround", 107),
        ("love", 84),
        ("awkwardness", 80),
        ("eyes", 77),
        ("guffaw", 51),
        ("query", 81),
        ("Shakehead", 64),
        ("dizzy", 56),
        ("wronged", 136),
    ],
    "W": [
        ("sad", 85),
        ("naughty", 105),
        ("angry", 96),
        ("shy", 85),
        ("surprise", 72),
        ("happy", 82),
        ("sleepy", 88),
        ("wake", 58),
        ("lookaround", 107),
        ("love", 84),
        ("awkwardness", 80),
        ("eyes", 77),
        ("guffaw", 51),
        ("query", 81),
        ("Shakehead", 64),
        ("dizzy", 56),
        ("wronged", 136),
    ],
    "B": [
        ("sad", 85),
        ("naughty", 105),
        ("angry", 96),
        ("shy", 85),
        ("surprise", 72),
        ("happy", 82),
        ("sleepy", 88),
        ("wake", 58),
        ("lookaround", 107),
        ("love", 84),
        ("awkwardness", 80),
        ("eyes", 77),
        ("guffaw", 51),
        ("query", 81),
        ("Shakehead", 64),
        ("dizzy", 56),
        ("wronged", 136),
    ],
    #dog_type 的表情序列...
}


button = Button()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

# === 无网络提示图片 ===
try:
    nowifi_image_path = "/home/pi/RaspberryPi-CM5/common/pics/offline.png"
    wifi_img = Image.open(nowifi_image_path)
    nowifi_image = Image.new("RGB", wifi_img.size, SPLASH_COLOR)
    nowifi_image.paste(wifi_img, (0, 0), wifi_img)
except Exception as e:
    print(f"加载图片失败: {e}")
    nowifi_image = Image.new('RGB', (100, 100), color=(255, 0, 0))
    
# === 工具函数 ===
def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"

def get_network_range():
    ip = get_local_ip()
    if ip == "127.0.0.1":
        return [], ip
    base = ".".join(ip.split(".")[:3])
    return [f"{base}.{i}" for i in range(1, 255)], ip
    
    
def _add_client_ip():
    ip = request.remote_addr
    local = get_local_ip()
    if ip != local:
            with known_devices_lock:
                known_devices[ip] = time.time()

def update_device_presence(ip):
    if not ip or ip == "127.0.0.1":
        return
    with known_devices_lock:
        known_devices[ip] = time.time()

def sync_peers_list(peers_list):
    """【八卦协议】合并远程设备列表"""
    if not peers_list:
        return
    current_time = time.time()
    with known_devices_lock:
        for ip in peers_list:
            if ip != "127.0.0.1":
                known_devices[ip] = current_time

# === HTTP 接口 ===
@app.route('/start', methods=['GET', 'POST'])
def start_route():
    global group_perform, start_timestamp, master_ip, last_master_ping
    
    if request.method == 'POST':
        data = request.json or {}
        ts = data.get('timestamp')
        peers = data.get('peers', [])
        sync_peers_list(peers)  #同步对方的设备列表
    else:
        ts = request.args.get('timestamp')

    start_timestamp = float(ts) if ts else time.time() + SYNCHRONIZATION_DELAY
    group_perform = True
    master_ip = request.remote_addr
    last_master_ping = time.time()
    update_device_presence(master_ip)

    wait = max(0, start_timestamp - time.time())
    return jsonify({"status": "success", "wait": round(wait, 1)})

@app.route('/stop')
def stop_route():
    global group_perform, start_timestamp, master_ip, last_master_ping
    group_perform = False
    start_timestamp = None
    master_ip = None
    last_master_ping = 0
    _add_client_ip()
    return jsonify({"status": "success"})

@app.route('/exit')
def exit_route():
    global exitmark, proc
    exitmark = True
    _add_client_ip()

    # 安全停止音乐（线程安全）
    with proc_lock:
        if proc is not None:
            kill_proc_async(proc)
            proc = None  # 清空引用
    
     # 新增：强制杀死所有残留 mplayer
    force_kill_all_mplayer()

    try:
        dog.reset()
    except:
        pass
    return jsonify({"status": "exiting"})

@app.route('/status')
def status_route():
    _add_client_ip()
    return jsonify({"is_performing": group_perform, "ip": get_local_ip()})

@app.route('/devices')
def devices_route():
    update_device_presence(request.remote_addr)
    with known_devices_lock:
        d_list = list(known_devices.keys())
    return jsonify({
        "local_ip": get_local_ip(),
        "known_devices": d_list
    })

@app.route('/action')
def action_route():
    try:
        aid = int(request.args.get('id'))
        dur = float(request.args.get('duration', 3))
    except:
        return jsonify({"error": "invalid params"}), 400

    def run():
        local_ip = get_local_ip()
        start_time = time.time()
        print(f"[ACTION_START] IP={local_ip} | ActionID={aid} | StartTime={start_time:.6f}")
        dog.action(aid)
        time.sleep(dur)
        dog.stop()
        end_time = time.time()
        print(f"[ACTION_END] IP={local_ip} | ActionID={aid} | EndTime={end_time:.6f} | Duration={end_time - start_time:.3f}s")
    threading.Thread(target=run, daemon=True).start()
    _add_client_ip()
    return jsonify({"status": "started", "id": aid})

@app.route('/music')
def music_route():
    cmd = request.args.get('cmd')
    global proc
    if cmd == 'play':
        with proc_lock:
            if proc is not None:
                kill_proc_async(proc)
            proc = Popen("mplayer -really-quiet -loop 0 /home/pi/RaspberryPi-CM5/common/music/dog.mp3",
                         shell=True, preexec_fn=os.setsid, stdout=DEVNULL)
        _add_client_ip()
        return jsonify({"status": "music playing"})
    elif cmd == 'stop':
        with proc_lock:
            if proc is not None:
                kill_proc_async(proc)
                proc = None
        _add_client_ip()
        return jsonify({"status": "music stopped"})
    return jsonify({"error": "cmd must be play/stop"}), 400


# === 进程终止工具函数 ===
def kill_proc_async(p):
    if p is None:
        return
    try:
        # 确保创建进程时用了 preexec_fn=os.setsid → 有独立进程组
        os.killpg(os.getpgid(p.pid), signal.SIGTERM)  # 先发 SIGTERM
        time.sleep(0.1)
        os.killpg(os.getpgid(p.pid), signal.SIGKILL)  # 再强杀
    except ProcessLookupError:
        pass  # 进程已退出
    except Exception as e:
        print(f"[WARN] kill_proc_async failed: {e}")

def kill_proc_safe(p, timeout=0.5):
    if p is None:
        return
    try:
        p.terminate()
        p.wait(timeout=timeout)
    except Exception:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except Exception:
            pass

# === 强制终止所有 mplayer 进程 ===
def force_kill_all_mplayer():
    """强制杀死本机所有 mplayer 进程（不依赖 proc 引用）"""
    try:
        # 使用 pkill（更简洁）或 pgrep + kill
        os.system("pkill -f 'mplayer.*dog.mp3' 2>/dev/null")
        print("[CLEANUP] 已强制终止所有 mplayer 进程")
    except Exception as e:
        print(f"[ERROR] 强制 kill mplayer 失败: {e}")


# === 检查并发送退出信号 ===
def send_exit_to_all():
    with known_devices_lock:
        targets = list(known_devices)
    local_ip = get_local_ip()
    print(f"[EXIT] 正在通知 {len(targets)} 台设备退出...")
    
    def notify_one(ip):
        if ip == local_ip:
            return
        for attempt in range(3):
            try:
                requests.get(f"http://{ip}:{HTTP_PORT}/exit", timeout=1.0)
                return
            except Exception as e:
                if attempt == 2:
                    print(f"无法通知 {ip} 退出: {e}")
                else:
                    time.sleep(0.2)

    threads = []
    for ip in targets:
        t = threading.Thread(target=notify_one, args=(ip,), daemon=True)
        t.start()
        threads.append(t)

    for t in threads:
        t.join(timeout=2.0)

# === 检查网络状态===
def check_network():
    """检查网络连接状态"""
    try:
        # 主要检查是否有有效的本地IP
        local_ip = get_local_ip()
        if local_ip != "127.0.0.1":
            print(f"网络正常，本地IP: {local_ip}")
            return True
        else:
            print("无网络连接")
            return False
    except:
        return False

# === 无网络显示===
def show_network_error():
    """显示无网络界面"""
    color_white = (255, 255, 255)
    
    while True:
        if exitmark or button.press_b():
            return False
            
        try:
            network_splash = Image.new("RGB", (display.height, display.width), SPLASH_COLOR)
            network_draw = ImageDraw.Draw(network_splash)
            
            img_width, img_height = nowifi_image.size
            x_pos = (display.height - img_width) // 2
            y_pos = 40
            network_splash.paste(nowifi_image, (x_pos, y_pos))
            
            text = lal['NETWORK']['NOT_CONNECTED']
            text_width = network_draw.textlength(text, font=font2)
            x_position = (display.height - text_width) // 2
            network_draw.text((x_position, 170), text, fill=color_white, font=font2)
            display.ShowImage(network_splash)
            
            # 检查网络恢复
            for _ in range(20): 
                if exitmark or button.press_b():
                    return False
                time.sleep(0.1)
                
            if check_network():
                print("网络连接已恢复")
                return True
                
        except Exception as e:
            print(f"显示无网络提示时出错: {e}")
            time.sleep(2)

# === 表情显示===
def play_expression(expression_name, frame_count, delay=0.01):
    """
    播放指定表情动画，支持 B 键中断。
    :param expression_name: 表情文件夹名，如 "sad"
    :param frame_count: 总帧数
    :param delay: 每帧间隔（秒）
    """
    global exitmark, group_perform
    full_path = os.path.join(pic_path, expression_dir, expression_name)
    for i in range(1, frame_count + 1):
        if exitmark or not group_perform or button.press_b():
            dog.perform(0)
            return False
        try:
            img = Image.open(os.path.join(full_path, f"{i}.png"))
            display.ShowImage(img)
        except Exception as e:
            print(f"[WARN] 表情图加载失败: {expression_name}/{i}.png - {e}")
            break
        time.sleep(delay)
    return True

# === 设备发现（异步扫描）===
async def async_scan_and_gossip(session, ip, local, found, lock):
    if ip == local:
        return
    try:
        async with session.get(f"http://{ip}:{HTTP_PORT}/devices", timeout=0.3) as r:
            if r.status == 200:
                data = await r.json()
                async with lock:
                    found.append(ip)
                    # 合并对方知道的设备（gossip）
                    remote_known = data.get('known_devices', [])
                    for rip in remote_known:
                        if rip != local and rip not in found:
                            found.append(rip)
    except:
        pass
async def async_scan_devices(ip_range, local_ip):
    found = [local_ip]
    lock = asyncio.Lock()
    connector = aiohttp.TCPConnector(limit=200)
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [async_scan_and_gossip(session, ip, local_ip, found, lock) for ip in ip_range]
        await asyncio.gather(*tasks, return_exceptions=True)
    return found

def scan_devices():
    global known_devices
    ip_range, local_ip = get_network_range()
    if not ip_range:
        return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    found = loop.run_until_complete(async_scan_devices(ip_range, local_ip))
    loop.close()

    now = time.time()
    with known_devices_lock:
        for ip in found:
            known_devices[ip] = now
        known_devices[local_ip] = now  # 自己始终在线
        
        # 清理离线设备
        offline = [ip for ip, ts in known_devices.items() if now - ts > DEVICE_TTL]
        for ip in offline:
            del known_devices[ip]
# === 线程任务 ===
def http_server_thread():
    app.run(host='0.0.0.0', port=HTTP_PORT, threaded=True, use_reloader=False)

def device_discovery_thread():
    local_ip = get_local_ip()
    with known_devices_lock:
        known_devices[local_ip] = time.time() 
    
    # 初始快速扫描
    for _ in range(3):
        scan_devices()
        time.sleep(5)
    
    while not exitmark:
        scan_devices()
        time.sleep(20)

def button_check():
    global exitmark, group_perform
    while not exitmark:
        if button.press_b():
            send_exit_to_all()
            exitmark = True

        elif button.press_a():
            with known_devices_lock:
                targets = list(known_devices) + [get_local_ip()]
            if not group_perform:
                start_ts = time.time() + SYNCHRONIZATION_DELAY
                for ip in targets:
                    try:
                        requests.get(
                            f"http://{ip}:{HTTP_PORT}/start",
                            params={"timestamp": str(start_ts)},
                            timeout=0.3
                        )
                    except:
                        pass
            else:
                for ip in targets:
                    try:
                        requests.get(f"http://{ip}:{HTTP_PORT}/stop", timeout=0.3)
                    except:
                        pass

        time.sleep(0.1)

def master_watchdog():
    global master_ip, last_master_ping, group_perform, proc
    while not exitmark:
        if group_perform and master_ip and master_ip != get_local_ip():
            # 主动 ping master 的 /status
            try:
                resp = requests.get(f"http://{master_ip}:{HTTP_PORT}/status", timeout=1.0)
                if resp.status_code == 200:
                    last_master_ping = time.time()
            except:
                pass

            if time.time() - last_master_ping > 8.0:
                print("Master lost, stopping.")
                group_perform = False
                master_ip = None
                with proc_lock:
                    kill_proc_safe(proc)
                    proc = None
        time.sleep(1.0)
        
def expression_loop_thread():
    global exitmark, group_perform
    seq = EXPRESSION_SEQUENCES.get(dog_type, [])
    while not exitmark and group_perform:
        if button.press_b():
            break
        for expr_name, frame_num in seq:
            if exitmark or not group_perform:
                return
            if not play_expression(expr_name, frame_num):
                return

# === 主循环 ===
if __name__ == "__main__":
    print(f"【FIRMWARE】raw = {repr(fm1)}")
    print(f"[INFO] 本机设备型号已识别为: {dog_type}")
    print(f"【DEBUG】将执行的动作列表：{[a['name'] for a in actions_to_perform]}")
    
    #行临时调试
    time.sleep(2)
    with known_devices_lock:
        print(f"[DEBUG] 初始 known_devices = {known_devices}")
    
    threading.Thread(target=http_server_thread, daemon=True).start()
    threading.Thread(target=device_discovery_thread, daemon=True).start()
    threading.Thread(target=button_check, daemon=True).start()
    threading.Thread(target=master_watchdog, daemon=True).start() # 启动主节点监控线程

    while not exitmark:
        # 检查网络连接
        if not check_network():
            print("网络连接失败，显示无网络界面")
            if not show_network_error():
                break
            else:
                continue

        if group_perform and start_timestamp:
            wait = start_timestamp - time.time()
            if wait > 0:
                time.sleep(min(wait, 0.1))
                continue

        if group_perform:
            force_kill_all_mplayer()
            with proc_lock:
                proc = Popen("mplayer -really-quiet -loop 0 /home/pi/RaspberryPi-CM5/common/music/dog.mp3",
                             shell=True, preexec_fn=os.setsid, stdout=DEVNULL)
            
            expr_thread = threading.Thread(target=expression_loop_thread, daemon=True)
            expr_thread.start()
        
            try:
                while group_perform and not exitmark:
                  for act in actions_to_perform:
                      if not group_perform or exitmark:
                          break
                      try:
                          requests.get(f"http://127.0.0.1:{HTTP_PORT}/action?id={act['id']}&duration={act['duration']}", timeout=0.1)
                      except:
                          pass
                      end_time = time.time() + act['duration'] + 0.5
                      while time.time() < end_time:
                          if not group_perform or exitmark:
                              break
                          time.sleep(0.1)
                  
            finally:
                with proc_lock:
                    kill_proc_safe(proc)
                    proc = None
                force_kill_all_mplayer()
        else:
            try:
                dog.stop()
            except:
                pass
            try:
                splash = Image.new("RGB", (display.height, display.width), SPLASH_COLOR)
                draw = ImageDraw.Draw(splash)
                
                status_text = "任意设备按右下键开始群组表演"
                with known_devices_lock:
                    device_count = len(known_devices)
                role_text = f"发现设备: {device_count}"
                text_width = draw.textlength(status_text, font=font2)
                x_position = (display.height - text_width) // 2
                draw.text((x_position, 80), status_text, fill=(255, 255, 255), font=font2)
                
                role_width = draw.textlength(role_text, font=font2)
                role_x = (display.height - role_width) // 2
                draw.text((role_x, 110), role_text, fill=(255, 255, 255), font=font2)
                
                tip_text = "任意设备按左下键同步退出"
                tip_width = draw.textlength(tip_text, font=font2)
                tip_x = (display.height - tip_width) // 2
                draw.text((tip_x, 140), tip_text, fill=(200, 200, 200), font=font2)
                
                display.ShowImage(splash)
            except Exception as e:
                print(f"显示准备界面时出错: {e}")

    dog.reset()
    force_kill_all_mplayer()  # 新增
    print("程序退出")

# === 处理异常退出 ===
import atexit

def cleanup():
    global proc
    with proc_lock:
        if proc is not None:
            kill_proc_safe(proc)
            proc = None
    force_kill_all_mplayer()  # 新增
    try:
        dog.reset()
    except:
        pass

atexit.register(cleanup)
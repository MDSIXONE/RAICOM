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

# === 全局配置 ===
HTTP_PORT = 8080
SPLASH_COLOR = (15, 21, 46)
SYNCHRONIZATION_DELAY = 3.0
exitmark = False
group_perform = False
start_timestamp = None
known_devices = []
actions_to_perform = [
    {"id": 1, "name": "趴下", "duration": 3},
    {"id": 2, "name": "站立", "duration": 3},
    {"id": 12, "name": "坐下", "duration": 5},
    # 可根据需要保留更多动作
]

button = Button()
app = Flask(__name__)
app.config['JSON_AS_ASCII'] = False

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

# === HTTP 接口 ===
@app.route('/start')
def start_route():
    global group_perform, start_timestamp
    ts = request.args.get('timestamp')
    start_timestamp = float(ts) if ts else time.time() + SYNCHRONIZATION_DELAY
    group_perform = True
    _add_client_ip()
    wait = max(0, start_timestamp - time.time())
    return jsonify({"status": "success", "wait": round(wait, 1)})

@app.route('/stop')
def stop_route():
    global group_perform, start_timestamp
    group_perform = False
    start_timestamp = None
    _add_client_ip()
    return jsonify({"status": "success"})

@app.route('/exit')
def exit_route():
    global exitmark
    exitmark = True
    _add_client_ip()
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
    _add_client_ip()
    return jsonify({
        "local_ip": get_local_ip(),
        "known_devices": known_devices.copy()
    })

@app.route('/action')
def action_route():
    try:
        aid = int(request.args.get('id'))
        dur = float(request.args.get('duration', 3))
    except:
        return jsonify({"error": "invalid params"}), 400

    def run():
        dog.action(aid)
        time.sleep(dur)
        dog.stop()
    threading.Thread(target=run, daemon=True).start()
    _add_client_ip()
    return jsonify({"status": "started", "id": aid})

@app.route('/music')
def music_route():
    cmd = request.args.get('cmd')
    global proc
    if cmd == 'play':
        if 'proc' in globals() and proc: kill_proc(proc)
        proc = Popen("mplayer -really-quiet -loop 0 /home/pi/RaspberryPi-CM5/common/music/dog.mp3",
                     shell=True, preexec_fn=os.setsid, stdout=DEVNULL)
        _add_client_ip()
        return jsonify({"status": "music playing"})
    elif cmd == 'stop':
        if 'proc' in globals() and proc:
            kill_proc(proc)
            del proc
        _add_client_ip()
        return jsonify({"status": "music stopped"})
    return jsonify({"error": "cmd must be play/stop"}), 400

def _add_client_ip():
    ip = request.remote_addr
    local = get_local_ip()
    if ip != local and ip not in known_devices:
        known_devices.append(ip)

def kill_proc(p):
    try:
        p.terminate(); p.wait(); os.killpg(p.pid, signal.SIGTERM)
    except: pass

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


# === 设备发现（异步扫描）===
async def async_scan_single_ip(session, ip, local, found, lock):
    if ip == local: return
    try:
        async with session.get(f"http://{ip}:{HTTP_PORT}/status", timeout=0.5) as r:
            if r.status == 200:
                async with lock:
                    if ip not in found:
                        found.append(ip)
    except: pass

async def async_scan_devices(ip_range, local_ip):
    found = [local_ip]
    lock = asyncio.Lock()
    connector = aiohttp.TCPConnector(limit=200)
    timeout = aiohttp.ClientTimeout(total=20)
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = [async_scan_single_ip(session, ip, local_ip, found, lock) for ip in ip_range]
        await asyncio.gather(*tasks, return_exceptions=True)
    return found

def scan_devices():
    global known_devices
    ip_range, local_ip = get_network_range()
    if not ip_range: return

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    found = loop.run_until_complete(async_scan_devices(ip_range, local_ip))
    loop.close()

    known_devices = list(set(found + [local_ip]))

# === 线程任务 ===
def http_server_thread():
    app.run(host='0.0.0.0', port=HTTP_PORT, threaded=True, use_reloader=False)

def device_discovery_thread():
    local_ip = get_local_ip()
    if local_ip not in known_devices:
        known_devices.append(local_ip)
    for _ in range(3):  # 初始快速扫描
        scan_devices()
        time.sleep(5)
    while not exitmark:
        scan_devices()
        time.sleep(20)

def button_check():
    global exitmark, group_perform
    while not exitmark:
        if button.press_b():
            # 按下退出键：通知所有已知设备退出
            for ip in known_devices:
                try:
                    requests.get(f"http://{ip}:{HTTP_PORT}/exit", timeout=0.3)
                except:
                    pass  # 忽略失败设备
            exitmark = True  # 本机也退出

        elif button.press_a():
            if not group_perform:
                # 开始表演：先计算统一时间戳
                start_ts = time.time() + SYNCHRONIZATION_DELAY
                for ip in known_devices:
                    try:
                        requests.get(
                            f"http://{ip}:{HTTP_PORT}/start",
                            params={"timestamp": str(start_ts)},
                            timeout=0.3
                        )
                    except:
                        pass
            else:
                # 停止表演
                for ip in known_devices:
                    try:
                        requests.get(f"http://{ip}:{HTTP_PORT}/stop", timeout=0.3)
                    except:
                        pass

        time.sleep(0.1)

# === 主循环 ===
if __name__ == "__main__":
    threading.Thread(target=http_server_thread, daemon=True).start()
    threading.Thread(target=device_discovery_thread, daemon=True).start()
    threading.Thread(target=button_check, daemon=True).start()

    while not exitmark:
        if group_perform and start_timestamp:
            wait = start_timestamp - time.time()
            if wait > 0:
                time.sleep(min(wait, 0.1))
                continue

        if group_perform:
            # 启动背景音乐
            proc = Popen("mplayer -really-quiet -loop 0 /home/pi/RaspberryPi-CM5/common/music/dog.mp3",
                         shell=True, preexec_fn=os.setsid, stdout=DEVNULL)
            try:
                for act in actions_to_perform:
                    if not group_perform or exitmark: break
                    requests.get(f"http://localhost:{HTTP_PORT}/action?id={act['id']}&duration={act['duration']}")
                    time.sleep(act['duration'] + 0.5)
            finally:
                kill_proc(proc)
        else:
            try:
                dog.stop()
            except:
                pass
            try:
                splash = Image.new("RGB", (display.height, display.width), SPLASH_COLOR)
                draw = ImageDraw.Draw(splash)
                
                status_text = "任意设备按右下键开始群组表演"
                role_text = f"发现设备: {len(known_devices)}"  # ← 这就是你要的！
                
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
    print("程序退出")
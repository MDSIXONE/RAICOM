import paho.mqtt.client as mqtt
import json
import uuid
import random
import string
import time

# --- 1. 安全生成模块 ---
def generate_security_info():
    # 生成一个简短的随机UUID作为Topic的一部分
    # 结果类似: cmd/dog/a1b2c3d4
    topic_suffix = str(uuid.uuid4()).split('-')[0]
    topic = f"cmd/dog/{topic_suffix}"
    
    # 生成6位随机密码 (大写字母+数字)
    # 结果类似: 7X9P2M
    chars = string.ascii_uppercase + string.digits
    password = ''.join(random.choice(chars) for _ in range(6))
    
    return topic, password

# 生成本次开机的安全信息
MY_TOPIC, MY_PASSWORD = generate_security_info()

print("\n" + "="*50)
print("?? 机器狗接收端已启动")
print(f"?? 监听 Topic (复制到Coze):  {MY_TOPIC}")
print(f"?? 验证 Password (复制到Coze): {MY_PASSWORD}")
print("="*50 + "\n")

# --- 2. MQTT 回调函数 ---

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"? 已连接到 MQTT 服务器，正在监听: {MY_TOPIC}...")
        client.subscribe(MY_TOPIC)
    else:
        print(f"? 连接失败，错误码: {rc}")

def on_message(client, userdata, msg):
    try:
        # 1. 解析收到的 JSON
        payload_str = msg.payload.decode('utf-8')
        data = json.loads(payload_str)
        
        # 2. 获取发送来的密码和动作
        received_token = data.get("token")
        action = data.get("action")
        
        # 3. 安全校验 (核心步骤)
        if received_token != MY_PASSWORD:
            print(f"?? 拦截非法指令！密码错误: {received_token}")
            return
            
        # 4. 校验通过，执行动作
        print(f"?? 收到指令: {action} (验证通过)")
        
        # === 在这里写机器狗的硬件控制代码 ===
        if action == "move_forward":
            # dog.move(1.0)
            print(">>> 机器狗正在前进...")
        elif action == "sit_down":
            # dog.sit()
            print(">>> 机器狗坐下了...")
        # ==================================

    except Exception as e:
        print(f"? 数据解析错误: {e}")

# --- 3. 启动连接 ---
# 使用免费的 EMQX 公共服务器
BROKER = "broker.emqx.io"
PORT = 1883

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

try:
    client.connect(BROKER, PORT, 60)
    client.loop_forever() # 保持一直运行
except KeyboardInterrupt:
    print("\n程序已退出")
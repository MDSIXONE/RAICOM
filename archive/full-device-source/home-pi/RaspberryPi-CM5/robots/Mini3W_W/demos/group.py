from subprocess import Popen
import sys, os, time
from pathlib import Path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)
p = Path(__file__).resolve()
for anc in [p] + list(p.parents):
    if anc.name == 'RaspberryPi-CM5':
        sys.path.append(str(anc / 'common'))
        break
from uiutils import language,Button,display,lal,font4,font2,dog

import _thread as thread
import signal
from socket import *
import requests
from PIL import Image, ImageDraw

button = Button()
la = language()

SPLASH_COLOR = (15, 21, 46)  
TEST_NETWORK_URL = "http://www.baidu.com"  

dog.reset()

try:
    nowifi_image_path = "/home/pi/RaspberryPi-CM5/common/pics/offline.png"
    wifi_img = Image.open(nowifi_image_path)
    nowifi_image = Image.new("RGB", wifi_img.size, SPLASH_COLOR)
    nowifi_image.paste(wifi_img, (0, 0), wifi_img)
except Exception as e:
    print(f"加载图片失败: {e}")
    nowifi_image = Image.new('RGB', (100, 100), color=(255, 0, 0))
    
boardcast=False
exitmark=False

pic_path = "/home/pi/RaspberryPi-CM5/common/demos/expression/"
_canvas_x, _canvas_y = 0, 0

def display_cjk_string(splash,x, y, text, color=(255,255,255), font_size=1, scale=1, mono_space=False, auto_wrap=True, background_color=(0,0,0)):
    splash.text((x,y),text,fill =color,font = font_size) 

def show(expression_name_cs, pic_num):
    global canvas,playmark,exitmark,boardcast
    for i in range(0, pic_num):
        if playmark==True and exitmark==False and boardcast==True:
            filename=pic_path + expression_name_cs + "/" + str(i+1) + ".png"
            exp = Image.open(pic_path + expression_name_cs + "/" + str(i+1) + ".png")
            display.ShowImage(exp)
            time.sleep(0.05)
        

address = ('', 6001)
s = socket(AF_INET, SOCK_DGRAM)
s.setsockopt(SOL_SOCKET, SO_BROADCAST, 1)
s.bind(address)

def check_network():
    """检查网络连接状态"""
    max_attempts = 5
    attempt = 0
    
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
    return False

def show_network_error():
    """显示无网络界面，并检查退出条件"""
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
            
            
            for _ in range(20): 
                if exitmark or button.press_b():
                    return False
                time.sleep(0.1)
                
            
            try:
                requests.get(TEST_NETWORK_URL, timeout=1)
                print("Network connection restored")
                return True
            except:
                continue
                
        except Exception as e:
            print(f"显示无网络提示时出错: {e}")
            time.sleep(2)
            continue

def broadcast_check(*args):
    global boardcast,playmark
    while 1:
        if exitmark:
            break
        try:
            data, address = s.recvfrom(128)
            if data==b'1':
                print('broadcast 1')
                boardcast=True
            elif data==b'0':
                print('broadcast 0')
                boardcast=False
                playmark=False
        except:
            pass

def button_check(*args):
    global exitmark
    while 1:
        if button.press_b():
            print("B键按下，设置退出标志")
            exitmark=True
            break
        time.sleep(0.1)

thread.start_new_thread(broadcast_check, ())
thread.start_new_thread(button_check, ())

playmark=False

while 1:
    if exitmark:
        break
        
    print(f"boardcast: {boardcast}")
    
    
    if not check_network():
        print("网络连接失败，显示无网络界面")
        if not show_network_error():
            break
        else:
            continue  
    
    if exitmark:
        break
        
    if not exitmark:
        if boardcast:
            print('playmark:', playmark)
            if not playmark:
                playmark=True
                dog.perform(1)  
                proc=Popen("mplayer /home/pi/RaspberryPi-CM5/common/music/dog.mp3", shell=True,preexec_fn=os.setsid) 
                while 1:
                    if not playmark or not boardcast or exitmark:
                        break

                    show("sad", 14)
                    show("naughty", 14)
                    show("boring", 14)
                    show("angry", 13)
                    show("shame", 11)
                    show("surprise", 15)
                    show("happy", 12)
                    show("sleepy", 19)
                    show("seek", 12)
                    show("lookaround", 12)
                    show("love", 13)
                    show("awkwardness", 11)
                    show("eyes", 15)
                    show("guffaw", 8)
                    show("query", 7)
                    show("Shakehead", 7)
                    show("Stun", 8)
                    show("wronged", 14)
        else:
            try:
                if 'proc' in locals():
                    proc.terminate()
                    proc.wait()
                    os.killpg(proc.pid,signal.SIGTERM)
                    print('kill music')
            except:
                print('no music play')
            dog.perform(0)
            print('ready...')
            splash = Image.new("RGB", (display.height, display.width ),"black")
            draw = ImageDraw.Draw(splash)
            draw.text((100,95),lal['GROUP']['READY'],fill =(255,255,255),font = font4) 
            display.ShowImage(splash)
    
    if exitmark:
        break


print("正在退出程序...")
try:
    if 'proc' in locals():
        proc.terminate()
        proc.kill()
except:
    pass
dog.reset()  
sys.exit()
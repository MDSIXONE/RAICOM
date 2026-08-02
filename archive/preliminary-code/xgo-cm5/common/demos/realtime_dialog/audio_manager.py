import asyncio
import uuid
import queue
import threading
import time
import random
from typing import Optional, Dict, Any
import wave
import pyaudio
import signal
from dataclasses import dataclass

import config
from realtime_dialog_client import RealtimeDialogClient
from PIL import Image, ImageDraw, ImageFont
import os
import requests
@dataclass
class AudioConfig:
    """音频配置数据类"""
    format: str
    bit_size: int
    channels: int
    sample_rate: int
    chunk: int


class AudioDeviceManager:
    """音频设备管理类，处理音频输入输出"""

    def __init__(self, input_config: AudioConfig, output_config: AudioConfig):
        self.input_config = input_config
        self.output_config = output_config
        self.pyaudio = pyaudio.PyAudio()
        self.input_stream: Optional[pyaudio.Stream] = None
        self.output_stream: Optional[pyaudio.Stream] = None

    def open_input_stream(self) -> pyaudio.Stream:
        """打开音频输入流"""
        # p = pyaudio.PyAudio()
        self.input_stream = self.pyaudio.open(
            format=self.input_config.bit_size,
            channels=self.input_config.channels,
            rate=self.input_config.sample_rate,
            input=True,
            frames_per_buffer=self.input_config.chunk
        )
        return self.input_stream

    def open_output_stream(self) -> pyaudio.Stream:
        """打开音频输出流"""
        self.output_stream = self.pyaudio.open(
            format=self.output_config.bit_size,
            channels=self.output_config.channels,
            rate=self.output_config.sample_rate,
            output=True,
            frames_per_buffer=self.output_config.chunk
        )
        return self.output_stream

    def cleanup(self) -> None:
        """清理音频设备资源"""
        for stream in [self.input_stream, self.output_stream]:
            if stream:
                stream.stop_stream()
                stream.close()
        self.pyaudio.terminate()



import xgoscreen.LCD_2inch as LCD_2inch
from uiutils import Button,language
la=language()


SPLASH_COLOR = (15, 21, 46)
FONT_PATH = "/home/pi/model/msyh.ttc"
FONT_SIZE = 20
TEST_NETWORK_URL = "http://www.baidu.com"
WIFI_OFFLINE_PATH = "/home/pi/RaspberryPi-CM5/common/pics/offline.png"

try:
    font2 = ImageFont.truetype("/home/pi/model/msyh.ttc", 22)
except:
    font2 = ImageFont.load_default()
color_white = (255, 255, 255)
class DialogSession:
    """对话会话管理类"""

    def __init__(self, ws_config: Dict[str, Any]):
        self.session_id = str(uuid.uuid4())
        self.client = RealtimeDialogClient(config=ws_config, session_id=self.session_id)
        self.audio_device = AudioDeviceManager(
            AudioConfig(**config.input_audio_config),
            AudioConfig(**config.output_audio_config)
        )

        self.is_running = True
        self.is_session_finished = False
        self.is_user_querying = False
        self.is_sending_chat_tts_text = False
        self.audio_buffer = b''
        self.is_speaking = False
        self.is_listening = False
        self.is_waiting = False
        self.listening_thread = None
        self.speaking_thread = None
        self.waiting_thread = None

        self.ani_num = 0
        self.play_anmi = True
        self.quitmark = False

        signal.signal(signal.SIGINT, self._keyboard_signal)
        
        self.display = LCD_2inch.LCD_2inch()
        self.display.Init()
        self.splash = Image.new("RGB", (self.display.height, self.display.width), SPLASH_COLOR)
        self.draw = ImageDraw.Draw(self.splash)
        try:
            self.font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        except:
            self.font = ImageFont.load_default()

        self.button = Button()
        self._start_button_thread()

        try:
            wifi_img = Image.open(WIFI_OFFLINE_PATH)
            self.nowifi_image = Image.new("RGB", wifi_img.size, SPLASH_COLOR)
            self.nowifi_image.paste(wifi_img, (0, 0), wifi_img)  
        except Exception as e:
            print(f"加载图片失败: {e}")
            self.nowifi_image = Image.new("RGB", (100, 100), (255, 0, 0))  


        self.audio_queue = queue.Queue()
        self.output_stream = self.audio_device.open_output_stream()

        self.is_recording = True
        self.is_playing = True
        self.player_thread = threading.Thread(target=self._audio_player_thread)
        self.player_thread.daemon = True
        self.player_thread.start()


    def _start_button_thread(self):
        if  not self.button:
            return
            
        def check_button():
            while True:
                if self.button.press_b():
                    print("B键按下, 退出程序")
                    os._exit(0)
                time.sleep(0.1)
        thread = threading.Thread(target=check_button, daemon=True)
        thread.start()  
    def check_network(self):
        max_attempts = 5
        attempt = 0
        
        while attempt < max_attempts:
            try:
                requests.get(TEST_NETWORK_URL, timeout=1)
                print("Net is connected")
                self.network_available = True
                return True
            except:
                print(f"Network connection attempt {attempt + 1} failed")
                attempt += 1
                time.sleep(1)
        
        print("Network connection failed after 5 attempts")
        self.network_available = False
        

        if self.display and self.draw:
            self.draw.rectangle((0, 0, self.display.height, self.display.width), fill=SPLASH_COLOR)
            img_width, img_height = self.nowifi_image.size
            x_pos = (self.display.height - img_width) // 2
            y_pos = 40
            self.splash.paste(self.nowifi_image, (x_pos, y_pos))
            try:
                from ..key import load_language
                lal = load_language()
                text = lal["NETWORK"]["NOT_CONNECTED"]
            except Exception:
                text = "WIFI is not connected"
            text_width = self.draw.textlength(text, font=font2)
            x_position = (self.display.height - text_width) // 2
            self.draw.text((x_position, 170), text, fill=color_white, font=font2)
            self.display.ShowImage(self.splash)
        
        return False
    def free_anmi(self,kinds):
        if kinds == "after":
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/"
            expression_name_cs = "after"
            pic_num = 30
        elif kinds == "before":
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/"
            expression_name_cs = "before"
            pic_num = 42
        elif kinds == "recog":
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/"
            expression_name_cs = "recog"
            pic_num = 90
        elif kinds == "speak1":
            expression_name_cs = "speak"
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/speak1/"
            pic_num = 74
        elif kinds == "speak2":
            expression_name_cs = "speak"
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/speak2/"
            pic_num = 53
        elif kinds == "speak3":
            expression_name_cs = "speak"
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/speak3/"
            pic_num = 86
        elif kinds == "speak4":
            expression_name_cs = "speak"
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/speak4/"
            pic_num = 87
        elif kinds == "waiting":
            pic_path = "/home/pi/RaspberryPi-CM5/common/demos/realtime_dialog/gptfree/"
            expression_name_cs = "waiting"
            pic_num = 114

        self.ani_num += 1
        if self.ani_num >= pic_num:
            self.ani_num = 0
            
        if self.display:
            try:
                exp = Image.open(pic_path + expression_name_cs + str(self.ani_num + 1) + ".png")
                self.display.ShowImage(exp)
            except Exception as e:
                print(f"表情显示错误: {e}")
        else:
            print(f"[表情模拟] {kinds} - 帧{self.ani_num + 1}/{pic_num}")
    
    def start_listening_animation(self):
        """开始聆听表情动画"""
        if self.is_listening or self.is_speaking or self.is_waiting:
            return
        
        self.is_listening = True
        self.is_speaking = False
        self.is_waiting = False
        
        def listening_animation():
            while self.is_listening and not self.is_session_finished:
                self.free_anmi("waiting")
                time.sleep(0.02)
            
        self.listening_thread = threading.Thread(target=listening_animation, daemon=True)
        self.listening_thread.start()
        
    def stop_listening_animation(self):
        """停止聆听表情动画"""
        self.is_listening = False
        if self.listening_thread and self.listening_thread.is_alive():
            self.listening_thread.join(timeout=0.5)
            
    def start_waiting_animation(self):
        """开始等待表情动画"""
        if self.is_waiting or self.is_speaking or self.is_listening:
            return
        
        self.is_waiting = True
        self.is_speaking = False
        self.is_listening = False
        
        def waiting_animation():
            while self.is_waiting and not self.is_session_finished:
             
                time.sleep(0.02)
            
        self.waiting_thread = threading.Thread(target=waiting_animation, daemon=True)
        self.waiting_thread.start()
        
    def stop_waiting_animation(self):
        """停止等待表情动画"""
        self.is_waiting = False
        if self.waiting_thread and self.waiting_thread.is_alive():
            self.waiting_thread.join(timeout=0.5)
            
    def reset_animation_state(self):
        """重置所有动画状态，用于新对话开始时"""
        self.stop_listening_animation()
        self.stop_speaking_animation()
        self.stop_waiting_animation()
        

        self.is_listening = False
        self.is_speaking = False
        self.is_waiting = False
        self.play_anmi = False
        self.ani_num = 0
        

        while not self.audio_queue.empty():
            try:
                self.audio_queue.get_nowait()
            except queue.Empty:
                break
        self.audio_buffer = b''
        
    def speak_anmi(self):
        rn = random.randint(1, 4)
        while self.play_anmi and not self.quitmark and self.is_speaking:
            if rn == 1:
                self.free_anmi("speak1")
            elif rn == 2:
                self.free_anmi("speak2")
            elif rn == 3:
                self.free_anmi("speak3")
            elif rn == 4:
                self.free_anmi("speak4")
            time.sleep(0.02)
    def start_speaking_animation(self):
        """开始说话表情动画"""
        if self.is_speaking or self.is_listening or self.is_waiting:
            return
        
        self.is_speaking = True
        self.is_listening = False
        self.is_waiting = False
        self.play_anmi = True
        
        def speaking_animation():
            while self.is_speaking and not self.is_session_finished and self.play_anmi:
                self.speak_anmi()
                time.sleep(0.02)
            
        self.speaking_thread = threading.Thread(target=speaking_animation, daemon=True)
        self.speaking_thread.start()
        
    def stop_speaking_animation(self):
        """停止说话表情动画"""
        self.is_speaking = False
        self.play_anmi = False
        if self.speaking_thread and self.speaking_thread.is_alive():
            self.speaking_thread.join(timeout=0.5)
        
    def _audio_player_thread(self):
        """音频播放线程"""
        while self.is_playing:
            try:
            
                audio_data = self.audio_queue.get(timeout=1.0)
                if audio_data is not None:
                 
                    if not self.is_speaking:
                        self.stop_listening_animation()
                        self.stop_waiting_animation()
                        self.start_speaking_animation()
                    self.output_stream.write(audio_data)
                else:
                    
                    self.stop_speaking_animation()
            except queue.Empty:

                if self.is_speaking and self.audio_queue.empty():
                    self.stop_speaking_animation()
                time.sleep(0.1)
            except Exception as e:
                print(f"音频播放错误: {e}")
                time.sleep(0.1)

    def handle_server_response(self, response: Dict[str, Any]) -> None:
        if response == {}:
            return
        """处理服务器响应"""
        if response['message_type'] == 'SERVER_ACK' and isinstance(response.get('payload_msg'), bytes):
            # print(f"\n接收到音频数据: {len(response['payload_msg'])} 字节")
            if self.is_sending_chat_tts_text:
                return
            audio_data = response['payload_msg']
            self.audio_queue.put(audio_data)
            self.audio_buffer += audio_data
            
            self.stop_waiting_animation()
            
        elif response['message_type'] == 'SERVER_FULL_RESPONSE':
            print(f"服务器响应: {response}")
            event = response.get('event')
            payload_msg = response.get('payload_msg', {})

          
            self.stop_listening_animation()

            if event == 450:
                print(f"等待音频播放完成: {response['session_id']}")
              
                while not self.audio_queue.empty():
                    time.sleep(0.1)  
             
                self.stop_speaking_animation()
                self.start_waiting_animation()
                self.is_user_querying = True

            if event == 350 and self.is_sending_chat_tts_text and payload_msg.get("tts_type") == "chat_tts_text":
                while not self.audio_queue.empty():
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        continue
                self.is_sending_chat_tts_text = False

            if event == 459:
                pass

        elif response['message_type'] == 'SERVER_ERROR':
            print(f"服务器错误: {response['payload_msg']}")
            raise Exception("服务器错误")



    def _keyboard_signal(self, sig, frame):
        print(f"receive keyboard Ctrl+C")
        self.is_recording = False
        self.is_playing = False
        self.is_running = False
        self.quitmark = True
      
        self.stop_listening_animation()
        self.stop_speaking_animation()
        self.stop_waiting_animation()

    async def receive_loop(self):
        try:
            while True:
                response = await self.client.receive_server_response()
                self.handle_server_response(response)
                if 'event' in response and (response['event'] == 152 or response['event'] == 153):
                    print(f"receive session finished event: {response['event']}")
                    self.is_session_finished = True
                    break
        except asyncio.CancelledError:
            print("接收任务已取消")
        except Exception as e:
            print(f"接收消息错误: {e}")

    async def process_microphone_input(self) -> None:
        await self.client.say_hello()
        """处理麦克风输入"""
        stream = self.audio_device.open_input_stream()
        print("已打开麦克风，请讲话...")
        
 
        self.start_waiting_animation()

        while self.is_recording:
            try:
                # 添加exception_on_overflow=False参数来忽略溢出错误
                audio_data = stream.read(config.input_audio_config["chunk"], exception_on_overflow=False)
                save_pcm_to_wav(audio_data, "input.pcm")
                

                if not self.is_speaking:
                    if self.is_waiting:
                        self.stop_waiting_animation()
                    self.start_listening_animation()
                
                await self.client.task_request(audio_data)
                await asyncio.sleep(0.01)  
            except Exception as e:
                print(f"读取麦克风数据出错: {e}")
                await asyncio.sleep(0.1)  

    async def start(self) -> None:
        """启动对话会话"""
     
        self.reset_animation_state()
        
        if not self.check_network():
            time.sleep(1)
            return
        try:
            await self.client.connect()
            asyncio.create_task(self.process_microphone_input())
            asyncio.create_task(self.receive_loop())

            while self.is_running:
                await asyncio.sleep(0.1)

            await self.client.finish_session()
            while not self.is_session_finished:
                await asyncio.sleep(0.1)
            await self.client.finish_connection()
            await asyncio.sleep(0.1)
            await self.client.close()
            print(f"dialog request logid: {self.client.logid}")
            save_audio_to_pcm_file(self.audio_buffer, "output.pcm")
        except Exception as e:
            print(f"会话错误: {e}")
        finally:
            print("正在关闭连接...")
            self.is_recording = False
            self.is_playing = False
            self.is_running = False
            self.is_session_finished = True
            self.quitmark = True
            self.stop_listening_animation()
            self.stop_speaking_animation()
            self.stop_waiting_animation()
            self.audio_device.cleanup()


def save_pcm_to_wav(pcm_data: bytes, filename: str) -> None:
    """保存PCM数据为WAV文件"""
    with wave.open(filename, 'wb') as wf:
        wf.setnchannels(config.input_audio_config["channels"])
        wf.setsampwidth(2)  # paInt16 = 2 bytes
        wf.setframerate(config.input_audio_config["sample_rate"])
        wf.writeframes(pcm_data)


def save_audio_to_pcm_file(audio_data: bytes, filename: str) -> None:
    """保存原始PCM音频数据到文件"""
    if not audio_data:
        print("No audio data to save.")
        return
    try:
        with open(filename, 'wb') as f:
            f.write(audio_data)
    except IOError as e:
        print(f"Failed to save pcm file: {e}")

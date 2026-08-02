# coding=utf-8
# 人脸识别类
import face_recognition
import numpy as np
import sys, os,cv2
from pathlib import Path

p = Path(__file__).resolve()

from uiutils import Button, language, load_language
from PIL import Image, ImageDraw, ImageFont
import xgoscreen.LCD_2inch as LCD_2inch

la = language()
lal = load_language()

splash_theme_color = (255, 255, 255)
display = LCD_2inch.LCD_2inch()
display.Init()
display.clear()

# Init Splash
splash = Image.new("RGB", (display.height, display.width), splash_theme_color)
draw = ImageDraw.Draw(splash)
display.ShowImage(splash)
button = Button()

from picamera2 import Picamera2
picam2 = Picamera2()
picam2.configure(picam2.create_preview_configuration(main={"format": 'RGB888', "size": (320, 240)}))
picam2.start()

message_queue = []

TEXT_START_PHOTO = lal['FACE']['START_PHOTO']
TEXT_PRESS_D = lal['FACE']['PRESS_D']
TEXT_PRESS_C = lal['FACE']['PRESS_C']
TEXT_PHOTO_SUCCESS_PREFIX = lal['FACE']['PHOTO_SUCCESS_PREFIX']
TEXT_EXIT_PHOTO = lal['FACE']['EXIT_PHOTO']
TEXT_START_RECOGNITION = lal['FACE']['START_RECOGNITION']
TEXT_EXIT_PROGRAM = lal['FACE']['EXIT_PROGRAM']
TEXT_START_ENROLLMENT = lal['FACE']['START_ENROLLMENT']
TEXT_ENROLLMENT_SUCCESS = lal['FACE']['ENROLLMENT_SUCCESS']
TEXT_START_RECOG = lal['FACE']['START_RECOG']
TEXT_NO_FACE_DATA = lal['FACE']['NO_FACE_DATA']
TEXT_RETAKE_PHOTO = lal['FACE']['RETAKE_PHOTO']
TEXT_ENROLLMENT_FAILED = lal['FACE']['ENROLLMENT_FAILED']
TEXT_LOADING_PHOTO_PREFIX = lal['FACE']['LOADING_PHOTO_PREFIX']
TEXT_NO_FACE_DETECTED_PREFIX = lal['FACE']['NO_FACE_DETECTED_PREFIX']
TEXT_LOAD_FAILED_PREFIX = lal['FACE']['LOAD_FAILED_PREFIX']
TEXT_UNKNOWN = lal['FACE']['UNKNOWN']
TEXT_RECOG_MODE = lal['FACE']['RECOG_MODE']
TEXT_PRESS_C_TO_RECOG = lal['FACE']['PRESS_C_TO_RECOG']
TEXT_NO_SAVED_FACES = lal['FACE']['NO_SAVED_FACES']
TEXT_RELOAD_FACE_DATA = lal['FACE']['RELOAD_FACE_DATA']

def draw_chinese_text(img, text, position, font_path="/home/pi/RaspberryPi-CM5/common/model/msyh.ttc", font_size=20, color=(255, 0, 0)):
    """在图像上绘制中文文本"""
    try:
        img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        draw = ImageDraw.Draw(img_pil)
        font = ImageFont.truetype(font_path, font_size)
        draw.text(position, text, font=font, fill=color)
        return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    except Exception as e:
        print(f"绘制文本时出错: {e}")
        return img

def add_message(text):
    """添加消息到队列，最多保留3条"""
    global message_queue
    message_queue.append(text)
    if len(message_queue) > 3:
        message_queue.pop(0)

def display_messages(frame):
    global message_queue
    temp_frame = frame.copy()
    
    height, width = frame.shape[:2]
    y_offset = height - 80  
    
    for i, msg in enumerate(message_queue):
        temp_frame = draw_chinese_text(temp_frame, msg, (10, y_offset))
        y_offset += 25
    
    return temp_frame

def take_photo():
    global i
    add_message(TEXT_START_PHOTO)
    add_message(TEXT_PRESS_D)
    add_message(TEXT_PRESS_C)
    
    while True:
        frame = picam2.capture_array()
        frame = cv2.flip(frame, 1)
        
        frame_with_msg = display_messages(frame)
        
        b, g, r = cv2.split(frame_with_msg)
        img = cv2.merge((r, g, b))
        imgok = Image.fromarray(img)
        display.ShowImage(imgok)
        
        if button.press_d():
            cv2.imwrite(f"{i}.jpg", frame)
            add_message(TEXT_PHOTO_SUCCESS_PREFIX + f"{i}.jpg")
            i += 1
            
        if button.press_c():
            add_message(TEXT_EXIT_PHOTO)
            add_message(TEXT_START_RECOGNITION)
            return True  
            
        if button.press_b():
            add_message(TEXT_EXIT_PROGRAM)
            exit()
    
    return False

def load_photos():
    """加载所有保存的照片"""
    total_image_name = []
    total_face_encoding = []
    
    jpg_files = [f for f in os.listdir('.') if f.endswith('.jpg') and f != 'splash.jpg']
    
    if not jpg_files:
        add_message(TEXT_NO_SAVED_FACES)
        return total_image_name, total_face_encoding
    
    for fn in jpg_files:
        add_message(TEXT_LOADING_PHOTO_PREFIX + fn)
        try:
            face_encodings = face_recognition.face_encodings(face_recognition.load_image_file(fn))
            if face_encodings:
                total_face_encoding.append(face_encodings[0])
                fn_name = fn[:(len(fn) - 4)] 
                total_image_name.append(fn_name)
            else:
                add_message(TEXT_NO_FACE_DETECTED_PREFIX + fn)
        except Exception as e:
            add_message(TEXT_LOAD_FAILED_PREFIX + fn)
            print(f"错误: {e}")
    
    return total_image_name, total_face_encoding

def recognize_faces(total_image_name, total_face_encoding):
    """人脸识别函数"""
    add_message(TEXT_RECOG_MODE)
    add_message(TEXT_PRESS_C_TO_RECOG)
    
    while True:
        frame = picam2.capture_array()
        frame = cv2.flip(frame, 1)
        
        face_locations = face_recognition.face_locations(frame)
        face_encodings = face_recognition.face_encodings(frame, face_locations)
        
        for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
            name = TEXT_UNKNOWN
            
            if total_face_encoding:  
                for idx, v in enumerate(total_face_encoding):
                    match = face_recognition.compare_faces([v], face_encoding, tolerance=0.5)
                    if match[0]:
                        name = f"NO.{total_image_name[idx]}"
                        break
            
           
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 0, 255), 2)
            
           
            cv2.rectangle(frame, (left, bottom - 25), (right, bottom), (0, 0, 255), cv2.FILLED)
            
            
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.6
            text_color = (255, 255, 255)
            thickness = 1
            
            
            text_size = cv2.getTextSize(name, font, font_scale, thickness)[0]
            text_x = left + (right - left - text_size[0]) // 2
            text_y = bottom - 5
            
            cv2.putText(frame, name, (text_x, text_y), font, font_scale, text_color, thickness)
        
        frame_with_msg = display_messages(frame)
        
        b, g, r = cv2.split(frame_with_msg)
        img = cv2.merge((r, g, b))
        imgok = Image.fromarray(img)
        display.ShowImage(imgok)
        
        if button.press_c():
            add_message(TEXT_RELOAD_FACE_DATA)
            return True
        
        if button.press_d():
            return False
        
        if button.press_b():
            add_message(TEXT_EXIT_PROGRAM)
            exit()


i = 1  
photo_mode = True  

total_image_name, total_face_encoding = load_photos()

while True:
    if photo_mode:
        add_message(TEXT_START_ENROLLMENT)
        if take_photo():
            total_image_name, total_face_encoding = load_photos()
            photo_mode = False 
    else:
        if recognize_faces(total_image_name, total_face_encoding):
            total_image_name, total_face_encoding = load_photos()
        else:
            photo_mode = True
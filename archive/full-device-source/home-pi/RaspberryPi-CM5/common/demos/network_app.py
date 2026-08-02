from picamera2 import Picamera2
import pyzbar.pyzbar as pyzbar
import cv2
import time
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from uiutils import display, Button,lal,language
la=language()
def draw_chinese_text(img, text, position, font_path="/home/pi/RaspberryPi-CM5/common/model/msyh.ttc", font_size=24, color=(255, 0, 0)):

    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)


    font = ImageFont.truetype(font_path, font_size)


    draw.text(position, text, font=font, fill=color)


    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    
def draw_chinese_text_connect(img, text, position, font_path="/home/pi/RaspberryPi-CM5/common/model/msyh.ttc", font_size=18, color=(0, 255, 0)):

    img_pil = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img_pil)


    font = ImageFont.truetype(font_path, font_size)


    draw.text(position, text, font=font, fill=color)


    return cv2.cvtColor(np.array(img_pil), cv2.COLOR_RGB2BGR)
    


def create_hotspot(ssid, password):
    cmd = f'sudo nmcli dev wifi connect "{ssid}" password "{password}"'
    print(f"Executing: {cmd}")
    result = os.system(cmd)
    if result == 0:
        print("Connected successfully")
        return True
    else:
        print(f"Connection failed: {result}")
        return False

def main():
    button = Button()
    picam2 = Picamera2()
    picam2.configure(picam2.create_preview_configuration(main={"format": 'RGB888', "size": (320, 240)}))
    picam2.start()

    print("QR scanner started...")

    try:
        while True:
            img = picam2.capture_array()
            img = cv2.flip(img, 1)
            gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            barcodes = pyzbar.decode(gray_img)

            if la=="cn":
              reset_hint = "按左上键重置网络"
            else:
              reset_hint = "Reset: Top-Left Button"
            img = draw_chinese_text(img, reset_hint, (10, 10), font_size=16, color=(255, 255, 255))
            
            if la=="cn":
              qr_hint = "只支持XGO-APP的二维码扫描"
            else:
              qr_hint = "Only scans XGO-AP QR codes"
            img = draw_chinese_text(img, qr_hint, (120, 210), font_size=14, color=(255, 255, 255))
            
            if not barcodes:
                print('useless data')
                text = "{}".format(lal['NETWORK']['NOQR'])
                # Move other info to the right side
                img = draw_chinese_text(img, text, (10, 30))
            else:
                for barcode in barcodes:
                    (x, y, w, h) = barcode.rect
                    cv2.rectangle(img, (x, y), (x + w, y + h), (0, 0, 255), 2)
                    barcode_data = barcode.data.decode("utf-8")

                    if barcode_data.startswith("WIFI:"):
                        parts = barcode_data[5:].split(";")
                        wifi_config = {}
                        for part in parts:
                            if ":" in part:
                                key, value = part.split(":", 1)
                                wifi_config[key] = value

                        ssid = wifi_config.get("S", "")
                        password = wifi_config.get("P", "")

                        if ssid and password:
                      
                            text = "{}" .format(lal['NETWORK']['QR_SCANNED'])
                            # Move QR scanned info to the right side
                            img_scanned = draw_chinese_text_connect(img, text, (10, 30), color=(0, 255, 255))
                            # Add QR code support hint in bottom right
                            if la=="cn":
                              qr_hint = "只支持XGO-APP的二维码扫描"
                            else:
                              qr_hint = "Only scans XGO-AP QR codes"
                            img_scanned = draw_chinese_text(img_scanned, qr_hint, (120, 210), font_size=14, color=(255, 255, 255))
                            display_img = Image.fromarray(cv2.cvtColor(img_scanned, cv2.COLOR_BGR2RGB))
                            display.ShowImage(display_img)
                            time.sleep(0.8)  
                            
                           
                            success = create_hotspot(ssid, password)
                        
                            if success:
                              
                                text = "{}" .format(lal['NETWORK']['SUCCESS'])
                                img_success = picam2.capture_array()
                                img_success= cv2.flip(img_success, 1)
                                img_success = draw_chinese_text_connect(img_success, text, (10, 30))
                                if la=="cn":
                                  qr_hint = "只支持XGO-APP的二维码扫描"
                                else:
                                  qr_hint = "Only scans XGO-AP QR codes"
                                img_success = draw_chinese_text(img_success, qr_hint, (120, 210), font_size=14, color=(255, 255, 255))
                                display_img = Image.fromarray(cv2.cvtColor(img_success, cv2.COLOR_BGR2RGB))
                                display.ShowImage(display_img)
                                time.sleep(3)
                                return
                            else:
                            
                                img_fail = picam2.capture_array()
                                img_fail= cv2.flip(img_fail, 1)
                                text = "{}" .format(lal['NETWORK']['CONNECTION_FAILED'])

                                img_fail = draw_chinese_text_connect(img_fail, text, (10, 30), color=(255, 255, 0))

                                if la=="cn":
                                  qr_hint = "只支持XGO-APP的二维码扫描"
                                else:
                                  qr_hint = "Only scans XGO-AP QR codes"
                                img_fail = draw_chinese_text(img_fail, qr_hint, (120, 210), font_size=14, color=(255, 255, 255))
                                display_img = Image.fromarray(cv2.cvtColor(img_fail, cv2.COLOR_BGR2RGB))
                                display.ShowImage(display_img)
                                time.sleep(3)


            display_img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
            display.ShowImage(display_img)
            time.sleep(0.01)

            if button.press_c():
                ssid = 'XGO2'
                pwd = 'LuwuDynamics'
                fc = create_hotspot(ssid, pwd)
                print("Network reset to XGO2")
                # Show reset confirmation
                reset_img = picam2.capture_array()
                reset_img = cv2.flip(reset_img, 1)
                if la=="cn":
                  reset_text = "网络已重置为XGO2"
                else:
                  reset_text = "Reset to XGO2"
                reset_img = draw_chinese_text_connect(reset_img, reset_text, (10, 10), color=(0, 255, 0))
                if la=="cn":
                  qr_hint = "只支持XGO-APP的二维码扫描"
                else:
                  qr_hint = "Only scans XGO-AP QR codes"
                reset_img = draw_chinese_text(reset_img, qr_hint, (120, 210), font_size=14, color=(255, 255, 255))
                display_img = Image.fromarray(cv2.cvtColor(reset_img, cv2.COLOR_BGR2RGB))
                display.ShowImage(display_img)
                time.sleep(2)
                
            if button.press_b():
                print("B button pressed - exiting...")
                break

    except KeyboardInterrupt:
        print("Program stopped by user")
    finally:
        picam2.stop()
        print("Camera released")

if __name__ == "__main__":
    main()

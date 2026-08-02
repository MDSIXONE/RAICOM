from xgolib import XGO
import sys
from pathlib import Path
p = Path(__file__).resolve()
from uiutils import Button, font2, draw, display, splash, la, lal,dog
import time

button = Button()
dog.load_allmotor() 
dog.attitude('p', 15)
dog.translation('z', 75)

recording = False
action_count = 0

while True:

    if button.press_b():  
        dog.reset()
        break
 
    draw.rectangle((0, 0, 320, 240), fill="BLACK")
    
    content = lal["SHIJIAO"]["HELP"]
    draw.text((30, 30), content, fill="WHITE", font=font2)
    
    if action_count > 0:
        count_text = lal["SHIJIAO"]["RECORDED_PREFIX"].format(action_count)
        count_text2 = (
            lal["SHIJIAO"]["END_HINT"] if recording else lal["SHIJIAO"]["REPLAY_HINT"]
        )
        draw.text((30, 100), count_text, fill="WHITE", font=font2)
        draw.text((30, 130), count_text2, fill="WHITE", font=font2)
    
    if recording:
        mode_text = lal["SHIJIAO"]["MODE_RECORDING"]
        draw.text((30, 170), mode_text, fill="YELLOW", font=font2)
    
    display.ShowImage(splash)
    
    if button.press_a() and not recording: 
        print(lal["SHIJIAO"]["ENTER_RECORD_MODE"])
        dog.unload_motor(5)
        recording = True
        action_count = 0


    if button.press_b():  
        dog.reset()
        break
    
    if recording:

        if button.press_b():  
            dog.reset()
            break
            
        if button.press_c():  
            print(lal["SHIJIAO"]["STOP_RECORD_PREFIX"].format(action_count))
            recording = False

        else:
            action_count += 1
            print(lal["SHIJIAO"]["RECORD_ACTION_PREFIX"].format(action_count))
            dog.teach_arm("record", action_count)
            
            start_time = time.time()
            while time.time() - start_time < 2:
                if button.press_b():
                    dog.reset()
                    sys.exit(0)
                time.sleep(0.1)
    

    if button.press_b():  
        dog.reset()
        break
        
    if not recording and button.press_c() and action_count > 0:
        replay_text = lal["SHIJIAO"]["REPLAY_START"]
        
        draw.rectangle((0, 0, 320, 240), fill="BLACK")
        draw.text((30, 100), replay_text, fill="GREEN", font=font2)
        display.ShowImage(splash)
        
        print(replay_text)
        for i in range(action_count):

            if button.press_b():  
                dog.reset()
                break
                
            status_text = lal["SHIJIAO"]["PLAYING_STATUS"].format(i+1, action_count)
            
            draw.rectangle((0, 0, 240, 240), fill="BLACK")
            draw.text((30, 100), replay_text, fill="GREEN", font=font2)
            draw.text((30, 130), status_text, fill="WHITE", font=font2)
            display.ShowImage(splash)
            
            print(status_text)
            
            start_time = time.time()
            while time.time() - start_time < 2:
                if button.press_b():
                    dog.reset()
                    sys.exit(0)
                time.sleep(0.1)
                
            dog.teach_arm("play", i+1)

    if button.press_b():  
        dog.reset()
        break
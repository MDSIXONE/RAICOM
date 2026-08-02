from subprocess import Popen
import sys, os, time
from pathlib import Path

p = Path(__file__).resolve()

from uiutils import dog,display,Button

from PIL import Image

#IniT Key
button = Button()

#PIC PATH
pic_path = "/home/pi/RaspberryPi-CM5/common/demos/expression/"

def show(expression_name_cs, pic_num):
    global canvas
    for i in range(0, pic_num):
        exp = Image.open(pic_path + "dog_LM/" + expression_name_cs + "/" + str(i + 1) + ".png")
        display.ShowImage(exp)
        time.sleep(0.01)
        if button.press_b():
            dog.perform(0)
            sys.exit()

dog.reset()
dog.perform(1)

#Play Music
proc = Popen("mplayer /home/pi/RaspberryPi-CM5/common/music/Dream.mp3 -loop 0", shell=True)

while 1:
        show("sad", 85)
        show("naughty", 105)
        show("angry", 96)
        show("shy", 85)
        show("surprise", 72)
        show("happy", 82)
        show("sleepy", 88)
        show("wake", 58)
        show("lookaround", 107)
        show("love", 84)
        show("awkwardness", 80)
        show("eyes", 77)
        show("guffaw", 51)
        show("query", 81)
        show("Shakehead", 64)
        show("dizzy", 56)
        show("wronged", 136)
dog.perform(0)
proc.kill()

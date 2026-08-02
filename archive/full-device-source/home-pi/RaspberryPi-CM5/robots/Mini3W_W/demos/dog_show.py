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
        exp = Image.open(pic_path + expression_name_cs + "/" + str(i + 1) + ".png")
        display.ShowImage(exp)
        time.sleep(0.1)
        if button.press_b():
            dog.perform(0)
            sys.exit()

dog.reset()
dog.perform(1)

#Play Music
proc = Popen("mplayer /home/pi/RaspberryPi-CM5/common/music/Dream.mp3 -loop 0", shell=True)

while 1:
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
dog.perform(0)
proc.kill()

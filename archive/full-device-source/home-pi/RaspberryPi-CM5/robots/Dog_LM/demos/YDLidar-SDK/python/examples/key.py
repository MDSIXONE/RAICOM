import RPi.GPIO as GPIO
import time,os
import spidev as SPI
from PIL import Image, ImageDraw, ImageFont
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
class Button:
    def __init__(self):
        self.key1=24
        self.key2=23
        self.key4=22
        GPIO.setup(self.key1,GPIO.IN,GPIO.PUD_UP)
        GPIO.setup(self.key2,GPIO.IN,GPIO.PUD_UP)
        GPIO.setup(self.key4,GPIO.IN,GPIO.PUD_UP)
    
    def press_a(self):
        last_state=GPIO.input(self.key1)
        if last_state:
            return False
        else:
            while not GPIO.input(self.key1):
                time.sleep(0.02)
            return True

    def press_b(self):
        last_state=GPIO.input(self.key2)
        if last_state:
            return False
        else:
            while not GPIO.input(self.key2):
                time.sleep(0.02)
            os.system('pkill mplayer')
            return True
    def press_d(self):
        last_state=GPIO.input(self.key4)
        if last_state:
            return False
        else:
            while not GPIO.input(self.key4):
                time.sleep(0.02)
            return True


def get_path(path):
    base_dir = "/home/pi/RaspberryPi-CM5"  
    if path == "current":
        return base_dir
    elif path == "language_ini_path":
        language_ini_path = os.path.join(base_dir, "language", "language.ini")
        return language_ini_path
    elif path == "language_dir":
        return os.path.join(base_dir, "language")
    else:
        raise ValueError("Invalid path type specified")
        
def get_language():
    language_ini_path = get_path("language_ini_path")
    try:
        with open(language_ini_path, 'r') as f:
            language = f.read().strip()
            print(f"Current language: {language}")
            return language
    except Exception as e:
        print(f"Error reading language.ini: {e}")
        return None

def load_language():
    language = get_language()
    if language is None:
        language = "cn"  
    
    language_dir = get_path("language_dir")
    language_pack = os.path.join(language_dir, language + ".la")
    print(f"Loading language pack from: {language_pack}")
    
    try:
        with open(language_pack, 'r') as f:
            language_json = f.read()
        cleaned_json = re.sub(r'[\x00-\x1f\x7f]', '', language_json)
        language_dict = json.loads(cleaned_json)
        return language_dict
    except Exception as e:
        print(f"Error loading language file: {e}")
        return None

def language():
    base_dir = "/home/pi/RaspberryPi-CM5"
    language_ini_path = os.path.join(base_dir, "language", "language.ini")
    print(f"Language config path: {language_ini_path}")
    
    try:
        with open(language_ini_path, 'r') as f:
            language = f.read().strip()
            print(f"Current language: {language}")
        return language
    except Exception as e:
        print(f"Error reading language.ini: {e}")
        return "cn"  

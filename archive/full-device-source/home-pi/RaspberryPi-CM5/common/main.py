import sys,socket, os, time
from pathlib import Path
current_dir = os.path.dirname(os.path.abspath(__file__))
p = Path(__file__).resolve()
from uiutils import Button, show_button, display, show_battery, load_language, draw, DogTypeChecker, lcd_draw_string, color_white, font1, show_button_template, splash
from PIL import Image



current_selection = 1

# Initialize the button
button = Button()
# Load the language settings
la = load_language()

last_battery_check_time = time.time()
last_network_check_time = time.time()
is_online = False


PROJECT_ROOT = "/home/pi/RaspberryPi-CM5"


def run_program(selection):
    def action_1():
        if dog_type == "R":
            script_path = f"{PROJECT_ROOT}/robots/Rider_R/flacksocket/app.py"
        elif dog_type in ("L", "M"):
            script_path = f"{PROJECT_ROOT}/robots/Dog_LM/flacksocket/app.py"
        elif dog_type == "W":
            script_path = f"{PROJECT_ROOT}/robots/Mini3W_W/flacksocket/app.py"
        elif dog_type == "B":
            script_path = f"{PROJECT_ROOT}/robots/Walker_B/flacksocket/app.py"
        else:
            print(f"Unknown dog type: {dog_type}")
            return

        os.system(f'python3 "{script_path}"')

    def action_2():
        hotspot_script = f"{PROJECT_ROOT}/common/hotspot.py"
        show_button(0, 160, 25, "OPENING")
        time.sleep(1)
        os.system(f'python3 "{hotspot_script}"')
        show_button(0, 160, 25, "PROGRAM")

    def action_3():
        demo_script = f"{PROJECT_ROOT}/common/demoen.py" 
        show_button(210, 320, 215, "OPENING")
        display.ShowImage(splash)
        print("turn demos")
        os.system(f'python3 "{demo_script}"')

    actions = {
        1: action_1,
        2: action_2,
        3: action_3
    }

    if selection in actions:
        actions[selection]()

def main_program():
    global key_state_left, key_state_right, key_state_down, current_selection
    update_status()
    key_state_left = key_state_right = key_state_down = 0


    if button.press_a():
        key_state_down = 1
    elif button.press_c():
        key_state_left = 1
    elif button.press_d():
        key_state_right = 1
    elif button.press_b():
        print("b button, but nothing to quit")

   
    if key_state_left == 1:
        current_selection = current_selection - 1 if current_selection > 1 else 3
    elif key_state_right == 1:
        current_selection = current_selection + 1 if current_selection < 3 else 1
   
    button_ranges = [(0, 110), (110, 210), (210, 320)]
    button_texts = [
        ("RC", "PROGRAM", "TRYDEMO"),
        ("RC", "PROGRAM", "TRYDEMO"),
        ("RC", "PROGRAM", "TRYDEMO")
    ]
    
    # Get button range and labels based on current selection
    left, right = button_ranges[current_selection - 1]
    text1, text2, text3 = button_texts[current_selection - 1]
    show_button_template(left, right, text1, text2, text3)

 
    if key_state_down == 1:
        show_battery()
        run_program(current_selection)
        print(f"{current_selection} select")
      
    display.ShowImage(splash)

# Check if the device has internet connection
def is_connected(host="8.8.8.8", port=53, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
        return True
    except socket.error as ex:
        print(f"network err: {ex}")
        return False
def update_status():
    global last_battery_check_time, last_network_check_time, is_online
    now = time.time()

    if now - last_battery_check_time > 3:
        show_battery()
        last_battery_check_time = now

    if now - last_network_check_time > 3:
        is_online = is_connected()
        last_network_check_time = now

    if is_online:
        draw.bitmap((10, 0), wifiy)
    else:
        draw.rectangle((10, 0, 50, 40), fill=(15, 21, 46))

current_dir = os.path.dirname(os.path.abspath(__file__))
logo = Image.open(os.path.join(current_dir, "pics", "max.png"))
wifiy = Image.open(os.path.join(current_dir, "pics", "wifi@2x.png"))
bat = Image.open(os.path.join(current_dir, "pics", "battery.png"))


if is_connected():
    draw.bitmap((10, 0), wifiy)
    draw.bitmap((74, 49), logo)
else:
    draw.bitmap((74, 49), logo)
    print("Wifi,Unconnection")

# Check dog type and firmware version
dog_type_checker = DogTypeChecker()
dog_type, version, firmware_info = dog_type_checker.check_type()


# Display firmware info on the LCD screen
firmware_inf = dog_type_checker.check_type()[2]
lcd_draw_string(draw, 210, 133, text=firmware_inf, color=color_white, scale=font1)

show_battery()

current_selection = 1

last_check_time = time.time()

while True:
    main_program()
    


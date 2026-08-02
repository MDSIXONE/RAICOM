import sys, os, time
from pathlib import Path

p = Path(__file__).resolve()

from uiutils import Button, lal, color_bg, color_unselect, color_select, display_cjk_string, draw, display, splash, font2, color_white, font1, DogTypeChecker
from PIL import Image
# Init Key
button = Button()
dog_type_checker = DogTypeChecker()
dog_type, version, firmware_info = dog_type_checker.check_type()
path = os.getcwd()

# const
firmware_info = "v1.0"

def lcd_rect(x, y, w, h, color, thickness):
    if thickness:
        draw.rectangle([(x, y), (w, h)], color, width=thickness)
    else:
        draw.rectangle([(x, y), (w, h)], fill=None, outline=color_bg, width=2)

lcd_rect(0, 0, 320, 240, color=color_bg, thickness=-1)
display.ShowImage(splash)

# Base absolute paths for programs (externalized)

REPO_ROOT = Path("/home/pi/RaspberryPi-CM5")

COMMON_DIR = REPO_ROOT / 'common'
COMMON_DEMOS_DIR = COMMON_DIR / 'demos'
ROBOTS_DIR = REPO_ROOT / 'robots'
DOG_LM_DEMOS_DIR = ROBOTS_DIR / 'Dog_LM' / 'demos'
RIDER_R_DEMOS_DIR = ROBOTS_DIR / 'Rider_R' / 'demos'
WALKER_B_DEMOS_DIR = ROBOTS_DIR / 'Walker_B' / 'demos'
MINI3W_W_DEMOS_DIR = ROBOTS_DIR / 'Mini3W_W' / 'demos'

# Default program mapping (absolute paths)
DEFAULT_PROGRAMS = {
    'dog_show': str(COMMON_DEMOS_DIR / 'dog_show.py'),
    'ai_blockly': str(COMMON_DEMOS_DIR / 'run_blockly.py'),
    'face_mask': str(COMMON_DEMOS_DIR / 'face_mask.py'),
    'hands': str(COMMON_DEMOS_DIR / 'hands.py'),
    'face_decetion': str(COMMON_DEMOS_DIR / 'face_decetion.py'),
    'qrcode': str(COMMON_DEMOS_DIR / 'qrcode.py'),
    'speech': str(COMMON_DEMOS_DIR / 'speech' / 'speech.py'),
    'handh': str(COMMON_DEMOS_DIR / 'hp.py'),
    'color': str(COMMON_DEMOS_DIR / 'color.py'),
    'wifi_set': str(COMMON_DEMOS_DIR / 'wifi_set.py'),
    'device': str(COMMON_DEMOS_DIR / 'device.py'),
    'network': str(COMMON_DEMOS_DIR / 'WIFI' / 'wifi.py'),
    'network_app': str(COMMON_DEMOS_DIR / 'network_app.py'),
    'language': str(COMMON_DEMOS_DIR / 'language.py'),
    'volume': str(COMMON_DEMOS_DIR / 'volume.py'),
    'xiaozhi': str(COMMON_DEMOS_DIR / 'xiaozhi_test' / 'main.py'),
    'workflow': str(COMMON_DEMOS_DIR / 'receiver_workflow.py'),
    'gpt_free': str(COMMON_DEMOS_DIR / 'realtime_dialog' / 'main.py'),
    'ei': str(COMMON_DEMOS_DIR / 'speech' / 'ei.py'),
    'face_r': str(COMMON_DEMOS_DIR / 'face.py'),
    'emotion': str(COMMON_DEMOS_DIR / 'face_classification' / 'src' / 'video_emotion_color_demo.py'),
    'gamefruit': str(COMMON_DEMOS_DIR / 'fru.py'),
    'follow_person': str(COMMON_DEMOS_DIR / 'follow_person' / 'follow_person.py'),
    'aigym': str(COMMON_DEMOS_DIR / 'AI_gym' / 'test.py'),
    'group': str(COMMON_DEMOS_DIR / 'group.py'),
    'dog_Joystick': str(COMMON_DEMOS_DIR / 'dog_Joystick.py'),
    'teach_mode': str(COMMON_DEMOS_DIR / 'shijiao.py'),
    'teach_UDP': str(COMMON_DEMOS_DIR / 'shijiao_UDP.py'),
    'agent': str(COMMON_DEMOS_DIR / 'speech' / 'coze.py'),
    'follow_line': str(COMMON_DEMOS_DIR / 'follow_line.py'),
    'lidar': str(COMMON_DEMOS_DIR / 'YDLidar-SDK' / 'python' /'examples'/'radar_display.py'),

}

# Type-specific overrides/additions
PROGRAMS_BY_TYPE = {
    'R': {
        'dog_show': str(RIDER_R_DEMOS_DIR / 'dog_show.py'),
        'face_mask': str(RIDER_R_DEMOS_DIR / 'face_mask.py'),
        'hands': str(RIDER_R_DEMOS_DIR / 'hands.py'),
        'face_decetion': str(RIDER_R_DEMOS_DIR / 'face_decetion.py'),
        'speech': str(RIDER_R_DEMOS_DIR / 'speech' / 'speech.py'),
        'handh': str(RIDER_R_DEMOS_DIR / 'hp.py'),
        'color': str(RIDER_R_DEMOS_DIR / 'color.py'),
        'xiaozhi': str(RIDER_R_DEMOS_DIR / 'xiaozhi_test' / 'main.py'),
        'ei': str(RIDER_R_DEMOS_DIR / 'speech' / 'ei.py'),
        'emotion': str(RIDER_R_DEMOS_DIR / 'face_classification' / 'src' / 'video_emotion_color_demo.py'),
        'follow_person': str(RIDER_R_DEMOS_DIR / 'follow_person' / 'follow_person.py'),
        'dog_Joystick': str(RIDER_R_DEMOS_DIR / 'dog_Joystick.py'),
        'agent': str(RIDER_R_DEMOS_DIR / 'speech' / 'coze.py'),
        'ei': str(RIDER_R_DEMOS_DIR / 'speech' / 'ei.py'),
    },
    'L': {
        'dog_show': str(DOG_LM_DEMOS_DIR / 'dog_show.py'),
        'face_mask': str(DOG_LM_DEMOS_DIR / 'face_mask.py'),
        'hands': str(DOG_LM_DEMOS_DIR / 'hands.py'),
        'face_decetion': str(DOG_LM_DEMOS_DIR / 'face_decetion.py'),
        'speech': str(DOG_LM_DEMOS_DIR / 'speech' / 'speech.py'),
        'handh': str(DOG_LM_DEMOS_DIR / 'hp.py'),
        'color': str(DOG_LM_DEMOS_DIR / 'color.py'),
        'xiaozhi': str(DOG_LM_DEMOS_DIR / 'xiaozhi_test' / 'main.py'),
        'ei': str(DOG_LM_DEMOS_DIR / 'speech' / 'ei.py'),
        'emotion': str(DOG_LM_DEMOS_DIR / 'face_classification' / 'src' / 'video_emotion_color_demo.py'),
        'follow_person': str(DOG_LM_DEMOS_DIR / 'follow_person' / 'follow_person.py'),
        'dog_Joystick': str(DOG_LM_DEMOS_DIR / 'dog_Joystick.py'),
        'agent': str(DOG_LM_DEMOS_DIR / 'speech' / 'coze.py'),
        'ei': str(DOG_LM_DEMOS_DIR / 'speech' / 'ei.py'),
        'teach_mode': str(DOG_LM_DEMOS_DIR / 'shijiao.py'),
        'teach_UDP': str(DOG_LM_DEMOS_DIR / 'shijiao_UDP.py'),
        'follow_line': str(DOG_LM_DEMOS_DIR / 'follow_line.py'),
        'lidar': str(DOG_LM_DEMOS_DIR / 'YDLidar-SDK' / 'python' /'examples'/'radar_display.py'),
        'ball_catch': str(DOG_LM_DEMOS_DIR / 'ball.py'),
    },
    'M': {
        'dog_show': str(DOG_LM_DEMOS_DIR / 'dog_show.py'),
        'face_mask': str(DOG_LM_DEMOS_DIR / 'face_mask.py'),
        'hands': str(DOG_LM_DEMOS_DIR / 'hands.py'),
        'face_decetion': str(DOG_LM_DEMOS_DIR / 'face_decetion.py'),
        'speech': str(DOG_LM_DEMOS_DIR / 'speech' / 'speech.py'),
        'handh': str(DOG_LM_DEMOS_DIR / 'hp.py'),
        'color': str(DOG_LM_DEMOS_DIR / 'color.py'),
        'xiaozhi': str(DOG_LM_DEMOS_DIR / 'xiaozhi_test' / 'main.py'),
        'ei': str(DOG_LM_DEMOS_DIR / 'speech' / 'ei.py'),
        'emotion': str(DOG_LM_DEMOS_DIR / 'face_classification' / 'src' / 'video_emotion_color_demo.py'),
        'follow_person': str(DOG_LM_DEMOS_DIR / 'follow_person' / 'follow_person.py'),
        'dog_Joystick': str(DOG_LM_DEMOS_DIR / 'dog_Joystick.py'),
        'agent': str(DOG_LM_DEMOS_DIR / 'speech' / 'coze.py'),
        'ei': str(DOG_LM_DEMOS_DIR / 'speech' / 'ei.py'),
        'teach_mode': str(DOG_LM_DEMOS_DIR / 'shijiao.py'),
        'teach_UDP': str(DOG_LM_DEMOS_DIR / 'shijiao_UDP.py'),
        'follow_line': str(DOG_LM_DEMOS_DIR / 'follow_line.py'),
        'lidar': str(DOG_LM_DEMOS_DIR / 'YDLidar-SDK' / 'python' /'examples'/'radar_display.py'),
        'ball_catch': str(DOG_LM_DEMOS_DIR / 'ball.py'),
    },
    'W': {
        'dog_show': str(DOG_LM_DEMOS_DIR / 'dog_show.py'),
        'face_mask': str(DOG_LM_DEMOS_DIR / 'face_mask.py'),
        'hands': str(DOG_LM_DEMOS_DIR / 'hands.py'),
        'face_decetion': str(DOG_LM_DEMOS_DIR / 'face_decetion.py'),
        'speech': str(DOG_LM_DEMOS_DIR / 'speech' / 'speech.py'),
        'handh': str(DOG_LM_DEMOS_DIR / 'hp.py'),
        'color': str(DOG_LM_DEMOS_DIR / 'color.py'),
        'xiaozhi': str(DOG_LM_DEMOS_DIR / 'xiaozhi_test' / 'main.py'),
        'ei': str(DOG_LM_DEMOS_DIR / 'speech' / 'ei.py'),
        'emotion': str(DOG_LM_DEMOS_DIR / 'face_classification' / 'src' / 'video_emotion_color_demo.py'),
        'follow_person': str(DOG_LM_DEMOS_DIR / 'follow_person' / 'follow_person.py'),
        'dog_Joystick': str(DOG_LM_DEMOS_DIR / 'dog_Joystick.py'),
        'agent': str(DOG_LM_DEMOS_DIR / 'speech' / 'coze.py'),
        'ei': str(DOG_LM_DEMOS_DIR / 'speech' / 'ei.py'),
        'teach_mode': str(DOG_LM_DEMOS_DIR / 'shijiao.py'),
        'teach_UDP': str(DOG_LM_DEMOS_DIR / 'shijiao_UDP.py'),
        'follow_line': str(DOG_LM_DEMOS_DIR / 'follow_line.py'),
        'lidar': str(DOG_LM_DEMOS_DIR / 'YDLidar-SDK' / 'python' /'examples'/'radar_display.py'),
        'ball_catch': str(DOG_LM_DEMOS_DIR / 'ball.py'),
    },
    'B': {
        'ball_catch': str(DOG_LM_DEMOS_DIR / 'ball.py'),
    },
}

MENU_ITEM_PARENT_PATH = "/home/pi/RaspberryPi-CM5/common/pics/"
if dog_type=="R":
    MENU_ITEMS = [
            # pic kinds program show
            ("dog_show", "1movement", "dog_show", lal["DEMOEN"]["SHOW"]),
            ("blockly", "ai_blockly", "ai_blockly", lal["DEMOEN"]["BLOCKLY"]),
            ("network", "2vision", "network", lal["DEMOEN"]["NETWORK"]),
            ("network_app", "vision", "network_app", lal["DEMOEN"]["NETWORK_APP"]),
            ("xiaozhi", "3voice", "xiaozhi", lal["DEMOEN"]["XIAOZHI"]),
            ("workflow", "vision", "workflow", lal["DEMOEN"]["WORKFLOW"]),
            ("gpt_free", "4vision", "gpt_free", lal["DEMOEN"]["GPTFREE"]),
            ("speech", "5voice", "speech", lal["DEMOEN"]["SPEECH"]),
            ("ei", "6voice", "ei", lal["DEMOEN"]["GPTCMD"]),
            ("aigym","7vision","aigym",lal["DEMOEN"]["AIGYM"]),
            ("gamefruit","8vision","gamefruit",lal["DEMOEN"]["FRUITGAM"]),
            ("emotion","9vision","emotion",lal["DEMOEN"]["EMOTION"]),
            ("face_r","10vision","face_r",lal["DEMOEN"]["FACEREC"]),
            ("follow_person","11vision","follow_person",lal["DEMOEN"]["FOLLOWPERSON"]),
            ("agent", "12vision", "agent", lal["DEMOEN"]["AGENT"]),
            ("dog_Joystick", "13vision", "dog_Joystick", lal["DEMOEN"]["JOYSTICK"]),      
            ("group", "14vision", "group", lal["DEMOEN"]["GROUP"]),
            ("face_mask", "15vision", "face_mask", lal["DEMOEN"]["MASK"]),
            ("face_decetion", "16vision", "face_decetion", lal["DEMOEN"]["FACETRACK"]),
            ("hands", "17vision", "hands", lal["DEMOEN"]["HANDS"]),
            ("height", "18vision", "handh", lal["DEMOEN"]["HEIGHT"]),
            ("color", "19vision", "color", lal["DEMOEN"]["COLOR"]),
            ("qrcode", "20vision", "qrcode", lal["DEMOEN"]["QRCODE"]),
            ("wifi_set", "21vision", "wifi_set", lal["DEMOEN"]["WIFISET"]),
            ("language", "22vision", "language", lal["DEMOEN"]["LANGUAGE"]),
            ("volume", "23vision", "volume", lal["DEMOEN"]["VOLUME"]),
            ("device", "24vision", "device", lal["DEMOEN"]["DEVICE"])
        ]
if dog_type=="L" or dog_type=="M":
    MENU_ITEMS = [
            # pic kinds program show
            ("dog_show", "1movement", "dog_show", lal["DEMOEN"]["SHOW"]),
            ("blockly", "ai_blockly", "ai_blockly", lal["DEMOEN"]["BLOCKLY"]),
            ("network", "2vision", "network", lal["DEMOEN"]["NETWORK"]),
            ("network_app", "vision", "network_app", lal["DEMOEN"]["NETWORK_APP"]),
            ("xiaozhi", "3voice", "xiaozhi", lal["DEMOEN"]["XIAOZHI"]),
            ("workflow", "vision", "workflow", lal["DEMOEN"]["WORKFLOW"]),
            ("gpt_free", "4vision", "gpt_free", lal["DEMOEN"]["GPTFREE"]),
            ("speech", "5voice", "speech", lal["DEMOEN"]["SPEECH"]),
            ("ei", "6voice", "ei", lal["DEMOEN"]["GPTCMD"]),
            ("aigym","7vision","aigym",lal["DEMOEN"]["AIGYM"]),
            ("gamefruit","8vision","gamefruit",lal["DEMOEN"]["FRUITGAM"]),
            ("emotion","9vision","emotion",lal["DEMOEN"]["EMOTION"]),
            ("face_r","10vision","face_r",lal["DEMOEN"]["FACEREC"]),
            ("follow_person","11vision","follow_person",lal["DEMOEN"]["FOLLOWPERSON"]),
            ("agent", "12vision", "agent", lal["DEMOEN"]["AGENT"]),
            ("ball_catch", "13vision", "ball_catch", lal["DEMOEN"]["CATCH"]),
            ("follow_line", "14vision", "follow_line", lal["DEMOEN"]["FOLLOWLINE"]),
            ("dog_Joystick", "15vision", "dog_Joystick", lal["DEMOEN"]["JOYSTICK"]),
            ("teach_mode", "16vision", "teach_mode", lal["DEMOEN"]["TEACH"]),
            ("teach_UDP", "17vision", "teach_UDP", lal["DEMOEN"]["TEACHUDP"]),
            ("lidar", "18vision", "lidar", lal["DEMOEN"]["LIDAR"]),             
            ("group", "19vision", "group", lal["DEMOEN"]["GROUP"]),
            ("face_mask", "20vision", "face_mask", lal["DEMOEN"]["MASK"]),
            ("face_decetion", "21vision", "face_decetion", lal["DEMOEN"]["FACETRACK"]),
            ("hands", "22vision", "hands", lal["DEMOEN"]["HANDS"]),
            ("height", "23vision", "handh", lal["DEMOEN"]["HEIGHT"]),
            ("color", "24vision", "color", lal["DEMOEN"]["COLOR"]),
            ("qrcode", "25vision", "qrcode", lal["DEMOEN"]["QRCODE"]),
            ("wifi_set", "26vision", "wifi_set", lal["DEMOEN"]["WIFISET"]),
            ("language", "27vision", "language", lal["DEMOEN"]["LANGUAGE"]),
            ("volume", "28vision", "volume", lal["DEMOEN"]["VOLUME"]),
            ("device", "29vision", "device", lal["DEMOEN"]["DEVICE"])
        ]

if dog_type=="W":
    MENU_ITEMS = [
            # pic kinds program show
            ("dog_show", "1movement", "dog_show", lal["DEMOEN"]["SHOW"]),
            ("blockly", "ai_blockly", "ai_blockly", lal["DEMOEN"]["BLOCKLY"]),
            ("network", "2vision", "network", lal["DEMOEN"]["NETWORK"]),
            ("network_app", "vision", "network_app", lal["DEMOEN"]["NETWORK_APP"]),
            ("xiaozhi", "3voice", "xiaozhi", lal["DEMOEN"]["XIAOZHI"]),
            ("workflow", "vision", "workflow", lal["DEMOEN"]["WORKFLOW"]),
            ("gpt_free", "4vision", "gpt_free", lal["DEMOEN"]["GPTFREE"]),
            ("speech", "5voice", "speech", lal["DEMOEN"]["SPEECH"]),
            ("ei", "6voice", "ei", lal["DEMOEN"]["GPTCMD"]),
            ("aigym","7vision","aigym",lal["DEMOEN"]["AIGYM"]),
            ("gamefruit","8vision","gamefruit",lal["DEMOEN"]["FRUITGAM"]),
            ("emotion","9vision","emotion",lal["DEMOEN"]["EMOTION"]),
            ("face_r","10vision","face_r",lal["DEMOEN"]["FACEREC"]),
            ("follow_person","11vision","follow_person",lal["DEMOEN"]["FOLLOWPERSON"]),
            ("agent", "12vision", "agent", lal["DEMOEN"]["AGENT"]),
            ("ball_catch", "13vision", "ball_catch", lal["DEMOEN"]["CATCH"]),
            ("follow_line", "14vision", "follow_line", lal["DEMOEN"]["FOLLOWLINE"]),
            ("dog_Joystick", "15vision", "dog_Joystick", lal["DEMOEN"]["JOYSTICK"]),
            ("teach_mode", "16vision", "teach_mode", lal["DEMOEN"]["TEACH"]),
            ("teach_UDP", "17vision", "teach_UDP", lal["DEMOEN"]["TEACHUDP"]),
            ("lidar", "18vision", "lidar", lal["DEMOEN"]["LIDAR"]),             
            ("group", "19vision", "group", lal["DEMOEN"]["GROUP"]),
            ("face_mask", "20vision", "face_mask", lal["DEMOEN"]["MASK"]),
            ("face_decetion", "21vision", "face_decetion", lal["DEMOEN"]["FACETRACK"]),
            ("hands", "22vision", "hands", lal["DEMOEN"]["HANDS"]),
            ("height", "23vision", "handh", lal["DEMOEN"]["HEIGHT"]),
            ("color", "24vision", "color", lal["DEMOEN"]["COLOR"]),
            ("qrcode", "25vision", "qrcode", lal["DEMOEN"]["QRCODE"]),
            ("wifi_set", "26vision", "wifi_set", lal["DEMOEN"]["WIFISET"]),
            ("language", "27vision", "language", lal["DEMOEN"]["LANGUAGE"]),
            ("volume", "28vision", "volume", lal["DEMOEN"]["VOLUME"]),
            ("device", "29vision", "device", lal["DEMOEN"]["DEVICE"])
        ]
if dog_type=="B":
    MENU_ITEMS = [
            # pic kinds program show
            ("dog_show", "1movement", "dog_show", lal["DEMOEN"]["SHOW"]),
            ("blockly", "ai_blockly", "ai_blockly", lal["DEMOEN"]["BLOCKLY"]),
            ("network", "2vision", "network", lal["DEMOEN"]["NETWORK"]),
            ("network_app", "vision", "network_app", lal["DEMOEN"]["NETWORK_APP"]),
            ("xiaozhi", "3voice", "xiaozhi", lal["DEMOEN"]["XIAOZHI"]),
            ("workflow", "vision", "workflow", lal["DEMOEN"]["WORKFLOW"]),
            ("gpt_free", "4vision", "gpt_free", lal["DEMOEN"]["GPTFREE"]),
            ("speech", "5voice", "speech", lal["DEMOEN"]["SPEECH"]),
            ("ei", "6voice", "ei", lal["DEMOEN"]["GPTCMD"]),
            ("aigym","7vision","aigym",lal["DEMOEN"]["AIGYM"]),
            ("gamefruit","8vision","gamefruit",lal["DEMOEN"]["FRUITGAM"]),
            ("emotion","9vision","emotion",lal["DEMOEN"]["EMOTION"]),
            ("face_r","10vision","face_r",lal["DEMOEN"]["FACEREC"]),
            ("follow_person","11vision","follow_person",lal["DEMOEN"]["FOLLOWPERSON"]),
            ("agent", "12vision", "agent", lal["DEMOEN"]["AGENT"]),
            ("ball_catch", "13vision", "ball_catch", lal["DEMOEN"]["CATCH"]),
            ("follow_line", "14vision", "follow_line", lal["DEMOEN"]["FOLLOWLINE"]),
            ("dog_Joystick", "15vision", "dog_Joystick", lal["DEMOEN"]["JOYSTICK"]),
            ("teach_mode", "16vision", "teach_mode", lal["DEMOEN"]["TEACH"]),
            ("teach_UDP", "17vision", "teach_UDP", lal["DEMOEN"]["TEACHUDP"]),
            ("lidar", "18vision", "lidar", lal["DEMOEN"]["LIDAR"]),             
            ("group", "19vision", "group", lal["DEMOEN"]["GROUP"]),
            ("face_mask", "20vision", "face_mask", lal["DEMOEN"]["MASK"]),
            ("face_decetion", "21vision", "face_decetion", lal["DEMOEN"]["FACETRACK"]),
            ("hands", "22vision", "hands", lal["DEMOEN"]["HANDS"]),
            ("height", "23vision", "handh", lal["DEMOEN"]["HEIGHT"]),
            ("color", "24vision", "color", lal["DEMOEN"]["COLOR"]),
            ("qrcode", "25vision", "qrcode", lal["DEMOEN"]["QRCODE"]),
            ("wifi_set", "26vision", "wifi_set", lal["DEMOEN"]["WIFISET"]),
            ("language", "27vision", "language", lal["DEMOEN"]["LANGUAGE"]),
            ("volume", "28vision", "volume", lal["DEMOEN"]["VOLUME"]),
            ("device", "29vision", "device", lal["DEMOEN"]["DEVICE"])
        ]
SELECT_BOX = [80, 68]
BASE_X = [0, 80, 160, 240]
BASE_Y = [36, 104, 172]

# Generate coordinates
MENU_ITEM_COORD = [[x, y, SELECT_BOX[0], SELECT_BOX[1]] for y in BASE_Y for x in BASE_X]
MENU_TEXT_COORD = [[x, y + 48] for y in BASE_Y for x in BASE_X]  
MENU_PIC_COORD = [[x + 26, y + 11] for y in BASE_Y for x in BASE_X] 

MENU_TOTAL_ITEMS = len(MENU_ITEMS) - 1
MENU_TOTAL_PAGES = MENU_TOTAL_ITEMS // 12
MENU_CURRENT_SELECT = 0
MENU_PAGE_SWAP_COUNT = 0

def draw_item(row, type, realindex):
    item_coord = MENU_ITEM_COORD[row]
    pic_coord = MENU_PIC_COORD[row]
    text_coord = MENU_TEXT_COORD[row]
    item_text = MENU_ITEMS[realindex][3]
    text_len = len(item_text)
    text_offset = (10 - text_len) * 2 - 2
    
    # Adjust row for clearup/cleardown
    if type == "clearup":
        row -= 1
    elif type == "cleardown":
        row += 1
        if realindex == 28:
            realindex = 0
    
    # Get coordinates again if row changed
    if type in ("clearup", "cleardown"):
        item_coord = MENU_ITEM_COORD[row]
        pic_coord = MENU_PIC_COORD[row]
        text_coord = MENU_TEXT_COORD[row]
    
    if type == "selected":
        rect_color = color_select
        text_color = color_white
        bg_color = color_select
        thickness = 1
    else:  # unselected, clearup, cleardown
        rect_color = color_bg
        text_color = color_unselect
        bg_color = color_bg
        thickness = -1
    

    lcd_rect(
        item_coord[0],
        item_coord[1],
        item_coord[2] + item_coord[0],
        item_coord[3] + item_coord[1],
        color=rect_color,
        thickness=thickness
    )
    

    picpath = f"/home/pi/RaspberryPi-CM5/common/pics/{MENU_ITEMS[realindex][0]}.png"
    nav_up = Image.open(picpath)
    draw.bitmap((pic_coord[0], pic_coord[1]), nav_up)
    
    display_cjk_string(
        draw,
        text_coord[0] + text_offset,
        text_coord[1],
        item_text,
        font_size=font1,
        color=text_color,
        background_color=bg_color
    )

def clear_page():
    print("clear page")
    lcd_rect(0, 36, 320, 240, color=color_bg, thickness=-1)


def draw_title_bar(index):
    lcd_rect(0, 0, 320, 35, color=color_bg, thickness=-1)
    draw.line((0, 35, 320, 35), color_unselect)
    display_cjk_string(
        draw,
        77,
        7,
        lal["DEMOEN"]["EXAMPLES"],
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )
    display_cjk_string(
        draw,
        203,
        7,
        str(index + 1) + "/" + str(MENU_TOTAL_ITEMS + 1),
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )


def draw_title_open():
    lcd_rect(0, 0, 320, 35, color=color_bg, thickness=-1)
    draw.line((0, 35, 320, 35), color_unselect)
    display_cjk_string(
        draw,
        85,
        7,
        lal["DEMOEN"]["OPENING"],
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )


def draw_title_error():
    lcd_rect(0, 0, 320, 35, color=color_bg, thickness=-1)
    draw.line((0, 35, 320, 35), color_unselect)
    display_cjk_string(
        draw,
        85,
        7,
        lal["DEMOEN"]["FAIL"],
        font_size=font2,
        color=color_white,
        background_color=color_bg,
    )

draw_title_bar(0)

for i in range(0, 12):
    draw_item(i, "unselected", i)
display.ShowImage(splash)
draw_item(0, "selected", 0)

display.ShowImage(splash)

inputkey = ""
while True:

    key_state_left = 0
    key_state_down = 0
    key_state_right = 0

    if button.press_a():
        key_state_down = 1
    elif button.press_c():
        key_state_left = 1
    elif button.press_d():
        key_state_right = 1
    elif button.press_b():
        os.system("pkill mplayer")
        break

    if key_state_left == 1:
        clear_page()
        if MENU_CURRENT_SELECT % 12 == 0:
            if MENU_PAGE_SWAP_COUNT == 0:
                MENU_PAGE_SWAP_COUNT = MENU_TOTAL_PAGES
                MENU_CURRENT_SELECT = MENU_TOTAL_ITEMS
            else:
                MENU_PAGE_SWAP_COUNT -= 1
                MENU_CURRENT_SELECT -= 1
        else:
            MENU_CURRENT_SELECT -= 1

        print(
            str(MENU_CURRENT_SELECT)
            + ", \t"
            + str(MENU_CURRENT_SELECT % 12)
            + ", "
            + str(MENU_PAGE_SWAP_COUNT)
        )

        draw_title_bar(MENU_CURRENT_SELECT)

        if MENU_PAGE_SWAP_COUNT == MENU_TOTAL_PAGES:
            for i in range(MENU_TOTAL_PAGES * 12, MENU_TOTAL_ITEMS + 1, 1):
                print(i)
                draw_item(i % 12, "unselected", i)
        else:
            for i in range(
                MENU_PAGE_SWAP_COUNT * 12, MENU_PAGE_SWAP_COUNT * 12 + 12, 1
            ):
                print(i)
                draw_item(i % 12, "unselected", i)

        draw_item(MENU_CURRENT_SELECT % 12, "selected", MENU_CURRENT_SELECT)

    if key_state_right == 1:
        clear_page()
        if MENU_CURRENT_SELECT == MENU_TOTAL_ITEMS:
            MENU_PAGE_SWAP_COUNT = 0
            MENU_CURRENT_SELECT = 0
        elif MENU_CURRENT_SELECT % 12 == 11:
            MENU_PAGE_SWAP_COUNT += 1
            MENU_CURRENT_SELECT += 1
        else:
            MENU_CURRENT_SELECT += 1

        print(
            str(MENU_CURRENT_SELECT)
            + ", \t"
            + str(MENU_CURRENT_SELECT % 12)
            + ", "
            + str(MENU_PAGE_SWAP_COUNT)
        )

        draw_title_bar(MENU_CURRENT_SELECT)

        if MENU_PAGE_SWAP_COUNT == MENU_TOTAL_PAGES:
            for i in range(MENU_TOTAL_PAGES * 12, MENU_TOTAL_ITEMS + 1, 1):
                print(i)
                draw_item(i % 12, "unselected", i)
        else:
            for i in range(
                MENU_PAGE_SWAP_COUNT * 12, MENU_PAGE_SWAP_COUNT * 12 + 12, 1
            ):
                print(i)
                draw_item(i % 12, "unselected", i)

        draw_item(MENU_CURRENT_SELECT % 12, "selected", MENU_CURRENT_SELECT)

    if key_state_down == 1:
        try:
            display.ShowImage(splash)
            key = MENU_ITEMS[MENU_CURRENT_SELECT][2]
            print("Running: " + key)
            draw_title_open()

            # Resolve program path by type, then fallback to default
            type_map = PROGRAMS_BY_TYPE.get(dog_type, {})
            prog_path = type_map.get(key) or DEFAULT_PROGRAMS.get(key)

            if prog_path and os.path.exists(prog_path):
                cmd = f"python3 \"{prog_path}\""
                if key == "network":
                    cmd = f"sudo  $(which python) \"{prog_path}\" "
                os.system(cmd)
            else:
                print(f"Program not found for type {dog_type}: {key} -> {prog_path}")

            print("program done")
            draw_title_bar(MENU_CURRENT_SELECT)
        except BaseException as e:
            print(str(e))
            draw_title_bar(MENU_CURRENT_SELECT)
        print("Key C Pressed.")
        time.sleep(0.5)
        draw_title_bar(MENU_CURRENT_SELECT)

    display.ShowImage(splash)

print("quit")

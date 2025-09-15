import lvgl as lv
import utime
import sys_bus
from usr.lcd import *
from machine import Timer
import log

log.basicConfig(level=log.INFO)
logger = log.getLogger("UI")


screen = lv.obj()
screen.set_size(240,240)
screen.set_scrollbar_mode(lv.SCROLLBAR_MODE.OFF)

# Set style for screen, Part: lv.PART.MAIN, State: lv.STATE.DEFAULT.
screen.set_style_bg_opa(255, lv.PART.MAIN|lv.STATE.DEFAULT)
screen.set_style_bg_color(lv.color_hex(0x000000), lv.PART.MAIN|lv.STATE.DEFAULT)
screen.set_style_bg_grad_dir(lv.GRAD_DIR.NONE, lv.PART.MAIN|lv.STATE.DEFAULT)

# Create flex flow
screen.center()
screen.set_flex_align(lv.FLEX_ALIGN.SPACE_EVENLY, lv.FLEX_ALIGN.CENTER, lv.FLEX_ALIGN.CENTER)
screen.set_flex_flow(lv.FLEX_FLOW.COLUMN)
# Create screen_gif
screen_gif = lv.gif(screen)
screen_gif.set_src("U:/media/neutral.gif")
screen_gif.set_style_bg_color(lv.color_hex(0x000000), 0)  # 黑色背景
screen_gif.set_style_bg_opa(lv.OPA.COVER, 0)
screen_gif.set_size(240, 240)
def update_emoji(topic,msg):
    screen_gif.set_style_opa(lv.OPA.TRANSP, 0)
    
    # 定义支持的表情列表
    supported_emojis = [
        "angry", "confident", "cool", "crying", "delicious",
        "funny", "happy", "kissy", "laughing", "loving", "neutral",
        "sleepy", "sad", "surprised", "winking", "thinking", "relaxed",
        "shocked", "embarrassed", "confused"
    ]
    
    # 检查消息是否为支持的表情
    if msg in supported_emojis:
        # 使用字符串拼接构建路径
        gif_path = "U:/media/" + msg + ".gif"
        screen_gif.set_src(gif_path)
    else:
       gif_path = "U:/media/neutral.gif"
       screen_gif.set_src(gif_path)
    
    # utime.sleep_ms(20)
    screen_gif.set_style_opa(lv.OPA.COVER, 0)


sys_bus.subscribe("update_emoji",update_emoji)

class lvglManager:
    #@staticmethod
    def __init__(self):
        lv.scr_load(screen)



        


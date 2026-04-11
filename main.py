import os
import time
import mss
import cv2
import pygetwindow as gw
import pydirectinput as pyin
import pyperclip

import numpy as np
import pandas as pd

# Ganti Path mu
pw_path = r"C:\Users\User\Desktop\Pixel Worlds.url"

print("kerja jep...")
os.startfile(pw_path)

while not gw.getWindowsWithTitle("Pixel World"):
    print("wait..")
    time.sleep(1)

windows = gw.getWindowsWithTitle("Pixel World")[0]

if windows.isMinimized:
    windows.restore()
windows.activate()

# take the coordinates pixelworld window only (not the entire window)
monitor = {
    "left": windows.left,
    "top": windows.top,
    "width": windows.width,
    "height": windows.height
}

sct = mss.mss()

# gray = return screenshoot grayscale, bgr = return gambar full color
def get_gray_ss(monitor):
    screenshot = sct.grab(monitor)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)
def get_bgr_ss(monitor):
    screenshot = sct.grab(monitor)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)

# for input text ingame
def type_in_game(text):
    pyperclip.copy(text)
    pyin.keyDown('ctrl')
    pyin.press('v')
    pyin.keyUp('ctrl')

# take img and templateimg, compare it and return the coordinate if matched
def get_match_template_coor(img, template, method): 
    h, w = template.shape[:-1]
    match = cv2.matchTemplate(img, template, method)
    loc = np.where(match >= 0.8)
    if len(loc[0]) > 0:
        y = loc[0][0] + h // 2
        x = loc[1][0] + w // 2
        return (x, y)                  # didnt return window relative coor
    else: return 0

#looping until get to homepage pixelworld
img = get_bgr_ss(monitor)
world_name_field_template = cv2.imread("template/world_name_input.png")
world_field_coor = get_match_template_coor(img, world_name_field_template, cv2.TM_CCOEFF_NORMED)
while not world_field_coor:
    print("not found..")
    time.sleep(1)
    img = get_bgr_ss(monitor)
    world_field = get_match_template_coor(img, world_name_field_template, cv2.TM_CCOEFF_NORMED)


# enter the world
pyin.click(world_field_coor[0] + monitor["left"], world_field_coor + monitor["top"])
time.sleep(.5)

type_in_game("MAVING")
time.sleep(.5)
pyin.press("enter")


# cv2.imwrite("debug.png", img)



# Masih gamatch templatenya jep, coba nanti di scale gambarnya dari 0.2 sampe 1.5
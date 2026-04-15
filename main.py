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
pw_path = r"C:\Users\Zefhana Ananda\OneDrive\Desktop\Pixel Worlds.url"

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

# Function to auto-enter world
def auto_enter_world(world_name="fish1", max_retries=3):
    """
    Otomatis masuk ke world dengan nama yang diberikan
    Return True jika berhasil, False jika gagal
    """
    global world_field_coor
    
    for attempt in range(max_retries):
        try:
            print(f"\n🌍 Masuk ke world '{world_name}' (attempt {attempt + 1}/{max_retries})...")
            
            # Cari world name field
            img = get_bgr_ss(monitor)
            world_field_coor = get_match_template_coor(img, world_name_field_template, cv2.TM_CCOEFF_NORMED)
            
            if not world_field_coor:
                print("⚠ World name field tidak ditemukan, retry...")
                time.sleep(1)
                continue
            
            # Click pada world name input field
            click_x = world_field_coor[0] + monitor["left"]
            click_y = world_field_coor[1] + monitor["top"]
            
            print(f"📍 Clicking at ({click_x}, {click_y})...")
            pyin.click(click_x, click_y)
            time.sleep(0.5)
            
            # Type world name
            print(f"⌨️ Typing world name: {world_name}")
            type_in_game(world_name)
            time.sleep(0.5)
            
            # Press enter
            print("🎯 Pressing ENTER...")
            pyin.press("enter")
            time.sleep(2)
            
            print(f"✅ Berhasil masuk ke world '{world_name}'!")
            return True
            
        except Exception as e:
            print(f"❌ Error saat masuk world: {e}")
            time.sleep(1)
    
    print(f"❌ Gagal masuk ke world '{world_name}' setelah {max_retries} kali coba")
    return False

# Auto-enter world
auto_enter_world("fish1")

time.sleep(2)

# STRIKE DETECTION & AUTO NARIK (SPACE)
print("Loading strike templates...")

# Load templates untuk strike detection
strike_templates = {}

# Coba load bite_the_baits.png sebagai indikator strike
try:
    strike_templates["bite"] = cv2.imread("template/bite_the_baits.png")
    print("✓ Loaded bite_the_baits.png")
except:
    print("⚠ bite_the_baits.png not found")

# Load semua template dari folder baits/ (1.png - 8.png)
for i in range(1, 9):
    try:
        template_path = f"template/baits/{i}.png"
        strike_templates[f"strike_{i}"] = cv2.imread(template_path)
        print(f"✓ Loaded {template_path}")
    except Exception as e:
        print(f"⚠ Failed to load template/baits/{i}.png: {e}")

print(f"Total templates loaded: {len(strike_templates)}")

# Function to detect any strike template with multi-scale matching
def detect_strike(img, templates):
    """
    Scan image untuk mendeteksi strike pattern dengan scaling 0.2 - 1.5 (10 steps)
    Return True jika ada yang match, False otherwise
    """
    # 10 scale steps dari 0.2 sampai 1.5
    scales = np.linspace(0.1, 2, 12)
    
    for template_name, template in templates.items():
        if template is None:
            continue
        
        orig_h, orig_w = template.shape[:-1]
        
        # Try each scale
        for scale in scales:
            # Resize template sesuai scale
            new_w = int(orig_w * scale)
            new_h = int(orig_h * scale)
            
            # Skip jika template terlalu kecil
            if new_w < 5 or new_h < 5:
                continue
            
            scaled_template = cv2.resize(template, (new_w, new_h))
            
            # Template matching
            match = cv2.matchTemplate(img, scaled_template, cv2.TM_CCOEFF_NORMED)
            loc = np.where(match >= 0.6)  # Threshold 0.6
            
            if len(loc[0]) > 0:
                print(f"⚡ STRIKE DETECTED: {template_name} (scale: {scale:.2f})")
                return True
    
    return False

# Main loop - terus monitor dan respond ke strike
print("\n🎣 Monitoring untuk strike...")
print("Tekan CTRL+C untuk stop\n")

strike_cooldown = 0
last_strike_time = 0

try:
    while True:
        img = get_bgr_ss(monitor)
        
        # Deteksi strike
        if detect_strike(img, strike_templates):
            current_time = time.time()
            # Cooldown 0.5 detik untuk avoid multiple triggers
            if current_time - last_strike_time > 0.5:
                print("🎯 NARIK! (Press SPACE)")
                pyin.press("space")
                last_strike_time = current_time
                time.sleep(0.2)  # Delay before next check
        
        time.sleep(0.1)  # Check setiap 100ms

except KeyboardInterrupt:
    print("\n\n❌ Script stopped by user")
    sct.close()
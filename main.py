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
    """Direct keyboard press - reliable untuk game"""
    for char in text:
        pyin.press(char)
        time.sleep(0.1)  # 0.1 detik per karakter - balanced antara speed & reliability

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
    print("Menunggu homepage pixelworld...")
    time.sleep(1)
    img = get_bgr_ss(monitor)
    world_field_coor = get_match_template_coor(img, world_name_field_template, cv2.TM_CCOEFF_NORMED)

# Function to auto-enter world
def auto_enter_world(world_name="fish1", max_retries=3):
    """
    Otomatis masuk ke world dengan nama yang diberikan
    Return True jika berhasil, False jika gagal
    """
    global world_name_field_template
    
    for attempt in range(max_retries):
        try:
            print(f"\n🌍 Masuk ke world '{world_name}' (attempt {attempt + 1}/{max_retries})...")
            
            # Cari world name field
            img = get_bgr_ss(monitor)
            world_field_coor = get_match_template_coor(img, world_name_field_template, cv2.TM_CCOEFF_NORMED)
            
            if not world_field_coor:
                print("⚠ World name field tidak ditemukan, wait...")
                time.sleep(1)
                continue
            
            # Click pada world name input field dengan offset yang sudah benar
            # world_field_coor sudah relative ke window, monitor["left"] & ["top"] adalah window position
            click_x = world_field_coor[0] + monitor["left"]
            click_y = world_field_coor[1] + monitor["top"]
            
            print(f"📍 Clicking pada input field at ({click_x}, {click_y})...")
            pyin.click(click_x, click_y)
            time.sleep(0.5)
            
            # Clear field dengan aggressive clearing (triple click + select all + delete)
            print("🗑️ Clearing field...")
            # Triple click untuk select all
            pyin.click(click_x, click_y)
            pyin.click(click_x, click_y)
            pyin.click(click_x, click_y)
            time.sleep(0.3)
            
            # Ctrl+A untuk select
            pyin.keyDown('ctrl')
            pyin.press('a')
            pyin.keyUp('ctrl')
            time.sleep(0.2)
            
            # Delete semua dengan delete + backspace
            pyin.press('delete')
            time.sleep(0.1)
            pyin.press('backspace')
            time.sleep(0.3)
            
            # Type world name
            print(f"⌨️ Typing world name: {world_name}")
            type_in_game(world_name)
            time.sleep(1)  # Longer delay untuk memastikan text ter-input
            
            # Cari dan click tombol "Join" (bukan press enter)
            print("🎯 Mencari tombol Join...")
            join_button_template = cv2.imread("template/join_button.png") if os.path.exists("template/join_button.png") else None
            
            if join_button_template is not None:
                # Jika ada template untuk join button
                img = get_bgr_ss(monitor)
                join_coor = get_match_template_coor(img, join_button_template, cv2.TM_CCOEFF_NORMED)
                if join_coor:
                    join_x = join_coor[0] + monitor["left"]
                    join_y = join_coor[1] + monitor["top"]
                    print(f"📍 Clicking Join button at ({join_x}, {join_y})...")
                    pyin.click(join_x, join_y)
                else:
                    # Fallback ke press enter
                    print("Join button tidak ditemukan, fallback ke ENTER...")
                    pyin.press("enter")
            else:
                # Tidak ada template, langsung press enter (atau try press enter multiple times)
                print("📌 Pressing ENTER untuk submit...")
                pyin.press("enter")
                time.sleep(0.2)
                pyin.press("enter")  # Double press untuk memastikan
                
            time.sleep(3)
            
            print(f"✅ Berhasil masuk ke world '{world_name}'!")
            return True
            
        except Exception as e:
            print(f"❌ Error saat masuk world: {e}")
            import traceback
            traceback.print_exc()
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

# FOKUS HANYA ke bite_the_baits.png
try:
    bite_template = cv2.imread("template/bite_the_baits.png")
    if bite_template is None:
        print("❌ ERROR: bite_the_baits.png tidak ditemukan!")
    else:
        strike_templates["bite"] = bite_template
        print("✓ Loaded bite_the_baits.png")
        print(f"  Template size: {bite_template.shape}")
except Exception as e:
    print(f"❌ Error loading bite_the_baits.png: {e}")

# SKIP baits folder templates (untuk fokus debugging)
print(f"Total templates loaded: {len(strike_templates)}")

# Function to detect any strike template with multi-scale matching
def detect_strike(img, templates, frame_count=0):
    """
    Scan image untuk mendeteksi strike pattern dengan scaling 0.1 - 2.0 (12 steps)
    Return best match score (0.0 - 1.0) as dict
    """
    # 12 scale steps dari 0.1 sampai 2.0
    scales = np.linspace(0.1, 2.0, 12)
    
    best_match = {"name": None, "scale": 0, "max_val": 0}
    
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
            max_val = np.max(match)
            
            # Track best match
            if max_val > best_match["max_val"]:
                best_match = {"name": template_name, "scale": scale, "max_val": max_val}
    
    return best_match

# Main loop - terus monitor dan respond ke strike
print("\n🎣 Monitoring untuk strike...")
print("Tekan CTRL+C untuk stop\n")

print("⚙️  Template: bite_the_baits.png ONLY")
print("⚙️  Strategy: Consecutive detection (min 3 frames @ 0.60+)")
print("⚙️  Cooldown: 2 detik\n")

strike_cooldown = 0
last_strike_time = 0
frame_count = 0
consecutive_hits = 0
consecutive_threshold = 0.60  # TURUNKAN drastis ke 0.60 (fokus bite template)
consecutive_required = 3  # Turunkan ke 3 frame (lebih responsif)

try:
    while True:
        img = get_bgr_ss(monitor)
        frame_count += 1
        
        # Deteksi strike - return best match score
        best_match = detect_strike(img, strike_templates, frame_count=frame_count)
        
        # Log setiap frame yang promising
        if best_match["max_val"] >= 0.55:
            status = "✓" if best_match["max_val"] >= consecutive_threshold else "✗"
            print(f"[{frame_count}] {status} {best_match['name']} = {best_match['max_val']:.4f} | Consecutive: {consecutive_hits}/{consecutive_required}")
        
        # Hitung consecutive detection
        if best_match["max_val"] >= consecutive_threshold:
            consecutive_hits += 1
            if consecutive_hits <= 3:  # Show first 3 consecutive matches
                print(f"  💓 [{consecutive_hits}/{consecutive_required}] {best_match['name']} ({best_match['max_val']:.4f})")
        else:
            # Reset jika tidak match
            if consecutive_hits > 0:
                print(f"  ⚠️ Reset! Score {best_match['max_val']:.4f} < {consecutive_threshold}")
            consecutive_hits = 0
        
        # TRIGGER STRIKE hanya jika consecutive hits cukup
        if consecutive_hits >= consecutive_required:
            current_time = time.time()
            # Cooldown 2 detik untuk avoid multiple triggers
            if current_time - last_strike_time > 2.0:
                print(f"\n{'='*60}")
                print(f"🎯🎯🎯 STRIKE CONFIRMED! NARIK! 🎯🎯🎯")
                print(f"Template: {best_match['name']}")
                print(f"Strength: {best_match['max_val']:.4f} | Consecutive Frames: {consecutive_hits}")
                print(f"{'='*60}\n")
                pyin.press("space")
                last_strike_time = current_time
                consecutive_hits = 0  # Reset counter
                time.sleep(0.5)
        
        time.sleep(0.1)  # Check setiap 100ms

except KeyboardInterrupt:
    print("\n\n❌ Script stopped by user")
    sct.close()
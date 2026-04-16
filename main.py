import os
import time
import mss
import cv2
import pygetwindow as gw
import pydirectinput as pyin
import numpy as np

# ==========================================
# KONFIGURASI
# ==========================================
PW_PATH = r"C:\Users\User\Desktop\Pixel Worlds.url"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "template")
WORLD_NAME = "fish1"  # Ganti dengan nama world yang diinginkan

# ==========================================
# SETUP WINDOW
# ==========================================
print("🎮 Membuka Pixel Worlds...")
os.startfile(PW_PATH)

# Tunggu window Pixel World terbuka
while not gw.getWindowsWithTitle("Pixel World"):
    print("⏳ Menunggu Pixel Worlds terbuka...")
    time.sleep(1)

windows = gw.getWindowsWithTitle("Pixel World")[0]

if windows.isMinimized:
    windows.restore()
windows.activate()

# Ambil koordinat window
monitor = {
    "left": windows.left,
    "top": windows.top,
    "width": windows.width,
    "height": windows.height
}

sct = mss.mss()

print(f"✅ Window ditemukan: {windows.title}")
print(f"📏 Ukuran window: {windows.width}x{windows.height}")

# ==========================================
# FUNGSI HELPER
# ==========================================
def get_bgr_ss(monitor):
    """Ambil screenshot dalam format BGR"""
    screenshot = sct.grab(monitor)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)

def type_in_game(text):
    """Ketik text di game dengan delay"""
    for char in text:
        pyin.press(char)
        time.sleep(0.1)

def get_match_template_coor(img, template, threshold=0.65):
    """
    Cari template di image dengan multi-scale matching
    Return (x, y, confidence) jika ditemukan, None jika tidak
    """
    if template is None or img is None:
        return None
    
    try:
        img_h, img_w = img.shape[:2]
        templ_h, templ_w = template.shape[:2]
        best_match = {"x": 0, "y": 0, "confidence": 0, "scale": 1.0}
        
        # Coba dengan berbagai skala (0.4x sampai 2.0x)
        scales = np.linspace(0.4, 2.0, 15)  # 15 tahap scaling
        
        for scale in scales:
            # Resize template sesuai skala
            new_w = int(templ_w * scale)
            new_h = int(templ_h * scale)
            
            # Skip jika template terlalu kecil
            if new_w < 5 or new_h < 5:
                continue
            
            # Skip jika template lebih besar dari image (error dari OpenCV)sh1
            if new_w > img_w or new_h > img_h:
                continue
            
            scaled_template = cv2.resize(template, (new_w, new_h))
            
            # Template matching
            match = cv2.matchTemplate(img, scaled_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(match)
            
            # Simpan match terbaik
            if max_val > best_match["confidence"]:
                best_match["confidence"] = max_val
                best_match["x"] = max_loc[0] + new_w // 2
                best_match["y"] = max_loc[1] + new_h // 2
                best_match["scale"] = scale
        
        # Return jika confidence cukup
        if best_match["confidence"] >= threshold:
            return (best_match["x"], best_match["y"], best_match["confidence"])
    
    except Exception as e:
        print(f"⚠️ Error template matching: {e}")
    
    return None

# ==========================================
# TUNGGU HOMEPAGE
# ==========================================
print("\n⏳ Tunggu halaman utama Pixel Worlds...")
world_name_field_template = cv2.imread(os.path.join(TEMPLATE_DIR, "world_name_input.png"))

while True:
    img = get_bgr_ss(monitor)
    result = get_match_template_coor(img, world_name_field_template, threshold=0.65)
    
    if result is not None:
        world_field_coor = (result[0], result[1])
        print("✅ Halaman utama ditemukan!")
        break
    
    print("⏳ Menunggu halaman utama...")
    time.sleep(1)

# ==========================================
# MASUK KE WORLD
# ==========================================
print(f"\n🌍 Memasukkan nama world: {WORLD_NAME}")

# Click field input
click_x = world_field_coor[0] + monitor["left"]
click_y = world_field_coor[1] + monitor["top"]

print(f"📍 Click pada input field...")
pyin.click(click_x, click_y)
time.sleep(0.5)

# Clear field
print("🗑️  Menghapus field...")
pyin.click(click_x, click_y)
pyin.click(click_x, click_y)
pyin.click(click_x, click_y)
time.sleep(0.2)

pyin.keyDown('ctrl')
pyin.press('a')
pyin.keyUp('ctrl')
time.sleep(0.1)

pyin.press('delete')
time.sleep(0.1)
pyin.press('backspace')
time.sleep(0.2)

# Type world name
print(f"⌨️  Mengetik: {WORLD_NAME}")
type_in_game(WORLD_NAME)
time.sleep(1)

# Press Enter untuk join
print("✅ Press ENTER untuk masuk...")
pyin.press('enter')
time.sleep(0.3)
pyin.press('enter')

time.sleep(3)

print(f"\n✨ Sudah masuk ke world '{WORLD_NAME}'")

# ==========================================
# LOAD TEMPLATES
# ==========================================
print("\n🎣 Loading templates...")

strike_template_path = os.path.join(TEMPLATE_DIR, "bite_the_baits.png")
strike_template = cv2.imread(strike_template_path)

fish_left_template = cv2.imread(os.path.join(TEMPLATE_DIR, "fish_left.png"))
fish_right_template = cv2.imread(os.path.join(TEMPLATE_DIR, "fish_right.png"))

net_left_template = cv2.imread(os.path.join(TEMPLATE_DIR, "net_left.png"))
net_right_template = cv2.imread(os.path.join(TEMPLATE_DIR, "net_right.png"))

if strike_template is None:
    print("❌ ERROR: bite_the_baits.png tidak ditemukan!")
    exit()

if fish_left_template is None or fish_right_template is None:
    print("⚠️ WARNING: Fish templates tidak lengkap!")

if net_left_template is None or net_right_template is None:
    print("⚠️ WARNING: Net templates tidak lengkap!")

print("✅ Semua template loaded!")

# ==========================================
# FUNGSI DETEKSI POSISI NET (AREA IKAN)
# ==========================================
def get_net_positions(img):
    """
    Deteksi posisi net_left dan net_right
    Return {'left': (x, y), 'right': (x, y)} atau None
    """
    positions = {}
    
    # Deteksi net_left
    if net_left_template is not None:
        result = get_match_template_coor(img, net_left_template, threshold=0.60)
        if result is not None:
            positions['left'] = (result[0], result[1])
    
    # Deteksi net_right
    if net_right_template is not None:
        result = get_match_template_coor(img, net_right_template, threshold=0.60)
        if result is not None:
            positions['right'] = (result[0], result[1])
    
    return positions if positions else None

# ==========================================
# FUNGSI DETEKSI IKAN
# ==========================================
def get_fish_position(img):
    """
    Deteksi posisi dan arah ikan
    Return ('left', x, y, confidence) atau ('right', x, y, confidence) atau None
    """
    # Deteksi ikan ke kiri
    if fish_left_template is not None:
        result = get_match_template_coor(img, fish_left_template, threshold=0.55)
        if result is not None:
            return ('left', result[0], result[1], result[2])
    
    # Deteksi ikan ke kanan
    if fish_right_template is not None:
        result = get_match_template_coor(img, fish_right_template, threshold=0.55)
        if result is not None:
            return ('right', result[0], result[1], result[2])
    
    return None

# ==========================================
# MONITORING & AUTO MOVE
# ==========================================
print("\n🎣 Menunggu STRIKE pertama kali...")
print("Tekan CTRL+C untuk stop\n")

strike_count = 0
move_count = 0
last_strike_time = 0
last_move_time = 0
strike_cooldown = 0.3
move_cooldown = 0.2

# State tracking
waiting_for_strike = True  # Tunggu strike sebelum mulai follow
a_pressed = False
d_pressed = False

try:
    while True:
        img = get_bgr_ss(monitor)
        current_time = time.time()
        
        # ===== PHASE 0: TUNGGU STRIKE (AWAL) =====
        if waiting_for_strike:
            # Coba deteksi STRIKE dengan threshold yang lebih rendah
            result = get_match_template_coor(img, strike_template, threshold=0.50)
            
            if result is not None:
                x, y, confidence = result
                
                # Press SPACE untuk strike pertama
                if current_time - last_strike_time > strike_cooldown:
                    strike_count += 1
                    print(f"\n[{strike_count}] 🎯 STRIKE DETECTED! (conf: {confidence:.3f}) → PRESS SPACE!")
                    pyin.press("space")
                    last_strike_time = current_time
                    waiting_for_strike = False  # Sekarang mulai follow ikan
                    print(f"✅ Memulai mengikuti ikan...\n")
                    time.sleep(0.5)
            else:
                # Terus tunggu strike
                print(".", end="", flush=True)
                time.sleep(0.1)
        
        # ===== PHASE 1: FOLLOW FISH (SETELAH STRIKE) =====
        else:
            # Deteksi net positions untuk hitung center
            net_pos = get_net_positions(img)
            center_x = None
            
            if net_pos is not None and 'left' in net_pos and 'right' in net_pos:
                net_left_x = net_pos['left'][0]
                net_right_x = net_pos['right'][0]
                center_x = (net_left_x + net_right_x) / 2
            
            # Deteksi ikan
            fish_info = get_fish_position(img)
            
            if fish_info is not None and center_x is not None:
                direction, fish_x, fish_y, confidence = fish_info
                tolerance = 30  # Pixel tolerance untuk dianggap centered
                
                # Bandingkan posisi ikan dengan center
                if fish_x < center_x - tolerance:
                    # Ikan di KIRI center → gerak ke KANAN (press 'd')
                    if current_time - last_move_time > move_cooldown:
                        if not d_pressed:
                            print(f"🐠 Ikan KIRI center ({fish_x:.0f} < {center_x:.0f}) → 'D' (gerak kanan)")
                            if a_pressed:
                                pyin.keyUp('a')
                                a_pressed = False
                            pyin.keyDown('d')
                            d_pressed = True
                        last_move_time = current_time
                        move_count += 1
                
                elif fish_x > center_x + tolerance:
                    # Ikan di KANAN center → gerak ke KIRI (press 'a')
                    if current_time - last_move_time > move_cooldown:
                        if not a_pressed:
                            print(f"🐠 Ikan KANAN center ({fish_x:.0f} > {center_x:.0f}) → 'A' (gerak kiri)")
                            if d_pressed:
                                pyin.keyUp('d')
                                d_pressed = False
                            pyin.keyDown('a')
                            a_pressed = True
                        last_move_time = current_time
                        move_count += 1
                
                else:
                    # Ikan CENTERED ✓
                    if a_pressed or d_pressed:
                        print(f"✅ Ikan CENTERED! ({fish_x:.0f} ≈ {center_x:.0f})")
                    if a_pressed:
                        pyin.keyUp('a')
                        a_pressed = False
                    if d_pressed:
                        pyin.keyUp('d')
                        d_pressed = False
            else:
                # Release tombol jika ikan/net tidak terdeteksi
                if a_pressed:
                    pyin.keyUp('a')
                    a_pressed = False
                if d_pressed:
                    pyin.keyUp('d')
                    d_pressed = False
            
            # ===== DETEKSI STRIKE BERIKUTNYA =====
            result = get_match_template_coor(img, strike_template, threshold=0.50)
            
            if result is not None:
                x, y, confidence = result
                
                if current_time - last_strike_time > strike_cooldown:
                    strike_count += 1
                    
                    # Release semua tombol saat strike
                    if a_pressed:
                        pyin.keyUp('a')
                        a_pressed = False
                    if d_pressed:
                        pyin.keyUp('d')
                        d_pressed = False
                    
                    print(f"\n[{strike_count}] 🎯 STRIKE! (conf: {confidence:.3f}) → PRESS SPACE!")
                    pyin.press("space")
                    last_strike_time = current_time
                    time.sleep(0.3)
            
            time.sleep(0.03)  # Check setiap 30ms

except KeyboardInterrupt:
    # Release semua tombol sebelum exit
    if a_pressed:
        pyin.keyUp('a')
    if d_pressed:
        pyin.keyUp('d')
    
    print(f"\n\n❌ Script stopped by user")
    print(f"Total strikes: {strike_count}")
    print(f"Total moves: {move_count}")
    sct.close()
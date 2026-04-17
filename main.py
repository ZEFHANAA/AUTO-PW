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
DEFAULT_PW_PATH = r"C:\Users\Zefhana Ananda\OneDrive\Desktop\Pixel Worlds.url"
PW_PATH = os.getenv("PW_PATH", DEFAULT_PW_PATH)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(SCRIPT_DIR, "template")
WORLD_NAME = os.getenv("WORLD_NAME", "fish1")
WINDOW_TITLES = ["Pixel World", "Pixel Worlds"]
STARTUP_TIMEOUT_SEC = 60
HOMEPAGE_TIMEOUT_SEC = 60
FAST_SCALES = np.array([0.88, 0.96, 1.0, 1.07, 1.15], dtype=np.float32)
FISH_FAST_SCALES = np.array([0.92, 1.0, 1.08], dtype=np.float32)
STRIKE_FALLBACK_SCALES = np.array([0.72, 0.8, 0.88, 0.96, 1.0, 1.08, 1.16, 1.24], dtype=np.float32)
DEBUG_LOG = os.getenv("DEBUG_LOG", "0").strip().lower() in ("1", "true", "yes", "on")
ACTIVE_FISH_CONF_MIN = 0.34
TRACK_GRACE_SEC = 0.12


def release_movement_keys(a_pressed, d_pressed):
    if a_pressed:
        pyin.keyUp("a")
    if d_pressed:
        pyin.keyUp("d")


def get_gray_ss(sct, monitor):
    """Ambil screenshot grayscale untuk mempercepat template matching."""
    screenshot = sct.grab(monitor)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2GRAY)


def type_in_game(text):
    """Ketik text di game dengan delay"""
    for char in text:
        pyin.press(char)
        time.sleep(0.1)


def press_space_strike():
    """Press SPACE lebih tegas agar game menangkap input strike."""
    pyin.keyDown("space")
    time.sleep(0.02)
    pyin.keyUp("space")


def press_direction_tap(key, hold_sec=0.012):
    """Tap arah singkat agar input tidak nyangkut."""
    pyin.keyDown(key)
    time.sleep(hold_sec)
    pyin.keyUp(key)


def get_match_template_coor(img, template, threshold=0.65, scales=None, roi=None):
    """
    Cari template di image dengan multi-scale matching
    Return (x, y, confidence) jika ditemukan, None jika tidak
    """
    if template is None or img is None:
        return None

    try:
        img_h, img_w = img.shape[:2]

        offset_x = 0
        offset_y = 0
        search_img = img
        if roi is not None:
            x1, y1, x2, y2 = roi
            x1 = max(0, min(int(x1), img_w - 1))
            y1 = max(0, min(int(y1), img_h - 1))
            x2 = max(x1 + 1, min(int(x2), img_w))
            y2 = max(y1 + 1, min(int(y2), img_h))
            search_img = img[y1:y2, x1:x2]
            offset_x = x1
            offset_y = y1

        img_h, img_w = search_img.shape[:2]
        templ_h, templ_w = template.shape[:2]
        best_match = {"x": 0, "y": 0, "confidence": 0, "scale": 1.0}

        if scales is None:
            scales = np.linspace(0.4, 2.0, 15)

        for scale in scales:
            new_w = int(templ_w * scale)
            new_h = int(templ_h * scale)

            if new_w < 5 or new_h < 5:
                continue

            if new_w > img_w or new_h > img_h:
                continue

            scaled_template = cv2.resize(template, (new_w, new_h))
            match = cv2.matchTemplate(search_img, scaled_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(match)

            if max_val > best_match["confidence"]:
                best_match["confidence"] = max_val
                best_match["x"] = offset_x + max_loc[0] + new_w // 2
                best_match["y"] = offset_y + max_loc[1] + new_h // 2
                best_match["scale"] = scale

        if best_match["confidence"] >= threshold:
            return (best_match["x"], best_match["y"], best_match["confidence"])

    except Exception as e:
        print(f"⚠️ Error template matching: {e}")

    return None


def find_game_window(timeout_sec=STARTUP_TIMEOUT_SEC):
    start_time = time.time()
    while True:
        for title in WINDOW_TITLES:
            matches = gw.getWindowsWithTitle(title)
            if matches:
                return matches[0]

        if time.time() - start_time >= timeout_sec:
            return None

        print("⏳ Menunggu Pixel Worlds terbuka...")
        time.sleep(1)


def setup_window():
    if not os.path.exists(PW_PATH):
        raise FileNotFoundError(
            f"Path game tidak ditemukan: {PW_PATH}. Atur env PW_PATH atau perbaiki path default."
        )

    print("🎮 Membuka Pixel Worlds...")
    os.startfile(PW_PATH)

    window = find_game_window()
    if window is None:
        raise TimeoutError(
            f"Window game tidak ditemukan dalam {STARTUP_TIMEOUT_SEC} detik. Pastikan game berhasil terbuka."
        )

    if window.isMinimized:
        window.restore()

    try:
        window.activate()
    except Exception:
        time.sleep(1)
        window.activate()

    monitor = {
        "left": window.left,
        "top": window.top,
        "width": window.width,
        "height": window.height,
    }

    print(f"✅ Window ditemukan: {window.title}")
    print(f"📏 Ukuran window: {window.width}x{window.height}")
    return monitor


def wait_homepage(sct, monitor):
    print("\n⏳ Tunggu halaman utama Pixel Worlds...")
    template_path = os.path.join(TEMPLATE_DIR, "world_name_input.png")
    world_name_field_template = cv2.imread(template_path, cv2.IMREAD_GRAYSCALE)

    if world_name_field_template is None:
        raise FileNotFoundError(f"Template tidak ditemukan atau rusak: {template_path}")

    start_time = time.time()
    while True:
        img = get_gray_ss(sct, monitor)
        result = get_match_template_coor(img, world_name_field_template, threshold=0.65)

        if result is not None:
            print("✅ Halaman utama ditemukan!")
            return (result[0], result[1])

        if time.time() - start_time >= HOMEPAGE_TIMEOUT_SEC:
            raise TimeoutError(
                f"Homepage tidak terdeteksi dalam {HOMEPAGE_TIMEOUT_SEC} detik."
            )

        print("⏳ Menunggu halaman utama...")
        time.sleep(1)


def join_world(monitor, world_field_coor):
    print(f"\n🌍 Memasukkan nama world: {WORLD_NAME}")
    click_x = world_field_coor[0] + monitor["left"]
    click_y = world_field_coor[1] + monitor["top"]

    print("📍 Click pada input field...")
    pyin.click(click_x, click_y)
    time.sleep(0.5)

    print("🗑️  Menghapus field...")
    pyin.click(click_x, click_y)
    pyin.click(click_x, click_y)
    pyin.click(click_x, click_y)
    time.sleep(0.2)

    pyin.keyDown("ctrl")
    pyin.press("a")
    pyin.keyUp("ctrl")
    time.sleep(0.1)

    pyin.press("delete")
    time.sleep(0.1)
    pyin.press("backspace")
    time.sleep(0.2)

    print(f"⌨️  Mengetik: {WORLD_NAME}")
    type_in_game(WORLD_NAME)
    time.sleep(1)

    print("✅ Press ENTER untuk masuk...")
    pyin.press("enter")
    time.sleep(0.3)
    pyin.press("enter")
    time.sleep(3)

    print(f"\n✨ Sudah masuk ke world '{WORLD_NAME}'")


def load_templates():
    print("\n🎣 Loading templates...")

    strike_template_path = os.path.join(TEMPLATE_DIR, "bite_the_baits.png")
    strike_template = cv2.imread(strike_template_path, cv2.IMREAD_GRAYSCALE)

    fish_left_template = cv2.imread(os.path.join(TEMPLATE_DIR, "fish_left.png"), cv2.IMREAD_GRAYSCALE)
    fish_right_template = cv2.imread(os.path.join(TEMPLATE_DIR, "fish_right.png"), cv2.IMREAD_GRAYSCALE)
    net_left_template = cv2.imread(os.path.join(TEMPLATE_DIR, "net_left.png"), cv2.IMREAD_GRAYSCALE)
    net_right_template = cv2.imread(os.path.join(TEMPLATE_DIR, "net_right.png"), cv2.IMREAD_GRAYSCALE)

    if strike_template is None:
        raise FileNotFoundError("bite_the_baits.png tidak ditemukan!")

    if fish_left_template is None or fish_right_template is None:
        print("⚠️ WARNING: Fish templates tidak lengkap!")

    if net_left_template is None or net_right_template is None:
        print("⚠️ WARNING: Net templates tidak lengkap!")

    print("✅ Semua template loaded!")
    return strike_template, fish_left_template, fish_right_template, net_left_template, net_right_template


def get_net_positions(img, net_left_template, net_right_template, net_roi=None):
    positions = {}

    if net_left_template is not None:
        result = get_match_template_coor(img, net_left_template, threshold=0.56, scales=FAST_SCALES, roi=net_roi)
        if result is not None:
            positions["left"] = (result[0], result[1])

    if net_right_template is not None:
        result = get_match_template_coor(img, net_right_template, threshold=0.56, scales=FAST_SCALES, roi=net_roi)
        if result is not None:
            positions["right"] = (result[0], result[1])

    return positions if positions else None


def get_fish_position(img, fish_left_template, fish_right_template, fish_roi=None):
    best = None

    if fish_left_template is not None:
        result = get_match_template_coor(img, fish_left_template, threshold=0.38, scales=FISH_FAST_SCALES, roi=fish_roi)
        if result is not None:
            best = ("left", result[0], result[1], result[2])

    if fish_right_template is not None:
        result = get_match_template_coor(img, fish_right_template, threshold=0.38, scales=FISH_FAST_SCALES, roi=fish_roi)
        if result is not None:
            candidate = ("right", result[0], result[1], result[2])
            if best is None or candidate[3] > best[3]:
                best = candidate

    return best


def run_fishing_loop(sct, monitor, strike_template, fish_left_template, fish_right_template, net_left_template, net_right_template):
    print("\n🎣 Menunggu STRIKE pertama kali...")
    print("Tekan CTRL+C untuk stop\n")

    strike_count = 0
    move_count = 0
    last_strike_time = 0
    last_move_time = 0
    strike_cooldown = 0.3
    move_cooldown = 0.003

    waiting_for_strike = True
    a_pressed = False
    d_pressed = False
    last_center_x = None
    last_center_y = None
    last_fish_seen_time = time.time()
    fish_x_smooth = None
    hold_direction = None
    hold_direction_since = 0.0
    strike_miss_count = 0
    last_wait_log_time = 0.0

    try:
        while True:
            img = get_gray_ss(sct, monitor)
            current_time = time.time()
            img_h, img_w = img.shape[:2]
            top_band_roi = (0, 0, img_w, int(img_h * 0.52))

            if waiting_for_strike:
                result = get_match_template_coor(
                    img,
                    strike_template,
                    threshold=0.47,
                    scales=FAST_SCALES,
                    roi=top_band_roi,
                )

                # Fallback scan layar penuh secara periodik untuk antisipasi posisi/scale UI berubah.
                if result is None and (strike_miss_count % 5 == 0):
                    result = get_match_template_coor(
                        img,
                        strike_template,
                        threshold=0.43,
                        scales=STRIKE_FALLBACK_SCALES,
                        roi=None,
                    )

                if result is not None:
                    _, _, confidence = result

                    if current_time - last_strike_time > strike_cooldown:
                        strike_count += 1
                        print(f"\n[{strike_count}] 🎯 STRIKE DETECTED! (conf: {confidence:.3f}) -> PRESS SPACE!")
                        press_space_strike()
                        last_strike_time = current_time
                        waiting_for_strike = False
                        strike_miss_count = 0
                        print("✅ Memulai mengikuti ikan...\n")
                        time.sleep(0.08)
                else:
                    strike_miss_count += 1
                    if DEBUG_LOG and (current_time - last_wait_log_time) >= 1.2:
                        print(f"⏳ Menunggu STRIKE... (miss={strike_miss_count})")
                        last_wait_log_time = current_time
                    time.sleep(0.02)
                continue

            net_pos = get_net_positions(img, net_left_template, net_right_template, top_band_roi)
            center_x = None
            center_y = None
            if net_pos is not None and "left" in net_pos and "right" in net_pos:
                center_x = (net_pos["left"][0] + net_pos["right"][0]) / 2
                center_y = (net_pos["left"][1] + net_pos["right"][1]) / 2
                last_center_x = center_x
                last_center_y = center_y
            elif last_center_x is not None:
                # Pakai center terakhir agar steering tetap jalan walau template net sempat miss.
                center_x = last_center_x
                center_y = last_center_y if last_center_y is not None else img_h * 0.25
            else:
                # Fallback awal saat net belum terdeteksi sama sekali.
                center_x = img.shape[1] / 2
                center_y = img_h * 0.25

            fish_roi = (
                max(0, int(center_x - 320)),
                max(0, int(center_y - 120)),
                min(img_w, int(center_x + 320)),
                min(int(img_h * 0.62), int(center_y + 95)),
            )

            fish_info = get_fish_position(img, fish_left_template, fish_right_template, fish_roi)
            if fish_info is not None and center_x is not None and fish_info[3] >= ACTIVE_FISH_CONF_MIN:
                _, fish_x_raw, _, fish_conf = fish_info
                last_fish_seen_time = current_time

                # Utamakan posisi terbaru agar tidak telat saat ikan ganti arah.
                if fish_x_smooth is None:
                    fish_x_smooth = fish_x_raw
                else:
                    fish_x_smooth = (0.02 * fish_x_smooth) + (0.98 * fish_x_raw)

                fish_x = fish_x_smooth
                tolerance = 2

                if fish_x < center_x - tolerance:
                    if current_time - last_move_time > move_cooldown:
                        hold_direction = "a"
                        hold_direction_since = current_time
                        if d_pressed:
                            pyin.keyUp("d")
                            d_pressed = False
                        print(f"🐠 Ikan KIRI center ({fish_x:.0f} < {center_x:.0f}, conf={fish_conf:.2f}) -> TAP 'A'")
                        press_direction_tap("a")
                        last_move_time = current_time
                        move_count += 1

                elif fish_x > center_x + tolerance:
                    if current_time - last_move_time > move_cooldown:
                        hold_direction = "d"
                        hold_direction_since = current_time
                        if a_pressed:
                            pyin.keyUp("a")
                            a_pressed = False
                        print(f"🐠 Ikan KANAN center ({fish_x:.0f} > {center_x:.0f}, conf={fish_conf:.2f}) -> TAP 'D'")
                        press_direction_tap("d")
                        last_move_time = current_time
                        move_count += 1

                else:
                    hold_direction = None
                    if DEBUG_LOG:
                        print(f"✅ Ikan CENTERED! ({fish_x:.0f} ~= {center_x:.0f})")
                    if a_pressed:
                        pyin.keyUp("a")
                        a_pressed = False
                    if d_pressed:
                        pyin.keyUp("d")
                        d_pressed = False
            else:
                # Miss pendek: tahan arah sebentar agar tracking tidak putus-putus.
                if (current_time - last_fish_seen_time) > TRACK_GRACE_SEC:
                    if a_pressed:
                        pyin.keyUp("a")
                        a_pressed = False
                    if d_pressed:
                        pyin.keyUp("d")
                        d_pressed = False
                    fish_x_smooth = None
                    hold_direction = None

                # Jika ikan lama tidak terlihat, anggap minigame selesai dan kembali tunggu strike.
                if current_time - last_fish_seen_time > 1.8:
                    waiting_for_strike = True
                    last_center_x = None
                    print("⏳ Minigame selesai/ikan hilang. Kembali menunggu STRIKE...")
                    time.sleep(0.15)
                    continue

            time.sleep(0.003)

    except KeyboardInterrupt:
        print("\n\n❌ Script stopped by user")
        print(f"Total strikes: {strike_count}")
        print(f"Total moves: {move_count}")
    finally:
        release_movement_keys(a_pressed, d_pressed)


def main():
    sct = None
    try:
        monitor = setup_window()
        sct = mss.mss()
        world_field_coor = wait_homepage(sct, monitor)
        join_world(monitor, world_field_coor)
        templates = load_templates()
        run_fishing_loop(sct, monitor, *templates)
    except Exception as e:
        print(f"❌ ERROR: {e}")
    finally:
        if sct is not None:
            sct.close()

if __name__ == "__main__":
    main()
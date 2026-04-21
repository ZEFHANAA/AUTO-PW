import os
import time

import cv2
import mss
import numpy as np
import pydirectinput as pyin
import pygetwindow as gw

# Hilangkan jeda global bawaan tiap input agar steering lebih responsif.
pyin.PAUSE = 0

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

# Matching yang lebih sempit membuat posisi fish/net lebih stabil.
FAST_SCALES = np.array([0.88, 0.96, 1.0, 1.08, 1.16], dtype=np.float32)
TRACK_FAST_SCALES = np.array([0.96, 1.0, 1.04], dtype=np.float32)
FISH_FAST_SCALES = np.array([0.96, 1.0, 1.04], dtype=np.float32)
STRIKE_FALLBACK_SCALES = np.array(
    [0.72, 0.8, 0.88, 0.96, 1.0, 1.08, 1.16, 1.24],
    dtype=np.float32,
)
ACTIVE_FISH_CONF_MIN = 0.38
FISH_TEMPLATE_THRESHOLD = 0.38
WIDE_FISH_CONF_MIN = 0.44
NET_TEMPLATE_THRESHOLD = 0.54
CATCH_BUTTON_THRESHOLD = 0.56
TRACK_GRACE_SEC = 0.05
MOVE_LOG_INTERVAL_SEC = 0.20

# Mapping arah dibuat manual supaya stabil.
# Jika arah terasa kebalik, ganti lewat STEER_MODE=normal/inverted.
STEER_MODE_RAW = os.getenv(
    "STEER_MODE",
    os.getenv("STEER_INVERT", "inverted"),
).strip().lower()
FISH_SMOOTHING_ALPHA = 1.0
STEER_BASE_TOLERANCE = 1
TRACK_FISH_HALF_WIDTH = 180
TRACK_FISH_HALF_HEIGHT = 85
WIDE_FISH_HALF_WIDTH = 320
WIDE_FISH_HALF_HEIGHT = 130
TRACK_VELOCITY_BIAS_SEC = 0.02
TRACK_VELOCITY_BIAS_LIMIT = 75
FISH_PREDICT_LEAD_SEC = 0.035
FISH_PREDICT_MAX_PX = 40


def resolve_steer_mode(value):
    if value in ("0", "false", "no", "off", "normal"):
        return "normal"
    if value in ("1", "true", "yes", "on", "invert", "inverted"):
        return "inverted"
    return "inverted"


def get_direction_key(target_side, steer_mode):
    if steer_mode == "inverted":
        return "d" if target_side == "left" else "a"
    return "a" if target_side == "left" else "d"


def get_tap_hold_sec(distance):
    if distance >= 90:
        return 0.042
    if distance >= 70:
        return 0.034
    if distance >= 50:
        return 0.028
    if distance >= 45:
        return 0.024
    if distance >= 28:
        return 0.020
    if distance >= 14:
        return 0.015
    if distance >= 7:
        return 0.011
    return 0.008


def release_movement_keys(a_pressed=False, d_pressed=False):
    if a_pressed:
        pyin.keyUp("a")
    if d_pressed:
        pyin.keyUp("d")


def apply_direction_hold(direction_key, a_pressed=False, d_pressed=False):
    want_a = direction_key == "a"
    want_d = direction_key == "d"

    if want_a and not a_pressed:
        pyin.keyDown("a")
    elif not want_a and a_pressed:
        pyin.keyUp("a")

    if want_d and not d_pressed:
        pyin.keyDown("d")
    elif not want_d and d_pressed:
        pyin.keyUp("d")

    return want_a, want_d


def get_bgr_ss(sct, monitor):
    """Ambil screenshot dalam format BGR."""
    screenshot = sct.grab(monitor)
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_BGRA2BGR)


def type_in_game(text):
    """Ketik text di game dengan delay."""
    for char in text:
        pyin.press(char)
        time.sleep(0.1)


def press_space_strike():
    """Press SPACE tegas agar strike lebih konsisten terbaca."""
    pyin.keyDown("space")
    time.sleep(0.02)
    pyin.keyUp("space")


def press_direction_tap(key, hold_sec=0.012):
    """Tap arah pendek agar tidak nyangkut di satu arah."""
    pyin.keyDown(key)
    time.sleep(hold_sec)
    pyin.keyUp(key)


def get_match_template_coor(img, template, threshold=0.65, scales=None, roi=None):
    """
    Cari template di image dengan multi-scale matching.
    Return (x, y, confidence) jika ditemukan, None jika tidak.
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

        search_h, search_w = search_img.shape[:2]
        templ_h, templ_w = template.shape[:2]
        best_match = {"x": 0, "y": 0, "confidence": 0.0, "scale": 1.0}

        if scales is None:
            scales = np.linspace(0.4, 2.0, 15)

        for scale in scales:
            new_w = int(templ_w * scale)
            new_h = int(templ_h * scale)

            if new_w < 5 or new_h < 5:
                continue

            if new_w > search_w or new_h > search_h:
                continue

            scaled_template = cv2.resize(template, (new_w, new_h))
            match = cv2.matchTemplate(search_img, scaled_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(match)

            if max_val > best_match["confidence"]:
                best_match["confidence"] = float(max_val)
                best_match["x"] = offset_x + max_loc[0] + new_w // 2
                best_match["y"] = offset_y + max_loc[1] + new_h // 2
                best_match["scale"] = float(scale)

        if best_match["confidence"] >= threshold:
            return (best_match["x"], best_match["y"], best_match["confidence"])

    except Exception as exc:
        print(f"[WARN] Error template matching: {exc}")

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

        print("[INFO] Menunggu Pixel Worlds terbuka...")
        time.sleep(1)


def setup_window():
    if not os.path.exists(PW_PATH):
        raise FileNotFoundError(
            f"Path game tidak ditemukan: {PW_PATH}. "
            "Atur env PW_PATH atau perbaiki path default."
        )

    print("[INFO] Membuka Pixel Worlds...")
    os.startfile(PW_PATH)

    window = find_game_window()
    if window is None:
        raise TimeoutError(
            "Window game tidak ditemukan dalam "
            f"{STARTUP_TIMEOUT_SEC} detik. Pastikan game berhasil terbuka."
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

    print(f"[OK] Window ditemukan: {window.title}")
    print(f"[OK] Ukuran window: {window.width}x{window.height}")
    return monitor


def wait_homepage(sct, monitor):
    print("\n[INFO] Tunggu halaman utama Pixel Worlds...")
    template_path = os.path.join(TEMPLATE_DIR, "world_name_input.png")
    world_name_field_template = cv2.imread(template_path)

    if world_name_field_template is None:
        raise FileNotFoundError(f"Template tidak ditemukan atau rusak: {template_path}")

    start_time = time.time()
    while True:
        img = get_bgr_ss(sct, monitor)
        result = get_match_template_coor(img, world_name_field_template, threshold=0.65)

        if result is not None:
            print("[OK] Halaman utama ditemukan.")
            return (result[0], result[1])

        if time.time() - start_time >= HOMEPAGE_TIMEOUT_SEC:
            raise TimeoutError(
                f"Homepage tidak terdeteksi dalam {HOMEPAGE_TIMEOUT_SEC} detik."
            )

        print("[INFO] Menunggu halaman utama...")
        time.sleep(1)


def join_world(monitor, world_field_coor):
    print(f"\n[INFO] Memasukkan nama world: {WORLD_NAME}")
    click_x = world_field_coor[0] + monitor["left"]
    click_y = world_field_coor[1] + monitor["top"]

    print("[INFO] Click pada input field...")
    pyin.click(click_x, click_y)
    time.sleep(0.5)

    print("[INFO] Menghapus field...")
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

    print(f"[INFO] Mengetik: {WORLD_NAME}")
    type_in_game(WORLD_NAME)
    time.sleep(1)

    print("[OK] Press ENTER untuk masuk...")
    pyin.press("enter")
    time.sleep(0.3)
    pyin.press("enter")
    time.sleep(3)

    print(f"\n[OK] Sudah masuk ke world '{WORLD_NAME}'")


def load_templates():
    print("\n[INFO] Loading templates...")

    strike_template = cv2.imread(os.path.join(TEMPLATE_DIR, "bite_the_baits.png"))
    catch_button_template = cv2.imread(os.path.join(TEMPLATE_DIR, "catch_button.png"))
    fish_left_template = cv2.imread(os.path.join(TEMPLATE_DIR, "fish_left.png"))
    fish_right_template = cv2.imread(os.path.join(TEMPLATE_DIR, "fish_right.png"))
    net_left_template = cv2.imread(os.path.join(TEMPLATE_DIR, "net_left.png"))
    net_right_template = cv2.imread(os.path.join(TEMPLATE_DIR, "net_right.png"))

    if strike_template is None:
        raise FileNotFoundError("bite_the_baits.png tidak ditemukan.")

    if catch_button_template is None:
        raise FileNotFoundError("catch_button.png tidak ditemukan.")

    if fish_left_template is None or fish_right_template is None:
        print("[WARN] Fish templates tidak lengkap.")

    if net_left_template is None or net_right_template is None:
        print("[WARN] Net templates tidak lengkap.")

    print("[OK] Semua template loaded.")
    return (
        strike_template,
        catch_button_template,
        fish_left_template,
        fish_right_template,
        net_left_template,
        net_right_template,
    )


def get_net_positions(img, net_left_template, net_right_template, net_roi=None):
    positions = {}

    if net_left_template is not None:
        result = get_match_template_coor(
            img,
            net_left_template,
            threshold=NET_TEMPLATE_THRESHOLD,
            scales=TRACK_FAST_SCALES,
            roi=net_roi,
        )
        if result is not None:
            positions["left"] = (result[0], result[1])

    if net_right_template is not None:
        result = get_match_template_coor(
            img,
            net_right_template,
            threshold=NET_TEMPLATE_THRESHOLD,
            scales=TRACK_FAST_SCALES,
            roi=net_roi,
        )
        if result is not None:
            positions["right"] = (result[0], result[1])

    return positions if positions else None


def get_fish_position(img, fish_left_template, fish_right_template, fish_roi=None):
    best = None

    if fish_left_template is not None:
        result = get_match_template_coor(
            img,
            fish_left_template,
            threshold=FISH_TEMPLATE_THRESHOLD,
            scales=FISH_FAST_SCALES,
            roi=fish_roi,
        )
        if result is not None:
            best = ("left", result[0], result[1], result[2])

    if fish_right_template is not None:
        result = get_match_template_coor(
            img,
            fish_right_template,
            threshold=FISH_TEMPLATE_THRESHOLD,
            scales=FISH_FAST_SCALES,
            roi=fish_roi,
        )
        if result is not None:
            candidate = ("right", result[0], result[1], result[2])
            if best is None or candidate[3] > best[3]:
                best = candidate

    return best


def run_fishing_loop(
    sct,
    monitor,
    strike_template,
    catch_button_template,
    fish_left_template,
    fish_right_template,
    net_left_template,
    net_right_template,
):
    print("\n[INFO] Menunggu STRIKE pertama kali...")
    print("Tekan CTRL+C untuk stop\n")

    strike_count = 0
    move_count = 0
    last_strike_time = 0.0
    last_move_time = 0.0
    last_catch_press_time = 0.0
    strike_cooldown = 0.3

    waiting_for_strike = True
    last_center_x = None
    last_center_y = None
    last_fish_seen_time = time.time()
    fish_x_smooth = None
    last_fish_side = None
    last_fish_track_time = None
    fish_velocity_px_sec = 0.0
    fish_detect_streak = 0
    a_pressed = False
    d_pressed = False
    last_hold_key = None
    last_track_state = None
    steer_mode = resolve_steer_mode(STEER_MODE_RAW)

    print(
        "[INFO] Steering mode manual: "
        f"{steer_mode.upper()} (STEER_MODE={STEER_MODE_RAW})"
    )

    try:
        while True:
            img = get_bgr_ss(sct, monitor)
            current_time = time.time()
            img_h, img_w = img.shape[:2]
            top_band_roi = (0, 0, img_w, max(1, int(img_h * 0.52)))

            if waiting_for_strike:
                result = get_match_template_coor(
                    img,
                    strike_template,
                    threshold=0.50,
                    scales=FAST_SCALES,
                    roi=top_band_roi,
                )

                if result is None:
                    result = get_match_template_coor(
                        img,
                        strike_template,
                        threshold=0.45,
                        scales=STRIKE_FALLBACK_SCALES,
                    )

                if result is not None:
                    _, _, confidence = result

                    if current_time - last_strike_time > strike_cooldown:
                        strike_count += 1
                        print(
                            f"\n[{strike_count}] STRIKE DETECTED "
                            f"(conf={confidence:.3f}) -> PRESS SPACE"
                        )
                        press_space_strike()
                        last_strike_time = current_time
                        waiting_for_strike = False
                        fish_x_smooth = None
                        last_fish_side = None
                        last_fish_track_time = None
                        fish_velocity_px_sec = 0.0
                        fish_detect_streak = 0
                        release_movement_keys(a_pressed, d_pressed)
                        a_pressed = False
                        d_pressed = False
                        last_hold_key = None
                        last_track_state = None
                        print("[OK] Memulai mengikuti ikan...\n")
                        time.sleep(0.02)
                else:
                    print(".", end="", flush=True)
                    time.sleep(0.02)
                continue

            net_pos = get_net_positions(
                img,
                net_left_template,
                net_right_template,
                net_roi=top_band_roi,
            )

            catch_result = get_match_template_coor(
                img,
                catch_button_template,
                threshold=CATCH_BUTTON_THRESHOLD,
                scales=TRACK_FAST_SCALES,
                roi=top_band_roi,
            )

            if catch_result is None:
                catch_result = get_match_template_coor(
                    img,
                    catch_button_template,
                    threshold=0.50,
                    scales=STRIKE_FALLBACK_SCALES,
                )

            if catch_result is not None and (current_time - last_catch_press_time) > 0.35:
                _, _, catch_conf = catch_result
                print(
                    "[OK] Catch button terdeteksi "
                    f"(conf={catch_conf:.3f}) -> PRESS SPACE"
                )
                press_space_strike()
                last_catch_press_time = current_time
                waiting_for_strike = True
                fish_x_smooth = None
                last_fish_side = None
                last_fish_track_time = None
                fish_velocity_px_sec = 0.0
                fish_detect_streak = 0
                last_center_x = None
                last_center_y = None
                release_movement_keys(a_pressed, d_pressed)
                a_pressed = False
                d_pressed = False
                last_hold_key = None
                last_track_state = None
                time.sleep(0.15)
                continue

            if net_pos is not None and "left" in net_pos and "right" in net_pos:
                center_x = (net_pos["left"][0] + net_pos["right"][0]) / 2
                center_y = (net_pos["left"][1] + net_pos["right"][1]) / 2
                last_center_x = center_x
                last_center_y = center_y
            elif last_center_x is not None:
                center_x = last_center_x
                center_y = last_center_y if last_center_y is not None else img_h * 0.25
            else:
                center_x = img_w / 2
                center_y = img_h * 0.25

            fish_search_x = fish_x_smooth if fish_x_smooth is not None else center_x
            fish_search_x += float(
                np.clip(
                    fish_velocity_px_sec * TRACK_VELOCITY_BIAS_SEC,
                    -TRACK_VELOCITY_BIAS_LIMIT,
                    TRACK_VELOCITY_BIAS_LIMIT,
                )
            )
            fish_roi = (
                max(0, int(fish_search_x - TRACK_FISH_HALF_WIDTH)),
                max(0, int(center_y - TRACK_FISH_HALF_HEIGHT)),
                min(img_w, int(fish_search_x + TRACK_FISH_HALF_WIDTH)),
                min(int(img_h * 0.70), int(center_y + TRACK_FISH_HALF_HEIGHT)),
            )

            fish_roi_wide = (
                max(0, int(center_x - WIDE_FISH_HALF_WIDTH)),
                max(0, int(center_y - WIDE_FISH_HALF_HEIGHT)),
                min(img_w, int(center_x + WIDE_FISH_HALF_WIDTH)),
                min(int(img_h * 0.72), int(center_y + WIDE_FISH_HALF_HEIGHT)),
            )

            fish_info = get_fish_position(
                img,
                fish_left_template,
                fish_right_template,
                fish_roi=fish_roi,
            )
            fish_detect_source = "narrow" if fish_info is not None else None

            if fish_info is None:
                fish_info = get_fish_position(
                    img,
                    fish_left_template,
                    fish_right_template,
                    fish_roi=fish_roi_wide,
                )
                if fish_info is not None:
                    fish_detect_source = "wide"

            use_last_known_fish = False
            if fish_info is None and fish_x_smooth is not None:
                use_last_known_fish = (current_time - last_fish_seen_time) <= TRACK_GRACE_SEC

            fish_detected_this_frame = False
            if fish_info is not None:
                fish_side, fish_x_raw, _, fish_conf = fish_info
                required_conf = (
                    ACTIVE_FISH_CONF_MIN
                    if fish_detect_source == "narrow"
                    else WIDE_FISH_CONF_MIN
                )

                if fish_conf >= required_conf:
                    fish_detected_this_frame = True
                    prev_fish_x = fish_x_smooth
                    prev_track_time = last_fish_track_time
                    last_fish_seen_time = current_time
                    last_fish_side = fish_side

                    if fish_x_smooth is None:
                        fish_x_smooth = fish_x_raw
                    else:
                        fish_x_smooth = (
                            (1.0 - FISH_SMOOTHING_ALPHA) * fish_x_smooth
                        ) + (FISH_SMOOTHING_ALPHA * fish_x_raw)

                    fish_x = fish_x_smooth
                    if prev_fish_x is not None and prev_track_time is not None:
                        dt = max(0.001, current_time - prev_track_time)
                        instant_velocity = (fish_x - prev_fish_x) / dt
                        fish_velocity_px_sec = (fish_velocity_px_sec * 0.35) + (
                            instant_velocity * 0.65
                        )
                    else:
                        fish_velocity_px_sec = 0.0
                    last_fish_track_time = current_time
                    fish_detect_streak += 1
                else:
                    fish_detect_streak = 0

            if fish_detected_this_frame and fish_detect_streak >= 2:
                pass
            elif fish_detected_this_frame:
                fish_x = None
                fish_side = None
            elif use_last_known_fish and fish_detect_streak >= 2:
                fish_x = fish_x_smooth
                fish_side = last_fish_side
                fish_conf = 0.0
            else:
                fish_x = None
                fish_side = None
                if not use_last_known_fish:
                    fish_detect_streak = 0

            if fish_x is not None:
                target_x = center_x
                predict_lead_px = float(
                    np.clip(
                        fish_velocity_px_sec * FISH_PREDICT_LEAD_SEC,
                        -FISH_PREDICT_MAX_PX,
                        FISH_PREDICT_MAX_PX,
                    )
                )
                control_x = fish_x + predict_lead_px
                delta = control_x - target_x
                delta_abs = abs(delta)
                tolerance = max(STEER_BASE_TOLERANCE, int(img_w * 0.001))

                if delta < -tolerance:
                    steer_side = "right"
                    direction_key = get_direction_key(steer_side, steer_mode)

                    a_pressed, d_pressed = apply_direction_hold(
                        direction_key,
                        a_pressed,
                        d_pressed,
                    )
                    if (
                        last_hold_key != direction_key
                        or (current_time - last_move_time) >= MOVE_LOG_INTERVAL_SEC
                    ):
                        print(
                            "[MOVE] Fish di kiri green center "
                            f"({fish_x:.0f} < {target_x:.0f}, "
                            f"conf={fish_conf:.2f}, delta={delta_abs:.0f}, "
                            f"lead={predict_lead_px:.0f}) "
                            f"-> HOLD '{direction_key.upper()}' [{steer_mode.upper()}]"
                        )
                        last_move_time = current_time
                    last_hold_key = direction_key
                    last_track_state = "move_right"
                    move_count += 1

                elif delta > tolerance:
                    steer_side = "left"
                    direction_key = get_direction_key(steer_side, steer_mode)

                    a_pressed, d_pressed = apply_direction_hold(
                        direction_key,
                        a_pressed,
                        d_pressed,
                    )
                    if (
                        last_hold_key != direction_key
                        or (current_time - last_move_time) >= MOVE_LOG_INTERVAL_SEC
                    ):
                        print(
                            "[MOVE] Fish di kanan green center "
                            f"({fish_x:.0f} > {target_x:.0f}, "
                            f"conf={fish_conf:.2f}, delta={delta_abs:.0f}, "
                            f"lead={predict_lead_px:.0f}) "
                            f"-> HOLD '{direction_key.upper()}' [{steer_mode.upper()}]"
                        )
                        last_move_time = current_time
                    last_hold_key = direction_key
                    last_track_state = "move_left"
                    move_count += 1
                else:
                    release_movement_keys(a_pressed, d_pressed)
                    a_pressed = False
                    d_pressed = False
                    last_hold_key = None
                    if last_track_state != "center":
                        print(
                            "[OK] Fish masuk ke tengah green "
                            f"({fish_x:.0f} ~= {target_x:.0f})"
                        )
                    last_track_state = "center"
            else:
                release_movement_keys(a_pressed, d_pressed)
                a_pressed = False
                d_pressed = False
                last_hold_key = None
                last_track_state = None

                if not use_last_known_fish:
                    fish_x_smooth = None
                    last_fish_side = None
                    last_fish_track_time = None
                    fish_velocity_px_sec = 0.0
                    fish_detect_streak = 0

                if current_time - last_fish_seen_time > 1.8:
                    waiting_for_strike = True
                    last_center_x = None
                    last_center_y = None
                    print(
                        "[INFO] Minigame selesai atau fish hilang. "
                        "Kembali menunggu STRIKE..."
                    )
                    time.sleep(0.15)
                    continue

            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\n\n[STOP] Script stopped by user")
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
    except Exception as exc:
        print(f"[ERROR] {exc}")
    finally:
        if sct is not None:
            sct.close()


if __name__ == "__main__":
    main()

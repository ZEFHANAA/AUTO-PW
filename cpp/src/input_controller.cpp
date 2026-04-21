#include "auto_pw/input_controller.hpp"

#include <chrono>
#include <thread>

namespace auto_pw {

namespace {

INPUT makeKeyboardInput(WORD virtualKey, DWORD flags) {
    INPUT input{};
    input.type = INPUT_KEYBOARD;
    input.ki.wVk = virtualKey;
    input.ki.dwFlags = flags;
    return input;
}

WORD virtualKeyFromChar(char ch) {
    SHORT mapped = VkKeyScanA(ch);
    if (mapped == -1) {
        return 0;
    }

    return static_cast<WORD>(mapped & 0xFF);
}

bool needsShift(char ch) {
    SHORT mapped = VkKeyScanA(ch);
    return mapped != -1 && (mapped & 0x0100) != 0;
}

} // namespace

void InputController::keyDown(WORD virtualKey) const {
    INPUT input = makeKeyboardInput(virtualKey, 0);
    SendInput(1, &input, sizeof(INPUT));
}

void InputController::keyUp(WORD virtualKey) const {
    INPUT input = makeKeyboardInput(virtualKey, KEYEVENTF_KEYUP);
    SendInput(1, &input, sizeof(INPUT));
}

void InputController::pressKey(WORD virtualKey, int holdMs) const {
    keyDown(virtualKey);
    std::this_thread::sleep_for(std::chrono::milliseconds(holdMs));
    keyUp(virtualKey);
}

void InputController::click(int screenX, int screenY) const {
    SetCursorPos(screenX, screenY);

    INPUT down{};
    down.type = INPUT_MOUSE;
    down.mi.dwFlags = MOUSEEVENTF_LEFTDOWN;

    INPUT up{};
    up.type = INPUT_MOUSE;
    up.mi.dwFlags = MOUSEEVENTF_LEFTUP;

    INPUT inputs[2] = {down, up};
    SendInput(2, inputs, sizeof(INPUT));
}

void InputController::typeText(const std::string& text) const {
    for (char ch : text) {
        WORD virtualKey = virtualKeyFromChar(ch);
        if (virtualKey == 0) {
            continue;
        }

        if (needsShift(ch)) {
            keyDown(VK_SHIFT);
        }

        keyDown(virtualKey);
        keyUp(virtualKey);

        if (needsShift(ch)) {
            keyUp(VK_SHIFT);
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(25));
    }
}

} // namespace auto_pw

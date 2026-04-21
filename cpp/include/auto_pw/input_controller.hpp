#pragma once

#include <string>

#include <Windows.h>

namespace auto_pw {

class InputController {
public:
    void pressKey(WORD virtualKey, int holdMs = 20) const;
    void keyDown(WORD virtualKey) const;
    void keyUp(WORD virtualKey) const;
    void click(int screenX, int screenY) const;
    void typeText(const std::string& text) const;
};

} // namespace auto_pw

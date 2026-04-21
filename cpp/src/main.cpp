#include <iostream>

#include "auto_pw/bot.hpp"

int main() {
    try {
        auto_pw::Config config = auto_pw::Config::load();
        auto_pw::Bot bot(std::move(config));
        return bot.run();
    } catch (const std::exception& error) {
        std::cerr << "[ERROR] " << error.what() << '\n';
        return 1;
    }
}

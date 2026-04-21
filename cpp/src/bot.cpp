#include "auto_pw/bot.hpp"

#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <optional>
#include <stdexcept>
#include <thread>

#include <Windows.h>

#include "auto_pw/template_matcher.hpp"
#include "auto_pw/window_capture.hpp"

namespace auto_pw {

namespace {

std::string getEnv(const char* name, const std::string& defaultValue) {
    const char* value = std::getenv(name);
    if (value == nullptr || *value == '\0') {
        return defaultValue;
    }

    return value;
}

std::filesystem::path resolveTemplateDir() {
    const std::filesystem::path current = std::filesystem::current_path();
    const std::filesystem::path direct = current / "template";
    if (std::filesystem::exists(direct)) {
        return direct;
    }

    const std::filesystem::path parent = current.parent_path() / "template";
    if (std::filesystem::exists(parent)) {
        return parent;
    }

    return direct;
}

cv::Rect topBand(const cv::Mat& frame, double ratio) {
    const int height = std::max(1, static_cast<int>(frame.rows * ratio));
    return {0, 0, frame.cols, height};
}

double nowSec() {
    using clock = std::chrono::steady_clock;
    const auto now = clock::now().time_since_epoch();
    return std::chrono::duration<double>(now).count();
}

WORD directionKey(bool inverted, bool targetLeft) {
    if (inverted) {
        return targetLeft ? 'd' : 'a';
    }

    return targetLeft ? 'a' : 'd';
}

} // namespace

Config Config::load() {
    Config config;
    config.gamePath = std::filesystem::path(getEnv("PW_PATH", R"(C:\Users\Zefhana Ananda\OneDrive\Desktop\Pixel Worlds.url)"));
    config.templateDir = std::filesystem::path(getEnv("TEMPLATE_DIR", resolveTemplateDir().string()));
    config.worldName = getEnv("WORLD_NAME", "fish1");
    config.steerModeRaw = getEnv("STEER_MODE", getEnv("STEER_INVERT", "inverted"));
    config.windowTitles = {L"Pixel World", L"Pixel Worlds"};

    config.fastScales = {0.88, 0.96, 1.0, 1.08, 1.16};
    config.trackFastScales = {0.96, 1.0, 1.04};
    config.fishFastScales = {0.96, 1.0, 1.04};
    config.strikeFallbackScales = {0.72, 0.8, 0.88, 0.96, 1.0, 1.08, 1.16, 1.24};

    return config;
}

Bot::Bot(Config config)
    : config_(std::move(config)) {}

void Bot::loadTemplates() {
    const auto& dir = config_.templateDir;

    templates_.strike = cv::imread((dir / "bite_the_baits.png").string());
    templates_.catchButton = cv::imread((dir / "catch_button.png").string());
    templates_.fishLeft = cv::imread((dir / "fish_left.png").string());
    templates_.fishRight = cv::imread((dir / "fish_right.png").string());
    templates_.netLeft = cv::imread((dir / "net_left.png").string());
    templates_.netRight = cv::imread((dir / "net_right.png").string());
    templates_.worldNameInput = cv::imread((dir / "world_name_input.png").string());

    if (templates_.strike.empty()) {
        throw std::runtime_error("bite_the_baits.png tidak ditemukan atau rusak");
    }

    if (templates_.catchButton.empty()) {
        throw std::runtime_error("catch_button.png tidak ditemukan atau rusak");
    }

    if (templates_.worldNameInput.empty()) {
        throw std::runtime_error("world_name_input.png tidak ditemukan atau rusak");
    }

    if (templates_.fishLeft.empty() || templates_.fishRight.empty()) {
        std::cout << "[WARN] Fish templates tidak lengkap\n";
    }

    if (templates_.netLeft.empty() || templates_.netRight.empty()) {
        std::cout << "[WARN] Net templates tidak lengkap\n";
    }
}

bool Bot::waitForHomepage(HWND hwnd) {
    const auto start = std::chrono::steady_clock::now();

    while (true) {
        const cv::Mat frame = captureWindow(hwnd);
        if (!frame.empty()) {
            auto result = matchTemplateMultiScale(
                frame,
                templates_.worldNameInput,
                0.65,
                config_.fastScales,
                topBand(frame, 0.75));

            if (result.has_value()) {
                std::cout << "[OK] Halaman utama ditemukan\n";
                return true;
            }
        }

        const auto elapsed = std::chrono::steady_clock::now() - start;
        if (std::chrono::duration_cast<std::chrono::seconds>(elapsed).count() >= config_.homepageTimeoutSec) {
            return false;
        }

        std::cout << "[INFO] Menunggu halaman utama...\n";
        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}

void Bot::joinWorld(HWND hwnd) {
    const cv::Mat frame = captureWindow(hwnd);
    if (frame.empty()) {
        throw std::runtime_error("Gagal capture window saat join world");
    }

    auto result = matchTemplateMultiScale(frame, templates_.worldNameInput, 0.65, config_.fastScales, topBand(frame, 0.75));
    if (!result.has_value()) {
        throw std::runtime_error("Field world name tidak ditemukan");
    }

    RECT rect{};
    if (!GetWindowRect(hwnd, &rect)) {
        throw std::runtime_error("Gagal membaca window rect");
    }

    const int clickX = rect.left + result->x;
    const int clickY = rect.top + result->y;

    std::cout << "[INFO] Memasukkan nama world: " << config_.worldName << '\n';
    input_.click(clickX, clickY);
    std::this_thread::sleep_for(std::chrono::milliseconds(500));

    input_.click(clickX, clickY);
    input_.click(clickX, clickY);
    input_.click(clickX, clickY);
    std::this_thread::sleep_for(std::chrono::milliseconds(200));

    input_.keyDown(VK_CONTROL);
    input_.pressKey('A');
    input_.keyUp(VK_CONTROL);
    std::this_thread::sleep_for(std::chrono::milliseconds(100));

    input_.pressKey(VK_DELETE, 20);
    input_.pressKey(VK_BACK, 20);

    input_.typeText(config_.worldName);
    std::this_thread::sleep_for(std::chrono::seconds(1));

    input_.pressKey(VK_RETURN, 20);
    std::this_thread::sleep_for(std::chrono::milliseconds(300));
    input_.pressKey(VK_RETURN, 20);
    std::this_thread::sleep_for(std::chrono::seconds(3));

    std::cout << "[OK] Sudah masuk ke world '" << config_.worldName << "'\n";
}

std::optional<std::pair<int, int>> Bot::getNetCenter(const cv::Mat& frame, const cv::Rect& roi) {
    std::optional<MatchResult> left;
    std::optional<MatchResult> right;

    if (!templates_.netLeft.empty()) {
        left = matchTemplateMultiScale(frame, templates_.netLeft, config_.netTemplateThreshold, config_.trackFastScales, roi);
    }

    if (!templates_.netRight.empty()) {
        right = matchTemplateMultiScale(frame, templates_.netRight, config_.netTemplateThreshold, config_.trackFastScales, roi);
    }

    if (left.has_value() && right.has_value()) {
        return std::make_pair((left->x + right->x) / 2, (left->y + right->y) / 2);
    }

    return std::nullopt;
}

std::optional<Bot::FishDetection> Bot::getFishPosition(const cv::Mat& frame, const cv::Rect& roi) {
    std::optional<FishDetection> best;

    if (!templates_.fishLeft.empty()) {
        auto result = matchTemplateMultiScale(frame, templates_.fishLeft, config_.fishTemplateThreshold, config_.fishFastScales, roi);
        if (result.has_value()) {
            best = FishDetection{"left", result->x, result->y, result->confidence};
        }
    }

    if (!templates_.fishRight.empty()) {
        auto result = matchTemplateMultiScale(frame, templates_.fishRight, config_.fishTemplateThreshold, config_.fishFastScales, roi);
        if (result.has_value()) {
            FishDetection candidate{"right", result->x, result->y, result->confidence};
            if (!best.has_value() || candidate.confidence > best->confidence) {
                best = candidate;
            }
        }
    }

    return best;
}

void Bot::runFishingLoop(HWND hwnd) {
    enum class TrackState {
        None,
        MoveLeft,
        MoveRight,
        Center,
    };

    std::cout << "[INFO] Menunggu STRIKE pertama kali...\n";
    std::cout << "Tekan CTRL+C untuk stop\n\n";

    const bool inverted = config_.steerModeRaw == "inverted" || config_.steerModeRaw == "invert" || config_.steerModeRaw == "1" || config_.steerModeRaw == "true";
    std::cout << "[INFO] Steering mode manual: " << (inverted ? "INVERTED" : "NORMAL") << " (STEER_MODE=" << config_.steerModeRaw << ")\n";

    int strikeCount = 0;
    int moveCount = 0;
    double lastStrikeTime = 0.0;
    double lastCatchPressTime = 0.0;
    double lastMoveTime = 0.0;
    double lastFishSeenTime = nowSec();

    Phase phase = Phase::WaitingForStrike;
    TrackState trackState = TrackState::None;

    std::optional<double> fishXSmooth;
    std::optional<std::string> lastFishSide;
    std::optional<double> lastFishTrackTime;
    double fishVelocityPxSec = 0.0;
    int fishDetectStreak = 0;
    bool aPressed = false;
    bool dPressed = false;
    std::optional<WORD> lastHoldKey;

    while (true) {
        const cv::Mat frame = captureWindow(hwnd);
        if (frame.empty()) {
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            continue;
        }

        const double currentTime = nowSec();
        const cv::Rect topBandRect = topBand(frame, 0.52);

        if (phase == Phase::WaitingForStrike) {
            auto strike = matchTemplateMultiScale(frame, templates_.strike, 0.50, config_.fastScales, topBandRect);
            if (!strike.has_value()) {
                strike = matchTemplateMultiScale(frame, templates_.strike, 0.45, config_.strikeFallbackScales, std::nullopt);
            }

            if (strike.has_value() && currentTime - lastStrikeTime > config_.strikeCooldownSec) {
                ++strikeCount;
                std::cout << "\n[" << strikeCount << "] STRIKE DETECTED (conf=" << strike->confidence << ") -> PRESS SPACE\n";
                input_.pressKey(VK_SPACE, 20);
                lastStrikeTime = currentTime;
                phase = Phase::Tracking;
                fishXSmooth.reset();
                lastFishSide.reset();
                lastFishTrackTime.reset();
                fishVelocityPxSec = 0.0;
                fishDetectStreak = 0;
                aPressed = false;
                dPressed = false;
                lastHoldKey.reset();
                trackState = TrackState::None;
                std::cout << "[OK] Memulai mengikuti ikan...\n\n";
                std::this_thread::sleep_for(std::chrono::milliseconds(20));
                continue;
            }

            std::cout << "." << std::flush;
            std::this_thread::sleep_for(std::chrono::milliseconds(20));
            continue;
        }

        auto catchResult = matchTemplateMultiScale(frame, templates_.catchButton, config_.catchButtonThreshold, config_.trackFastScales, topBandRect);
        if (!catchResult.has_value()) {
            catchResult = matchTemplateMultiScale(frame, templates_.catchButton, 0.50, config_.strikeFallbackScales, std::nullopt);
        }

        if (catchResult.has_value() && currentTime - lastCatchPressTime > config_.catchCooldownSec) {
            std::cout << "[OK] Catch button terdeteksi (conf=" << catchResult->confidence << ") -> PRESS SPACE\n";
            input_.pressKey(VK_SPACE, 20);
            lastCatchPressTime = currentTime;
            phase = Phase::WaitingForStrike;
            fishXSmooth.reset();
            lastFishSide.reset();
            lastFishTrackTime.reset();
            fishVelocityPxSec = 0.0;
            fishDetectStreak = 0;
            aPressed = false;
            dPressed = false;
            lastHoldKey.reset();
            trackState = TrackState::None;
            std::this_thread::sleep_for(std::chrono::milliseconds(150));
            continue;
        }

        const int imgW = frame.cols;
        const int imgH = frame.rows;
        const int centerX = imgW / 2;
        const int centerY = imgH / 4;

        cv::Rect fishRoi;
        if (fishXSmooth.has_value()) {
            const double fishSearchX = *fishXSmooth + std::clamp(fishVelocityPxSec * config_.trackVelocityBiasSec, -static_cast<double>(config_.trackVelocityBiasLimit), static_cast<double>(config_.trackVelocityBiasLimit));
            const int left = std::max(0, static_cast<int>(fishSearchX - config_.trackFishHalfWidth));
            const int top = std::max(0, static_cast<int>(centerY - config_.trackFishHalfHeight));
            const int right = std::min(imgW, static_cast<int>(fishSearchX + config_.trackFishHalfWidth));
            const int bottom = std::min(static_cast<int>(imgH * 0.70), static_cast<int>(centerY + config_.trackFishHalfHeight));
            fishRoi = {left, top, std::max(1, right - left), std::max(1, bottom - top)};
        } else {
            const int left = std::max(0, centerX - config_.trackFishHalfWidth);
            const int top = std::max(0, centerY - config_.trackFishHalfHeight);
            const int right = std::min(imgW, centerX + config_.trackFishHalfWidth);
            const int bottom = std::min(static_cast<int>(imgH * 0.70), centerY + config_.trackFishHalfHeight);
            fishRoi = {left, top, std::max(1, right - left), std::max(1, bottom - top)};
        }

        std::optional<FishDetection> fishInfo = getFishPosition(frame, fishRoi);
        bool fishDetectedThisFrame = false;

        if (fishInfo.has_value() && fishInfo->confidence >= config_.activeFishConfMin) {
            fishDetectedThisFrame = true;
            const double previousFishX = fishXSmooth.has_value() ? *fishXSmooth : fishInfo->x;
            const double previousTrackTime = lastFishTrackTime.has_value() ? *lastFishTrackTime : currentTime;

            lastFishSeenTime = currentTime;
            lastFishSide = fishInfo->side;
            if (!fishXSmooth.has_value()) {
                fishXSmooth = fishInfo->x;
            } else {
                fishXSmooth = *fishXSmooth + (fishInfo->x - *fishXSmooth);
            }

            const double dt = std::max(0.001, currentTime - previousTrackTime);
            const double instantVelocity = ((*fishXSmooth) - previousFishX) / dt;
            fishVelocityPxSec = (fishVelocityPxSec * 0.35) + (instantVelocity * 0.65);
            lastFishTrackTime = currentTime;
            ++fishDetectStreak;
        } else if (fishInfo.has_value()) {
            fishDetectStreak = 0;
        }

        bool useLastKnownFish = false;
        if (!fishDetectedThisFrame && fishXSmooth.has_value()) {
            useLastKnownFish = (currentTime - lastFishSeenTime) <= config_.trackGraceSec;
        }

        std::optional<int> fishX;
        if (fishDetectedThisFrame && fishDetectStreak >= 2) {
            fishX = static_cast<int>(*fishXSmooth);
        } else if (useLastKnownFish && fishDetectStreak >= 2) {
            fishX = static_cast<int>(*fishXSmooth);
        } else if (!useLastKnownFish) {
            fishXSmooth.reset();
            lastFishSide.reset();
            lastFishTrackTime.reset();
            fishVelocityPxSec = 0.0;
            fishDetectStreak = 0;
        }

        if (fishX.has_value()) {
            const double predictLeadPx = std::clamp(fishVelocityPxSec * config_.fishPredictLeadSec, -static_cast<double>(config_.fishPredictMaxPx), static_cast<double>(config_.fishPredictMaxPx));
            const double controlX = *fishX + predictLeadPx;
            const double delta = controlX - centerX;
            const double deltaAbs = std::abs(delta);
            const int tolerance = std::max(config_.steerBaseTolerance, static_cast<int>(imgW * 0.001));

            if (delta < -tolerance) {
                const WORD direction = directionKey(inverted, false);
                if (!aPressed || !lastHoldKey.has_value() || *lastHoldKey != direction) {
                    if (lastHoldKey.has_value() && *lastHoldKey != direction) {
                        input_.keyUp(*lastHoldKey);
                    }
                    input_.keyDown(direction);
                    aPressed = direction == 'a';
                    dPressed = direction == 'd';
                }

                if (!lastHoldKey.has_value() || *lastHoldKey != direction || currentTime - lastMoveTime >= config_.moveLogIntervalSec) {
                    std::cout << "[MOVE] Fish di kiri green center (" << *fishX << " < " << centerX << ", delta=" << deltaAbs << ", lead=" << predictLeadPx << ") -> HOLD '" << static_cast<char>(direction) << "' [" << (inverted ? "INVERTED" : "NORMAL") << "]\n";
                    lastMoveTime = currentTime;
                }

                lastHoldKey = direction;
                trackState = TrackState::MoveRight;
                ++moveCount;
            } else if (delta > tolerance) {
                const WORD direction = directionKey(inverted, true);
                if (!dPressed || !lastHoldKey.has_value() || *lastHoldKey != direction) {
                    if (lastHoldKey.has_value() && *lastHoldKey != direction) {
                        input_.keyUp(*lastHoldKey);
                    }
                    input_.keyDown(direction);
                    aPressed = direction == 'a';
                    dPressed = direction == 'd';
                }

                if (!lastHoldKey.has_value() || *lastHoldKey != direction || currentTime - lastMoveTime >= config_.moveLogIntervalSec) {
                    std::cout << "[MOVE] Fish di kanan green center (" << *fishX << " > " << centerX << ", delta=" << deltaAbs << ", lead=" << predictLeadPx << ") -> HOLD '" << static_cast<char>(direction) << "' [" << (inverted ? "INVERTED" : "NORMAL") << "]\n";
                    lastMoveTime = currentTime;
                }

                lastHoldKey = direction;
                trackState = TrackState::MoveLeft;
                ++moveCount;
            } else {
                if (aPressed) {
                    input_.keyUp('a');
                }
                if (dPressed) {
                    input_.keyUp('d');
                }
                aPressed = false;
                dPressed = false;
                lastHoldKey.reset();
                if (trackState != TrackState::Center) {
                    std::cout << "[OK] Fish masuk ke tengah green (" << *fishX << " ~= " << centerX << ")\n";
                }
                trackState = TrackState::Center;
            }
        } else {
            if (aPressed) {
                input_.keyUp('a');
            }
            if (dPressed) {
                input_.keyUp('d');
            }
            aPressed = false;
            dPressed = false;
            lastHoldKey.reset();
            trackState = TrackState::None;

            if (currentTime - lastFishSeenTime > 1.8) {
                phase = Phase::WaitingForStrike;
                std::cout << "[INFO] Minigame selesai atau fish hilang. Kembali menunggu STRIKE...\n";
                std::this_thread::sleep_for(std::chrono::milliseconds(150));
                continue;
            }
        }

        std::this_thread::sleep_for(std::chrono::milliseconds(1));
    }
}

int Bot::run() {
    if (!std::filesystem::exists(config_.gamePath)) {
        throw std::runtime_error("Path game tidak ditemukan: " + config_.gamePath.string());
    }

    loadTemplates();

    std::cout << "[INFO] Membuka Pixel Worlds...\n";
    HINSTANCE result = ShellExecuteW(nullptr, L"open", config_.gamePath.wstring().c_str(), nullptr, nullptr, SW_SHOWNORMAL);
    if (reinterpret_cast<intptr_t>(result) <= 32) {
        throw std::runtime_error("Gagal membuka Pixel Worlds");
    }

    HWND hwnd = findWindowByTitles(config_.windowTitles, config_.startupTimeoutSec);
    if (hwnd == nullptr) {
        throw std::runtime_error("Window game tidak ditemukan dalam timeout");
    }

    activateWindow(hwnd);

    RECT rect{};
    if (!GetWindowRect(hwnd, &rect)) {
        throw std::runtime_error("Gagal membaca ukuran window");
    }

    std::cout << "[OK] Window ditemukan\n";
    std::cout << "[OK] Ukuran window: " << (rect.right - rect.left) << "x" << (rect.bottom - rect.top) << '\n';

    if (!waitForHomepage(hwnd)) {
        throw std::runtime_error("Homepage tidak terdeteksi dalam timeout");
    }

    joinWorld(hwnd);
    runFishingLoop(hwnd);
    return 0;
}

} // namespace auto_pw

#pragma once

#include <optional>
#include <string>

#include <opencv2/opencv.hpp>

#include "config.hpp"
#include "input_controller.hpp"

namespace auto_pw {

class Bot {
public:
    explicit Bot(Config config);
    int run();

private:
    enum class Phase {
        WaitingForStrike,
        Tracking,
    };

    struct Templates {
        cv::Mat strike;
        cv::Mat catchButton;
        cv::Mat fishLeft;
        cv::Mat fishRight;
        cv::Mat netLeft;
        cv::Mat netRight;
        cv::Mat worldNameInput;
    };

    struct FishDetection {
        std::string side;
        int x = 0;
        int y = 0;
        double confidence = 0.0;
    };

    Config config_;
    Templates templates_;
    InputController input_;

    void loadTemplates();
    bool waitForHomepage(HWND hwnd);
    void joinWorld(HWND hwnd);
    void runFishingLoop(HWND hwnd);

    std::optional<std::pair<int, int>> getNetCenter(const cv::Mat& frame, const cv::Rect& roi);
    std::optional<FishDetection> getFishPosition(const cv::Mat& frame, const cv::Rect& roi);
};

} // namespace auto_pw

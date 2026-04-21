#pragma once

#include <optional>
#include <vector>

#include <opencv2/opencv.hpp>

namespace auto_pw {

struct MatchResult {
    int x = 0;
    int y = 0;
    double confidence = 0.0;
    double scale = 1.0;
};

std::optional<MatchResult> matchTemplateMultiScale(
    const cv::Mat& image,
    const cv::Mat& templ,
    double threshold,
    const std::vector<double>& scales,
    const std::optional<cv::Rect>& roi = std::nullopt);

} // namespace auto_pw

#include "auto_pw/template_matcher.hpp"

#include <algorithm>

namespace auto_pw {

std::optional<MatchResult> matchTemplateMultiScale(
    const cv::Mat& image,
    const cv::Mat& templ,
    double threshold,
    const std::vector<double>& scales,
    const std::optional<cv::Rect>& roi) {
    if (image.empty() || templ.empty()) {
        return std::nullopt;
    }

    cv::Mat searchImage = image;
    cv::Rect offsetRect{0, 0, image.cols, image.rows};

    if (roi.has_value()) {
        cv::Rect clipped = *roi & cv::Rect{0, 0, image.cols, image.rows};
        if (clipped.width <= 0 || clipped.height <= 0) {
            return std::nullopt;
        }

        searchImage = image(clipped);
        offsetRect = clipped;
    }

    MatchResult bestMatch{};

    for (double scale : scales) {
        int newWidth = std::max(5, static_cast<int>(templ.cols * scale));
        int newHeight = std::max(5, static_cast<int>(templ.rows * scale));

        if (newWidth > searchImage.cols || newHeight > searchImage.rows) {
            continue;
        }

        cv::Mat scaledTemplate;
        cv::resize(templ, scaledTemplate, cv::Size(newWidth, newHeight));

        cv::Mat matchResult;
        cv::matchTemplate(searchImage, scaledTemplate, matchResult, cv::TM_CCOEFF_NORMED);

        double minValue = 0.0;
        double maxValue = 0.0;
        cv::Point minLocation;
        cv::Point maxLocation;
        cv::minMaxLoc(matchResult, &minValue, &maxValue, &minLocation, &maxLocation);

        if (maxValue > bestMatch.confidence) {
            bestMatch.confidence = maxValue;
            bestMatch.x = offsetRect.x + maxLocation.x + newWidth / 2;
            bestMatch.y = offsetRect.y + maxLocation.y + newHeight / 2;
            bestMatch.scale = scale;
        }
    }

    if (bestMatch.confidence >= threshold) {
        return bestMatch;
    }

    return std::nullopt;
}

} // namespace auto_pw

#pragma once

#include <filesystem>
#include <string>
#include <vector>

namespace auto_pw {

struct Config {
    std::filesystem::path gamePath;
    std::filesystem::path templateDir;
    std::string worldName;
    std::string steerModeRaw;
    std::vector<std::wstring> windowTitles;

    int startupTimeoutSec = 60;
    int homepageTimeoutSec = 60;

    double strikeCooldownSec = 0.30;
    double catchCooldownSec = 0.35;
    double trackGraceSec = 0.05;
    double moveLogIntervalSec = 0.20;

    double activeFishConfMin = 0.38;
    double fishTemplateThreshold = 0.38;
    double wideFishConfMin = 0.44;
    double netTemplateThreshold = 0.54;
    double catchButtonThreshold = 0.56;

    int steerBaseTolerance = 1;
    int trackFishHalfWidth = 180;
    int trackFishHalfHeight = 85;
    int wideFishHalfWidth = 320;
    int wideFishHalfHeight = 130;

    double trackVelocityBiasSec = 0.02;
    int trackVelocityBiasLimit = 75;
    double fishPredictLeadSec = 0.035;
    int fishPredictMaxPx = 40;

    std::vector<double> fastScales;
    std::vector<double> trackFastScales;
    std::vector<double> fishFastScales;
    std::vector<double> strikeFallbackScales;

    static Config load();
};

} // namespace auto_pw

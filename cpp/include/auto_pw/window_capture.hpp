#pragma once

#include <string>
#include <vector>

#include <Windows.h>
#include <opencv2/opencv.hpp>

namespace auto_pw {

HWND findWindowByTitles(const std::vector<std::wstring>& titles, int timeoutSec);
void activateWindow(HWND hwnd);
cv::Mat captureWindow(HWND hwnd);

} // namespace auto_pw

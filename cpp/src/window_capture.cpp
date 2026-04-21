#include "auto_pw/window_capture.hpp"

#include <chrono>
#include <thread>

namespace auto_pw {

HWND findWindowByTitles(const std::vector<std::wstring>& titles, int timeoutSec) {
    const auto start = std::chrono::steady_clock::now();

    while (true) {
        for (const auto& title : titles) {
            HWND hwnd = FindWindowW(nullptr, title.c_str());
            if (hwnd != nullptr) {
                return hwnd;
            }
        }

        const auto elapsed = std::chrono::steady_clock::now() - start;
        if (std::chrono::duration_cast<std::chrono::seconds>(elapsed).count() >= timeoutSec) {
            return nullptr;
        }

        std::this_thread::sleep_for(std::chrono::seconds(1));
    }
}

void activateWindow(HWND hwnd) {
    if (hwnd == nullptr) {
        return;
    }

    ShowWindow(hwnd, SW_RESTORE);
    SetForegroundWindow(hwnd);
    BringWindowToTop(hwnd);
}

cv::Mat captureWindow(HWND hwnd) {
    if (hwnd == nullptr) {
        return {};
    }

    RECT rect{};
    if (!GetWindowRect(hwnd, &rect)) {
        return {};
    }

    const int width = rect.right - rect.left;
    const int height = rect.bottom - rect.top;
    if (width <= 0 || height <= 0) {
        return {};
    }

    HDC windowDC = GetWindowDC(hwnd);
    if (windowDC == nullptr) {
        return {};
    }

    HDC memoryDC = CreateCompatibleDC(windowDC);
    if (memoryDC == nullptr) {
        ReleaseDC(hwnd, windowDC);
        return {};
    }

    HBITMAP bitmap = CreateCompatibleBitmap(windowDC, width, height);
    if (bitmap == nullptr) {
        DeleteDC(memoryDC);
        ReleaseDC(hwnd, windowDC);
        return {};
    }

    HGDIOBJ oldBitmap = SelectObject(memoryDC, bitmap);
    BitBlt(memoryDC, 0, 0, width, height, windowDC, 0, 0, SRCCOPY | CAPTUREBLT);

    BITMAPINFO bitmapInfo{};
    bitmapInfo.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bitmapInfo.bmiHeader.biWidth = width;
    bitmapInfo.bmiHeader.biHeight = -height;
    bitmapInfo.bmiHeader.biPlanes = 1;
    bitmapInfo.bmiHeader.biBitCount = 32;
    bitmapInfo.bmiHeader.biCompression = BI_RGB;

    cv::Mat image(height, width, CV_8UC4);
    GetDIBits(memoryDC, bitmap, 0, height, image.data, &bitmapInfo, DIB_RGB_COLORS);

    SelectObject(memoryDC, oldBitmap);
    DeleteObject(bitmap);
    DeleteDC(memoryDC);
    ReleaseDC(hwnd, windowDC);

    cv::Mat bgrImage;
    cv::cvtColor(image, bgrImage, cv::COLOR_BGRA2BGR);
    return bgrImage;
}

} // namespace auto_pw

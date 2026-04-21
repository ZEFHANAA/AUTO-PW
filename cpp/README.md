# Auto PW C++

Ini versi C++ untuk Auto PW yang memisahkan capture, input, template matching, dan state bot.

## Struktur

- `src/main.cpp` entry point
- `src/bot.cpp` state machine bot
- `src/window_capture.cpp` capture window Pixel Worlds
- `src/template_matcher.cpp` multi-scale template matching
- `src/input_controller.cpp` keyboard dan mouse input

## Build

Butuh CMake, compiler C++17, dan OpenCV.

```powershell
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release
```

## Konfigurasi

Env yang dipakai:

- `PW_PATH`
- `WORLD_NAME`
- `TEMPLATE_DIR`
- `STEER_MODE`

## Catatan

Project ini adalah fondasi native C++. Logika deteksi sudah dipindah ke struktur yang rapi, tetapi kamu tetap perlu menyesuaikan threshold dan ROI sesuai resolusi window game.

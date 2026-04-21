cmake_minimum_required(VERSION 3.20)

project(auto_pw_cpp LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenCV REQUIRED)

add_executable(auto_pw
    src/bot.cpp
    src/input_controller.cpp
    src/main.cpp
    src/template_matcher.cpp
    src/window_capture.cpp
)

target_include_directories(auto_pw PRIVATE include)
target_link_libraries(auto_pw PRIVATE ${OpenCV_LIBS} Shell32 User32 Gdi32)

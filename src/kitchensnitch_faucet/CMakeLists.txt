cmake_minimum_required(VERSION 3.8)
project(kitchensnitch_faucet)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()
set(CMAKE_CXX_STANDARD 17)

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(cv_bridge REQUIRED)
find_package(OpenCV REQUIRED)
find_package(kitchensnitch_interfaces REQUIRED)

add_executable(faucet_watcher src/faucet_watcher.cpp)
ament_target_dependencies(faucet_watcher
  rclcpp sensor_msgs cv_bridge OpenCV kitchensnitch_interfaces)

install(TARGETS faucet_watcher DESTINATION lib/${PROJECT_NAME})

ament_package()

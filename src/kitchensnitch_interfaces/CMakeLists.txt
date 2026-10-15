cmake_minimum_required(VERSION 3.8)
project(kitchensnitch_interfaces)

find_package(ament_cmake REQUIRED)
find_package(builtin_interfaces REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/PitcherEvent.msg"
  "msg/FaucetEvent.msg"
  "msg/SinkState.msg"
  "msg/Alert.msg"
  DEPENDENCIES builtin_interfaces
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()

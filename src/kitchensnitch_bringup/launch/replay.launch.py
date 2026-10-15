"""Test setup: replay a recorded bag through the detectors instead of using the camera.

  ros2 launch kitchensnitch_bringup replay.launch.py bag:=bags/session_01
  ros2 launch kitchensnitch_bringup replay.launch.py bag:=bags/session_01 telegram:=true
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess
from launch.conditions import IfCondition
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('kitchensnitch_bringup'), 'config')
    params = [os.path.join(config, 'zones.yaml'), os.path.join(config, 'params.yaml')]

    return LaunchDescription([
        DeclareLaunchArgument('bag', description='Path to the rosbag2 directory to replay'),
        DeclareLaunchArgument('telegram', default_value='false',
                              description='Send real Telegram messages while replaying'),
        ExecuteProcess(cmd=['ros2', 'bag', 'play', LaunchConfiguration('bag')], output='screen'),
        Node(package='kitchensnitch_vision', executable='pitcher_tracker', parameters=params),
        Node(package='kitchensnitch_vision', executable='sink_checker', parameters=params),
        Node(package='kitchensnitch_faucet', executable='faucet_watcher', parameters=params),
        Node(package='kitchensnitch_logic', executable='snitch_logic', parameters=params),
        Node(package='kitchensnitch_logic', executable='telegram_node',
             condition=IfCondition(LaunchConfiguration('telegram'))),
    ])

"""Live system: camera -> detectors -> logic -> Telegram."""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    config = os.path.join(get_package_share_directory('kitchensnitch_bringup'), 'config')
    params = [os.path.join(config, 'zones.yaml'), os.path.join(config, 'params.yaml')]

    return LaunchDescription([
        # camera_ros publishes /camera/image_raw when the node is named "camera"
        Node(package='camera_ros', executable='camera_node', name='camera',
             parameters=[{'width': 1280, 'height': 720}]),
        Node(package='kitchensnitch_vision', executable='pitcher_tracker', parameters=params),
        Node(package='kitchensnitch_vision', executable='sink_checker', parameters=params),
        Node(package='kitchensnitch_faucet', executable='faucet_watcher', parameters=params),
        Node(package='kitchensnitch_logic', executable='snitch_logic', parameters=params),
        Node(package='kitchensnitch_logic', executable='telegram_node'),
    ])

"""Finds the neon tag on the pitcher and publishes PitcherEvent on state changes."""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image

from kitchensnitch_interfaces.msg import PitcherEvent

from .pitcher_state import PitcherStateMachine

PROCESS_WIDTH = 640


class PitcherTracker(Node):
    def __init__(self):
        super().__init__('pitcher_tracker')
        self.hsv_low = np.array(
            self.declare_parameter('tag_hsv_low', [40, 120, 120]).value, dtype=np.uint8)
        self.hsv_high = np.array(
            self.declare_parameter('tag_hsv_high', [80, 255, 255]).value, dtype=np.uint8)
        self.min_area = self.declare_parameter('min_tag_area_px', 150).value
        fridge_zone = self.declare_parameter('fridge_zone', [0.70, 0.10, 0.28, 0.80]).value
        sink_zone = self.declare_parameter('sink_zone', [0.10, 0.45, 0.40, 0.35]).value
        debounce = self.declare_parameter('debounce_frames', 5).value
        return_gone_s = self.declare_parameter('return_gone_s', 3.0).value

        self.sm = PitcherStateMachine(fridge_zone, sink_zone, debounce, return_gone_s)
        self.bridge = CvBridge()
        self.kernel = np.ones((3, 3), np.uint8)
        self.pub = self.create_publisher(PitcherEvent, '/events/pitcher', 10)
        self.create_subscription(Image, '/camera/image_raw', self._on_image, qos_profile_sensor_data)
        self.get_logger().info('pitcher_tracker ready')

    def _find_tag(self, frame):
        """Return the normalized centroid of the biggest tag-colored blob, or None."""
        h, w = frame.shape[:2]
        scale = PROCESS_WIDTH / w
        small = cv2.resize(frame, (PROCESS_WIDTH, int(h * scale)))
        hsv = cv2.cvtColor(small, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.hsv_low, self.hsv_high)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, self.kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, self.kernel)
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contours:
            return None
        best = max(contours, key=cv2.contourArea)
        # min area is defined at 640 px width so it behaves the same at any camera resolution
        if cv2.contourArea(best) < self.min_area:
            return None
        m = cv2.moments(best)
        if m['m00'] == 0:
            return None
        sh, sw = small.shape[:2]
        return m['m10'] / m['m00'] / sw, m['m01'] / m['m00'] / sh

    def _on_image(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        stamp = msg.header.stamp
        t = stamp.sec + stamp.nanosec * 1e-9
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9
        for code, x, y in self.sm.update(self._find_tag(frame), t):
            out = PitcherEvent()
            out.stamp = msg.header.stamp
            out.event = code
            out.x = float(x)
            out.y = float(y)
            self.pub.publish(out)
            self.get_logger().info(f'pitcher event {code} at ({x:.2f}, {y:.2f})')


def main(args=None):
    rclpy.init(args=args)
    node = PitcherTracker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()

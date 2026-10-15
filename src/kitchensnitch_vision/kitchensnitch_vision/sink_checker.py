"""Compares the sink basin to an empty reference and publishes SinkState on change."""
import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_srvs.srv import Trigger

from kitchensnitch_interfaces.msg import SinkState

from .zones import zone_to_rect

PROCESS_WIDTH = 640
PIXEL_DIFF = 30            # gray level difference that counts as a changed pixel
BUSY_MOTION_RATIO = 0.05   # frame-to-frame change above this means someone is at the sink


class SinkChecker(Node):
    def __init__(self):
        super().__init__('sink_checker')
        self.zone = self.declare_parameter('sink_zone', [0.10, 0.45, 0.40, 0.35]).value
        self.full_threshold = self.declare_parameter('sink_full_threshold', 0.12).value
        self.hold_s = self.declare_parameter('state_hold_s', 60.0).value

        self.bridge = CvBridge()
        self.reference = None
        self.prev = None
        self.full = False
        self._candidate = False
        self._candidate_since = None

        self.pub = self.create_publisher(SinkState, '/events/sink', 10)
        self.create_service(Trigger, '~/capture_reference', self._capture_reference)
        self.create_subscription(Image, '/camera/image_raw', self._on_image, qos_profile_sensor_data)
        self._want_reference = True  # first good frame becomes the empty reference
        self.get_logger().info('sink_checker ready, first frame becomes the empty reference')

    def _crop_gray(self, msg):
        frame = self.bridge.imgmsg_to_cv2(msg, 'bgr8')
        h, w = frame.shape[:2]
        scale = PROCESS_WIDTH / w
        small = cv2.resize(frame, (PROCESS_WIDTH, int(h * scale)))
        x0, y0, x1, y1 = zone_to_rect(self.zone, small.shape[1], small.shape[0])
        gray = cv2.cvtColor(small[y0:y1, x0:x1], cv2.COLOR_BGR2GRAY)
        return cv2.GaussianBlur(gray, (5, 5), 0)

    def _capture_reference(self, _request, response):
        self._want_reference = True
        response.success = True
        response.message = 'Will capture the next frame as the empty-sink reference'
        return response

    @staticmethod
    def _changed_ratio(a, b):
        diff = cv2.absdiff(a, b)
        return float(np.count_nonzero(diff > PIXEL_DIFF)) / diff.size

    def _on_image(self, msg):
        gray = self._crop_gray(msg)
        stamp = msg.header.stamp
        t = stamp.sec + stamp.nanosec * 1e-9
        if t == 0.0:
            t = self.get_clock().now().nanoseconds * 1e-9

        if self._want_reference:
            self.reference = gray
            self._want_reference = False
            self.prev = gray
            self.get_logger().info('Empty-sink reference captured')
            return

        busy = self.prev is not None and self._changed_ratio(gray, self.prev) > BUSY_MOTION_RATIO
        self.prev = gray
        if busy:
            # someone is standing at the sink, don't mistake a person for dishes
            self._candidate_since = None
            return

        ratio = self._changed_ratio(gray, self.reference)
        looks_full = ratio > self.full_threshold
        if looks_full == self.full:
            self._candidate_since = None
            return
        if looks_full != self._candidate or self._candidate_since is None:
            self._candidate = looks_full
            self._candidate_since = t
        elif t - self._candidate_since >= self.hold_s:
            self.full = looks_full
            self._candidate_since = None
            out = SinkState()
            out.stamp = msg.header.stamp
            out.full = self.full
            out.changed_ratio = ratio
            self.pub.publish(out)
            self.get_logger().info(f'sink is now {"full" if self.full else "empty"} ({ratio:.2f})')


def main(args=None):
    rclpy.init(args=args)
    node = SinkChecker()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()

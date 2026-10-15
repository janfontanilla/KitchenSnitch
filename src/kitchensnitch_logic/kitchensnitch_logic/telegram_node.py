"""Sends /alerts to a Telegram group chat. Token and chat id come from env vars."""
import json
import os
import threading
import time
import urllib.request

import rclpy
from rclpy.node import Node

from kitchensnitch_interfaces.msg import Alert


class TelegramNode(Node):
    def __init__(self):
        super().__init__('telegram_node')
        self._token = os.environ.get('TELEGRAM_BOT_TOKEN')
        self._chat_id = os.environ.get('TELEGRAM_CHAT_ID')
        if not self._token or not self._chat_id:
            self.get_logger().warn(
                'TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID not set, alerts will only be logged')
        self.create_subscription(Alert, '/alerts', self._on_alert, 10)

    def _on_alert(self, msg):
        self.get_logger().info(f'Alert: {msg.text}')
        if self._token and self._chat_id:
            # send off the executor thread so network retries never block ROS callbacks
            threading.Thread(target=self._send, args=(msg.text,), daemon=True).start()

    def _send(self, text, attempts=3):
        url = f'https://api.telegram.org/bot{self._token}/sendMessage'
        body = json.dumps({'chat_id': self._chat_id, 'text': text}).encode()
        request = urllib.request.Request(
            url, data=body, headers={'Content-Type': 'application/json'})
        for attempt in range(attempts):
            try:
                with urllib.request.urlopen(request, timeout=10):
                    return
            except Exception as err:  # network down, bad token, rate limit
                # log the error type only: the exception text can contain the bot token in the URL
                self.get_logger().warn(
                    f'Telegram send failed ({attempt + 1}/{attempts}): {type(err).__name__}')
                time.sleep(2 ** attempt)
        self.get_logger().error('Telegram send gave up, alert not delivered')


def main(args=None):
    rclpy.init(args=args)
    node = TelegramNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()

"""ROS node that feeds detector events into ChoreRules and publishes alerts."""
import json
import os
from datetime import datetime

import rclpy
from rclpy.node import Node

from kitchensnitch_interfaces.msg import Alert, FaucetEvent, PitcherEvent, SinkState

from .rules import ChoreRules, RulesConfig

PITCHER_NAMES = {0: 'TAKEN', 1: 'NEAR_SINK', 2: 'LEFT_SINK', 3: 'RETURNED'}
FAUCET_NAMES = {0: 'STARTED', 1: 'STOPPED'}
ALERT_NAMES = {0: 'PITCHER_NOT_REFILLED', 1: 'PITCHER_LEFT_OUT', 2: 'DISHES_IN_SINK'}


class SnitchLogic(Node):
    def __init__(self):
        super().__init__('snitch_logic')
        defaults = RulesConfig()
        cfg = RulesConfig(
            refill_min_s=self.declare_parameter('refill_min_s', defaults.refill_min_s).value,
            pitcher_out_max_min=self.declare_parameter(
                'pitcher_out_max_min', defaults.pitcher_out_max_min).value,
            dishes_max_min=self.declare_parameter('dishes_max_min', defaults.dishes_max_min).value,
            alert_cooldown_min=self.declare_parameter(
                'alert_cooldown_min', defaults.alert_cooldown_min).value,
            quiet_start=self.declare_parameter('quiet_start', defaults.quiet_start).value,
            quiet_end=self.declare_parameter('quiet_end', defaults.quiet_end).value,
        )
        self._log_path = self.declare_parameter('log_path', 'logs/events.log').value
        os.makedirs(os.path.dirname(self._log_path) or '.', exist_ok=True)

        self.rules = ChoreRules(cfg)
        self.alert_pub = self.create_publisher(Alert, '/alerts', 10)
        self.create_subscription(PitcherEvent, '/events/pitcher', self._on_pitcher, 10)
        self.create_subscription(FaucetEvent, '/events/faucet', self._on_faucet, 10)
        self.create_subscription(SinkState, '/events/sink', self._on_sink, 10)
        self.create_timer(10.0, self._on_tick)
        self.get_logger().info('snitch_logic ready')

    def _on_pitcher(self, msg):
        now = datetime.now()
        self._log({'type': 'pitcher', 'event': PITCHER_NAMES.get(msg.event, msg.event)}, now)
        self._handle(self.rules.on_pitcher(msg.event, now))

    def _on_faucet(self, msg):
        now = datetime.now()
        record = {'type': 'faucet', 'event': FAUCET_NAMES.get(msg.event, msg.event)}
        if msg.event == FaucetEvent.STOPPED:
            record['duration_s'] = round(msg.duration_s, 1)
        self._log(record, now)
        self._handle(self.rules.on_faucet(msg.event, msg.duration_s, now))

    def _on_sink(self, msg):
        now = datetime.now()
        self._log({'type': 'sink', 'full': msg.full}, now)
        self._handle(self.rules.on_sink(msg.full, now))

    def _on_tick(self):
        self._handle(self.rules.tick(datetime.now()))

    def _handle(self, alerts):
        for alert in alerts:
            self._log({'type': 'alert', 'kind': ALERT_NAMES[alert.kind],
                       'sent': not alert.quiet}, alert.at)
            if alert.quiet:
                continue
            out = Alert()
            out.stamp = self.get_clock().now().to_msg()
            out.kind = alert.kind
            out.text = alert.text
            self.alert_pub.publish(out)

    def _log(self, record, when):
        record = {'t': when.isoformat(timespec='seconds'), **record}
        with open(self._log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(record) + '\n')


def main(args=None):
    rclpy.init(args=args)
    node = SnitchLogic()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.try_shutdown()

"""Chore rules. Pure Python, no ROS and no camera, so it can be unit tested.

Every method takes `now` (a datetime) so tests can control time.
Constants mirror the values in kitchensnitch_interfaces/msg.
"""
from dataclasses import dataclass
from datetime import datetime, time as dtime, timedelta
from typing import List, Optional

# PitcherEvent.event
TAKEN, NEAR_SINK, LEFT_SINK, RETURNED = 0, 1, 2, 3
# FaucetEvent.event
FAUCET_STARTED, FAUCET_STOPPED = 0, 1
# Alert.kind
PITCHER_NOT_REFILLED, PITCHER_LEFT_OUT, DISHES_IN_SINK = 0, 1, 2

ALERT_TEXT = {
    PITCHER_NOT_REFILLED: 'The pitcher just went back in the fridge without a refill.',
    PITCHER_LEFT_OUT: 'The pitcher has been out of the fridge for {minutes} minutes.',
    DISHES_IN_SINK: 'The sink has had dishes in it for {minutes} minutes.',
}


@dataclass
class RulesConfig:
    refill_min_s: float = 20.0
    pitcher_out_max_min: float = 15.0
    dishes_max_min: float = 30.0
    alert_cooldown_min: float = 30.0
    quiet_start: str = '23:00'
    quiet_end: str = '07:00'


@dataclass
class AlertOut:
    kind: int
    text: str
    at: datetime
    quiet: bool  # True during quiet hours: log it, don't send it


def _parse_hhmm(value: str) -> dtime:
    hour, minute = value.split(':')
    return dtime(int(hour), int(minute))


class ChoreRules:
    def __init__(self, cfg: Optional[RulesConfig] = None):
        self.cfg = cfg or RulesConfig()
        self._last_alert = {}
        # pitcher state
        self.pitcher_out = False
        self.refilled = False
        self._out_since: Optional[datetime] = None
        self._left_out_alerted = False
        self._near_intervals: List[list] = []  # [start, end or None]
        # sink state
        self._full_since: Optional[datetime] = None

    # ---- inputs -------------------------------------------------------

    def on_pitcher(self, event: int, now: datetime) -> List[AlertOut]:
        out: List[AlertOut] = []
        if event == TAKEN:
            self.pitcher_out = True
            self.refilled = False
            self._out_since = now
            self._left_out_alerted = False
            self._near_intervals = []
        elif event == NEAR_SINK:
            if self.pitcher_out and not self._near_open():
                self._near_intervals.append([now, None])
        elif event == LEFT_SINK:
            self._close_near(now)
        elif event == RETURNED:
            self._close_near(now)
            if self.pitcher_out and not self.refilled:
                out += self._emit(PITCHER_NOT_REFILLED, now)
            self.pitcher_out = False
            self._out_since = None
        return out

    def on_faucet(self, event: int, duration_s: float, now: datetime) -> List[AlertOut]:
        if event != FAUCET_STOPPED or not self.pitcher_out:
            return []
        if duration_s < self.cfg.refill_min_s:
            return []
        run_start = now - timedelta(seconds=duration_s)
        if self._near_overlap_s(run_start, now) >= 0.5 * duration_s:
            self.refilled = True
        return []

    def on_sink(self, full: bool, now: datetime) -> List[AlertOut]:
        if full and self._full_since is None:
            self._full_since = now
        elif not full:
            self._full_since = None
        return []

    def tick(self, now: datetime) -> List[AlertOut]:
        """Call every few seconds to fire the timer based alerts."""
        out: List[AlertOut] = []
        if (self.pitcher_out and self._out_since and not self._left_out_alerted
                and now - self._out_since > timedelta(minutes=self.cfg.pitcher_out_max_min)):
            alerts = self._emit(PITCHER_LEFT_OUT, now, minutes=int(self.cfg.pitcher_out_max_min))
            if alerts:
                self._left_out_alerted = True
            out += alerts
        if (self._full_since
                and now - self._full_since >= timedelta(minutes=self.cfg.dishes_max_min)):
            out += self._emit(DISHES_IN_SINK, now, minutes=int(self.cfg.dishes_max_min))
        return out

    # ---- helpers ------------------------------------------------------

    def _near_open(self) -> bool:
        return bool(self._near_intervals) and self._near_intervals[-1][1] is None

    def _close_near(self, now: datetime) -> None:
        if self._near_open():
            self._near_intervals[-1][1] = now

    def _near_overlap_s(self, start: datetime, end: datetime) -> float:
        total = 0.0
        for begin, finish in self._near_intervals:
            finish = finish or end
            lo, hi = max(begin, start), min(finish, end)
            if hi > lo:
                total += (hi - lo).total_seconds()
        return total

    def is_quiet(self, now: datetime) -> bool:
        start, end, t = _parse_hhmm(self.cfg.quiet_start), _parse_hhmm(self.cfg.quiet_end), now.time()
        if start <= end:
            return start <= t < end
        return t >= start or t < end  # wraps midnight

    def _emit(self, kind: int, now: datetime, **fmt) -> List[AlertOut]:
        last = self._last_alert.get(kind)
        if last and now - last < timedelta(minutes=self.cfg.alert_cooldown_min):
            return []
        self._last_alert[kind] = now
        text = ALERT_TEXT[kind].format(**fmt)
        return [AlertOut(kind, text, now, self.is_quiet(now))]

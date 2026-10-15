"""Pitcher state machine. Pure Python so it can be tested without ROS or OpenCV.

Fed one observation per frame: the tag centroid (normalized x, y) or None if the
tag isn't visible. Returns the events that fired on that frame as (code, x, y).
Event codes match kitchensnitch_interfaces/msg/PitcherEvent.
"""
from typing import List, Optional, Sequence, Tuple

from .zones import in_zone

TAKEN, NEAR_SINK, LEFT_SINK, RETURNED = 0, 1, 2, 3
IN_FRIDGE, OUT, AT_SINK = 'IN_FRIDGE', 'OUT', 'NEAR_SINK'

Point = Tuple[float, float]


class PitcherStateMachine:
    def __init__(self, fridge_zone: Sequence[float], sink_zone: Sequence[float],
                 debounce_frames: int = 5, return_gone_s: float = 3.0):
        self.fridge_zone = fridge_zone
        self.sink_zone = sink_zone
        self.debounce_frames = debounce_frames
        self.return_gone_s = return_gone_s
        self.state = IN_FRIDGE
        self._seen = 0            # consecutive frames with the tag outside the fridge
        self._in_sink = 0         # consecutive frames inside the sink zone
        self._not_in_sink = 0     # consecutive frames outside the sink zone
        self._gone_since: Optional[float] = None
        self._last_in_fridge = False

    def update(self, point: Optional[Point], t: float) -> List[Tuple[int, float, float]]:
        events: List[Tuple[int, float, float]] = []

        if point is None:
            self._seen = self._in_sink = self._not_in_sink = 0
            if self.state != IN_FRIDGE:
                if self._gone_since is None:
                    self._gone_since = t
                elif t - self._gone_since >= self.return_gone_s and self._last_in_fridge:
                    self.state = IN_FRIDGE
                    self._gone_since = None
                    events.append((RETURNED, 0.0, 0.0))
            return events

        x, y = point
        self._gone_since = None
        in_fridge = in_zone(point, self.fridge_zone)
        self._last_in_fridge = in_fridge

        if self.state == IN_FRIDGE:
            self._seen = 0 if in_fridge else self._seen + 1
            if self._seen >= self.debounce_frames:
                self.state = OUT
                self._seen = 0
                events.append((TAKEN, x, y))
            return events

        in_sink = in_zone(point, self.sink_zone)
        if self.state == OUT:
            self._in_sink = self._in_sink + 1 if in_sink else 0
            if self._in_sink >= self.debounce_frames:
                self.state = AT_SINK
                self._in_sink = 0
                events.append((NEAR_SINK, x, y))
        else:  # AT_SINK
            self._not_in_sink = 0 if in_sink else self._not_in_sink + 1
            if self._not_in_sink >= self.debounce_frames:
                self.state = OUT
                self._not_in_sink = 0
                events.append((LEFT_SINK, x, y))
        return events

from kitchensnitch_vision.pitcher_state import (
    LEFT_SINK, NEAR_SINK, RETURNED, TAKEN, PitcherStateMachine,
)
from kitchensnitch_vision.zones import in_zone, zone_to_rect

FRIDGE = [0.70, 0.10, 0.28, 0.80]
SINK = [0.10, 0.45, 0.40, 0.35]
IN_FRIDGE_PT = (0.80, 0.50)
IN_SINK_PT = (0.30, 0.60)
ON_COUNTER_PT = (0.55, 0.30)  # neither fridge nor sink


def run(sm, points, start_t=0.0, dt=0.1):
    """Feed points frame by frame, return the list of event codes fired."""
    fired = []
    for i, p in enumerate(points):
        fired += [e[0] for e in sm.update(p, start_t + i * dt)]
    return fired


def make():
    return PitcherStateMachine(FRIDGE, SINK, debounce_frames=5, return_gone_s=3.0)


def test_taken_needs_debounce():
    assert run(make(), [ON_COUNTER_PT] * 4) == []
    assert run(make(), [ON_COUNTER_PT] * 5) == [TAKEN]


def test_single_noisy_frame_is_ignored():
    sm = make()
    assert run(sm, [ON_COUNTER_PT, None, ON_COUNTER_PT, None, ON_COUNTER_PT]) == []


def test_full_trip_with_refill():
    sm = make()
    trip = (
        [ON_COUNTER_PT] * 5              # TAKEN
        + [IN_SINK_PT] * 5               # NEAR_SINK
        + [ON_COUNTER_PT] * 5            # LEFT_SINK
        + [IN_FRIDGE_PT] * 3             # walking back toward the fridge
        + [None] * 40                    # tag disappears inside the fridge (4 s)
    )
    assert run(sm, trip) == [TAKEN, NEAR_SINK, LEFT_SINK, RETURNED]


def test_not_returned_if_tag_vanishes_away_from_fridge():
    sm = make()
    run(sm, [ON_COUNTER_PT] * 5)  # TAKEN
    assert run(sm, [None] * 100, start_t=1.0) == []  # hand covers it, never near the fridge


def test_returned_needs_the_gone_timer():
    sm = make()
    run(sm, [ON_COUNTER_PT] * 5 + [IN_FRIDGE_PT] * 2)
    assert run(sm, [None] * 20, start_t=1.0) == []        # only 2 s gone
    assert run(sm, [None] * 20, start_t=3.0) == [RETURNED]


def test_zone_helpers():
    assert in_zone((0.8, 0.5), FRIDGE)
    assert not in_zone((0.3, 0.3), FRIDGE)
    assert zone_to_rect([0.0, 0.0, 1.0, 1.0], 640, 360) == (0, 0, 640, 360)
    x0, y0, x1, y1 = zone_to_rect([0.25, 0.35, 0.08, 0.12], 640, 360)
    assert abs((x1 - x0) - 0.08 * 640) <= 1
    assert abs((y1 - y0) - 0.12 * 360) <= 1

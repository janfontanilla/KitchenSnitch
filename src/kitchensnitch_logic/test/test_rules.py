from datetime import datetime, timedelta

from kitchensnitch_logic.rules import (
    DISHES_IN_SINK, FAUCET_STOPPED, LEFT_SINK, NEAR_SINK, PITCHER_LEFT_OUT,
    PITCHER_NOT_REFILLED, RETURNED, TAKEN, ChoreRules,
)

T0 = datetime(2026, 10, 20, 14, 0, 0)


def at(seconds):
    return T0 + timedelta(seconds=seconds)


def kinds(alerts):
    return [a.kind for a in alerts]


def test_refill_then_return_gives_no_alert():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    r.on_pitcher(NEAR_SINK, at(5))
    r.on_faucet(FAUCET_STOPPED, 25, at(40))
    r.on_pitcher(LEFT_SINK, at(45))
    assert r.on_pitcher(RETURNED, at(60)) == []


def test_return_without_tap_alerts():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    assert kinds(r.on_pitcher(RETURNED, at(30))) == [PITCHER_NOT_REFILLED]


def test_short_tap_run_does_not_count():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    r.on_pitcher(NEAR_SINK, at(2))
    r.on_faucet(FAUCET_STOPPED, 10, at(15))
    assert kinds(r.on_pitcher(RETURNED, at(30))) == [PITCHER_NOT_REFILLED]


def test_handwashing_with_pitcher_away_from_sink_does_not_count():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    r.on_faucet(FAUCET_STOPPED, 30, at(50))  # pitcher never near the sink
    assert kinds(r.on_pitcher(RETURNED, at(70))) == [PITCHER_NOT_REFILLED]


def test_pitcher_near_sink_for_only_a_bit_of_the_run_does_not_count():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    r.on_pitcher(NEAR_SINK, at(40))  # arrives at the very end of a 30 s run
    r.on_faucet(FAUCET_STOPPED, 30, at(45))  # run was 15..45, overlap only 5 s
    assert kinds(r.on_pitcher(RETURNED, at(60))) == [PITCHER_NOT_REFILLED]


def test_pitcher_left_out_fires_once():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    assert r.tick(at(14 * 60)) == []
    assert kinds(r.tick(at(16 * 60))) == [PITCHER_LEFT_OUT]
    assert r.tick(at(17 * 60)) == []


def test_dishes_alert_after_30_minutes():
    r = ChoreRules()
    r.on_sink(True, at(0))
    assert r.tick(at(29 * 60)) == []
    assert kinds(r.tick(at(31 * 60))) == [DISHES_IN_SINK]


def test_dishes_cleared_before_30_minutes_gives_no_alert():
    r = ChoreRules()
    r.on_sink(True, at(0))
    r.on_sink(False, at(20 * 60))
    assert r.tick(at(40 * 60)) == []


def test_cooldown_blocks_repeat_then_allows_after_30_minutes():
    r = ChoreRules()
    r.on_sink(True, at(0))
    assert len(r.tick(at(31 * 60))) == 1
    assert r.tick(at(40 * 60)) == []
    assert len(r.tick(at(62 * 60))) == 1


def test_same_violation_twice_in_cooldown_sends_once():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    assert len(r.on_pitcher(RETURNED, at(10))) == 1
    r.on_pitcher(TAKEN, at(60))
    assert r.on_pitcher(RETURNED, at(120)) == []


def test_quiet_hours_flag_alert_as_quiet():
    r = ChoreRules()
    midnight = datetime(2026, 10, 21, 0, 0, 0)
    r.on_pitcher(TAKEN, midnight)
    alerts = r.on_pitcher(RETURNED, midnight + timedelta(seconds=30))
    assert kinds(alerts) == [PITCHER_NOT_REFILLED]
    assert alerts[0].quiet is True


def test_daytime_alert_is_not_quiet():
    r = ChoreRules()
    r.on_pitcher(TAKEN, at(0))
    assert r.on_pitcher(RETURNED, at(30))[0].quiet is False

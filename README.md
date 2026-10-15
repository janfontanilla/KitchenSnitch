# KitchenSnitch

A ROS2 system on a Raspberry Pi 5 that watches the kitchen sink and fridge with one camera, and calls out skipped chores in the family group chat.

- **Pitcher not refilled:** the pitcher gets taken out and put back without the tap running for 20+ seconds near the sink.
- **Dishes left in the sink:** the sink stays full for 30+ minutes.

Everything runs on the Pi. No video leaves the device.

## Stack

Raspberry Pi 5 · Camera Module 3 Wide · Ubuntu 24.04 · ROS2 Jazzy · OpenCV · Python + C++ · Telegram Bot API

## Architecture

```
camera_node ──/camera/image_raw──┬──> pitcher_tracker ──/events/pitcher──┐
                                 ├──> faucet_watcher ───/events/faucet───┼──> snitch_logic ──/alerts──> telegram_node
                                 └──> sink_checker ─────/events/sink─────┘
```

## Docs

The full design, covering hardware, nodes, messages, setup, testing and milestones, is in [docs/TECHNICAL_DESIGN.md](docs/TECHNICAL_DESIGN.md).

## Repository layout

| Package | What it is |
|---|---|
| `kitchensnitch_interfaces` | Custom messages: `PitcherEvent`, `FaucetEvent`, `SinkState`, `Alert` |
| `kitchensnitch_vision` | `pitcher_tracker` and `sink_checker` (Python, OpenCV) |
| `kitchensnitch_faucet` | `faucet_watcher` (C++, OpenCV) |
| `kitchensnitch_logic` | `snitch_logic` rules and `telegram_node` |
| `kitchensnitch_bringup` | Launch files and config (zones, thresholds) |

## Build and run

On Ubuntu 24.04 with ROS2 Jazzy:

```bash
colcon build --symlink-install
source install/setup.bash
ros2 launch kitchensnitch_bringup kitchensnitch.launch.py      # live camera
ros2 launch kitchensnitch_bringup replay.launch.py bag:=bags/session_01   # recorded footage
```

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in the environment for real alerts. Without them, alerts are only logged.

## Tests

The decision logic has no ROS dependency and runs anywhere with pytest:

```bash
cd src/kitchensnitch_logic && python -m pytest test
cd src/kitchensnitch_vision && python -m pytest test
```

## Status

Code scaffolded, with unit tests for the chore rules and the pitcher state machine passing. The ROS2 build and the vision nodes have **not** been run on real hardware yet: the Pi, camera and ROS2 environment come next, then tuning against recorded footage.

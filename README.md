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

## Status

Planning. Hardware is on order, and the ROS2 workspace is next.

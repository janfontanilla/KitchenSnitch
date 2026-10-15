# KitchenSnitch: Technical Design Document

Version 0.1 (October 2026)
Author: Jan Fontanilla

## 1. Overview

KitchenSnitch is a ROS2 system running on a Raspberry Pi 5 with one wide-angle camera aimed at the kitchen sink and fridge. It watches for two skipped chores and posts a reminder to the family group chat on Telegram:

1. **Pitcher not refilled.** Someone takes the water pitcher out and puts it back without running the tap to refill it.
2. **Dishes left in the sink.** The sink stays full for too long.

Everything runs on the Pi. No video leaves the device and, in normal operation, no video is saved. Only small event logs are kept.

### 1.1 Goals

- Detect the two chore violations reliably enough that the family trusts the reminders.
- Build it as a proper ROS2 system (nodes, topics, custom messages, launch files, bag-based testing) so it doubles as robotics portfolio work.
- Include at least one C++ node.
- Make every detector testable offline against recorded footage.

### 1.2 Non-goals

- Identifying *who* skipped the chore. No face recognition.
- Measuring how much water is actually in the pitcher. A 20 second tap run counts as a refill.
- Running a large AI model. Classic computer vision (OpenCV) covers v1. ML detection is a possible later upgrade (see section 11).

## 2. Requirements

### 2.1 Functional

| ID | Requirement |
|---|---|
| F1 | Detect when the pitcher is taken out of the fridge and when it is returned. |
| F2 | Detect when the faucet is running and for how long. |
| F3 | Mark the pitcher as refilled if the faucet runs for 20 s or more while the pitcher is near the sink. |
| F4 | Send a pitcher alert if the pitcher is returned without a refill. |
| F5 | Send a pitcher alert if the pitcher has been out for more than 15 minutes. |
| F6 | Detect whether the sink is empty or has dishes in it. |
| F7 | Send a dishes alert if the sink has been full for 30 minutes or more. |
| F8 | Deliver alerts to a Telegram group chat. |
| F9 | Write every event and alert to a local log file. |

### 2.2 Non-functional

| ID | Requirement |
|---|---|
| N1 | Process at least 5 frames per second on a Pi 5 4GB. |
| N2 | Don't repeat the same alert more than once every 30 minutes. |
| N3 | Respect quiet hours (default 23:00 to 07:00): no alerts sent, events still logged. |
| N4 | Keep secrets (Telegram token) out of the repo. |
| N5 | All thresholds and zones configurable in YAML, no code changes needed. |

## 3. Hardware

| Part | Purpose | Approx. CAD |
|---|---|---|
| Raspberry Pi 5, 4GB | Main computer | $155 |
| Official 27W USB-C power supply | Stable power under load | $17 |
| 64GB microSD (A2 rated) | OS, ROS2, logs, test recordings | $13 |
| Camera Module 3 Wide | 120° diagonal view covers sink and fridge | $38 |
| Pi 5 camera cable, 300 mm or longer | Pi 5 uses the smaller 22-pin connector | $3 to $5 |
| Active cooler | Sustained vision processing heats the CPU | $7 |
| Case compatible with the cooler | Protection and mounting | $13 |
| Neon tape (bright green or pink) | Visual tag on the pitcher | $3 |
| **Total** | | **~$250 before tax** |

Optional later: Raspberry Pi AI HAT+ (~$100) if ML-based detection is added.

### 3.1 Mounting

- Mount high on a wall or cabinet, angled down so the sink basin, faucet and fridge door are all in frame.
- Avoid pointing it at a window. Backlight wrecks the sink comparison.
- Once the zones are calibrated, the camera must not move. Use a rigid mount, not tape.

## 4. Software stack

| Layer | Choice |
|---|---|
| OS | Ubuntu 24.04 LTS (64-bit) for Raspberry Pi |
| ROS | ROS2 Jazzy Jalisco |
| Camera driver | `camera_ros` (libcamera based) |
| Vision | OpenCV 4 (Python `cv2` and C++) |
| Image transport | `cv_bridge`, `image_transport` |
| Languages | Python 3.12, C++17 |
| Build | `colcon`, `ament_python`, `ament_cmake` |
| Alerts | Telegram Bot API over HTTPS |
| Dev machine | Ubuntu 24.04 or WSL2 on Windows with ROS2 Jazzy |

## 5. System architecture

```
                         /camera/image_raw
 ┌────────────┐      (sensor_msgs/Image, ~10 Hz)
 │ camera_node│────────────────┬─────────────────────┬─────────────────────┐
 └────────────┘                │                     │                     │
                               ▼                     ▼                     ▼
                      ┌─────────────────┐   ┌─────────────────┐   ┌───────────────┐
                      │ pitcher_tracker │   │ faucet_watcher  │   │ sink_checker  │
                      │    (Python)     │   │     (C++)       │   │   (Python)    │
                      └────────┬────────┘   └────────┬────────┘   └───────┬───────┘
                 /events/pitcher│         /events/faucet│      /events/sink │
                               └──────────────┬─────────┴───────────────────┘
                                              ▼
                                     ┌─────────────────┐
                                     │  snitch_logic   │──── logs/events.log
                                     │    (Python)     │
                                     └────────┬────────┘
                                              │ /alerts
                                              ▼
                                     ┌─────────────────┐
                                     │  telegram_node  │──── Telegram group chat
                                     │    (Python)     │
                                     └─────────────────┘
```

Each detector only knows about its own job. All the "is this a violation?" reasoning lives in `snitch_logic`. That means detectors can be swapped or retuned without touching the rules, and the rules can be tested by publishing fake events with no camera at all.

## 6. Repository layout

```
KitchenSnitch/
├── README.md
├── LICENSE
├── .github/workflows/tests.yml     # runs the pure-Python tests on every push
├── docs/
│   └── TECHNICAL_DESIGN.md
├── scripts/
│   └── calibrate_zones.py          # drag-a-rectangle zone tool, writes zones.yaml
├── bags/                           # recorded test footage (gitignored)
├── logs/                           # runtime event logs (gitignored)
└── src/
    ├── kitchensnitch_interfaces/   # custom .msg definitions (ament_cmake)
    ├── kitchensnitch_vision/       # pitcher_tracker, sink_checker (ament_python)
    │   └── kitchensnitch_vision/pitcher_state.py   # tag state machine, no ROS imports
    ├── kitchensnitch_faucet/       # faucet_watcher (ament_cmake, C++)
    ├── kitchensnitch_logic/        # snitch_logic, telegram_node (ament_python)
    │   └── kitchensnitch_logic/rules.py            # chore rules, no ROS imports
    └── kitchensnitch_bringup/      # launch files and config
        ├── config/zones.yaml       # fridge, sink, faucet regions
        ├── config/params.yaml      # thresholds, timers, quiet hours
        └── launch/
            ├── kitchensnitch.launch.py   # live camera
            └── replay.launch.py          # bag playback for testing
```

The decision logic (`rules.py`, `pitcher_state.py`) is kept free of ROS imports on purpose, so it runs under plain `pytest` on any machine, including CI.

## 7. Interfaces

### 7.1 Topics

| Topic | Type | Publisher | Subscribers |
|---|---|---|---|
| `/camera/image_raw` | `sensor_msgs/Image` | camera_node | all detectors |
| `/events/pitcher` | `kitchensnitch_interfaces/PitcherEvent` | pitcher_tracker | snitch_logic |
| `/events/faucet` | `kitchensnitch_interfaces/FaucetEvent` | faucet_watcher | snitch_logic |
| `/events/sink` | `kitchensnitch_interfaces/SinkState` | sink_checker | snitch_logic |
| `/alerts` | `kitchensnitch_interfaces/Alert` | snitch_logic | telegram_node |
| `/debug/overlay` | `sensor_msgs/Image` | each detector (optional) | rqt_image_view |

Detectors publish **on change**, not every frame. That keeps the event topics quiet and easy to read with `ros2 topic echo`.

### 7.2 Message definitions

`PitcherEvent.msg`
```
builtin_interfaces/Time stamp
uint8 TAKEN=0
uint8 NEAR_SINK=1
uint8 LEFT_SINK=2
uint8 RETURNED=3
uint8 event
float32 x        # tag centroid, normalized 0..1
float32 y
```

`FaucetEvent.msg`
```
builtin_interfaces/Time stamp
uint8 STARTED=0
uint8 STOPPED=1
uint8 event
float32 duration_s   # filled on STOPPED
```

`SinkState.msg`
```
builtin_interfaces/Time stamp
bool full
float32 changed_ratio   # fraction of sink pixels that differ from the reference
```

`Alert.msg`
```
builtin_interfaces/Time stamp
uint8 PITCHER_NOT_REFILLED=0
uint8 PITCHER_LEFT_OUT=1
uint8 DISHES_IN_SINK=2
uint8 kind
string text
```

## 8. Node specifications

### 8.1 camera_node

Uses the `camera_ros` package instead of writing a driver.

- Resolution: 1280×720 (downscaled to 640×360 inside each detector for speed)
- Frame rate: 10 fps
- Fixed exposure and white balance once tuned, so lighting shifts don't look like "change" to the detectors

### 8.2 pitcher_tracker (Python)

Tracks the neon tag on the pitcher.

1. Convert the frame to HSV.
2. Threshold with `cv2.inRange` using the tag's HSV range from `params.yaml`.
3. Morphological open, then close, to remove speckle.
4. Find contours and keep the largest one above `min_tag_area_px`.
5. Compute its centroid and check which zone it's in (`fridge`, `sink`, or neither).

States: `IN_FRIDGE`, `OUT`, `NEAR_SINK`.

| From | To | Condition | Publishes |
|---|---|---|---|
| IN_FRIDGE | OUT | Tag visible outside the fridge zone for 5 consecutive frames | TAKEN |
| OUT | NEAR_SINK | Centroid in sink zone for 5 frames | NEAR_SINK |
| NEAR_SINK | OUT | Centroid leaves sink zone for 5 frames | LEFT_SINK |
| OUT / NEAR_SINK | IN_FRIDGE | Tag last seen in the fridge zone, then gone for 3 s | RETURNED |

The consecutive-frame counts are debounce. Without them a single bad frame flips the state.

### 8.3 faucet_watcher (C++)

Detects running water through constant motion in a small region under the spout.

1. Crop to the faucet zone and convert to grayscale.
2. Gaussian blur.
3. `cv::absdiff` against the previous frame, then threshold.
4. `motion_ratio = nonzero pixels / zone area`.
5. If `motion_ratio > faucet_motion_threshold`, the frame counts as "running."

Debounce: running must hold for 1 s to publish STARTED, and stop for 1.5 s to publish STOPPED (with `duration_s`). Gaps under 1.5 s don't end the run, because a hand or the pitcher passing through the stream causes brief dropouts.

Written in C++ because it's a tight per-frame pixel loop, and to get hands-on with `rclcpp`, `cv_bridge` and `ament_cmake`.

### 8.4 sink_checker (Python)

Compares the sink basin to a reference photo of the empty sink.

1. On startup (or on the `~/capture_reference` service call), save the current sink zone as the empty reference.
2. Each frame: crop, grayscale, blur, `absdiff` against the reference, threshold.
3. `changed_ratio = changed pixels / zone area`.
4. If `changed_ratio > sink_full_threshold` for 60 s, set `full = true`. Back under for 60 s, set `full = false`.
5. Skip updates while there's heavy motion in the sink zone (someone is standing there washing), so a person isn't mistaken for dishes.

Lighting is the main risk. Fixed camera exposure helps, and the reference can be re-captured with one service call:
```
ros2 service call /sink_checker/capture_reference std_srvs/srv/Trigger
```

### 8.5 snitch_logic (Python)

Holds all the rules. It doesn't touch images.

**Pitcher rule**

```
on TAKEN:              pitcher_out = true, refilled = false, out_since = now
on NEAR_SINK:          near_sink = true
on LEFT_SINK:          near_sink = false
on FaucetEvent STOPPED:
    if pitcher_out and near_sink_during_run and duration_s >= 20:
        refilled = true
on RETURNED:
    if not refilled: alert PITCHER_NOT_REFILLED
    pitcher_out = false
every 10 s:
    if pitcher_out and now - out_since > 15 min: alert PITCHER_LEFT_OUT (once)
```

"near_sink_during_run" means the pitcher was in the sink zone for at least half of the faucet run. That stops handwashing or rinsing from counting as a refill when the pitcher is sitting on the counter somewhere else.

**Dishes rule**

```
on SinkState full=true:   full_since = now
on SinkState full=false:  full_since = none
every 30 s:
    if full_since and now - full_since >= 30 min: alert DISHES_IN_SINK
```

**Shared behaviour**

- Cooldown: the same alert type can't fire more than once per 30 minutes.
- Quiet hours: alerts are logged but not published to `/alerts`.
- Every event and alert gets appended to `logs/events.log` as one line of JSON.

Example log lines:
```
{"t":"2026-10-20T14:32:05","type":"pitcher","event":"TAKEN"}
{"t":"2026-10-20T14:33:40","type":"pitcher","event":"RETURNED"}
{"t":"2026-10-20T14:33:40","type":"alert","kind":"PITCHER_NOT_REFILLED"}
```

### 8.6 telegram_node (Python)

- Subscribes to `/alerts` and sends `text` to a group chat with the Bot API `sendMessage` endpoint.
- Reads `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` from environment variables. Never from a committed file.
- Retries up to 3 times with backoff if the network is down, then logs the failure.

Example messages:
- "The pitcher just went back in the fridge without a refill."
- "The pitcher has been out for 15 minutes."
- "The sink has had dishes in it for 30 minutes."

## 9. Configuration

Both files live in `src/kitchensnitch_bringup/config/` and are passed to every node as ROS parameter files, so each node reads its own section.

`zones.yaml` holds normalized `[x, y, w, h]` regions (0..1 of the frame), so changing resolution doesn't break them:
```yaml
pitcher_tracker:
  ros__parameters:
    fridge_zone: [0.70, 0.10, 0.28, 0.80]
    sink_zone:   [0.10, 0.45, 0.40, 0.35]
sink_checker:
  ros__parameters:
    sink_zone:   [0.10, 0.45, 0.40, 0.35]
faucet_watcher:
  ros__parameters:
    faucet_zone: [0.25, 0.35, 0.08, 0.12]
```

`params.yaml` holds the thresholds and timers (HSV range for the tag, faucet motion threshold, sink-full threshold, 20 s refill, 15 min out, 30 min dishes, 30 min cooldown, quiet hours). See the file for the full list.

`scripts/calibrate_zones.py` takes a photo (or a webcam frame), lets you drag a rectangle for each zone, and writes `zones.yaml`. After changing config, rebuild with `colcon build --symlink-install` or relaunch, since the files are installed into the workspace.

**Replay note:** the detectors use the image timestamps, so bag replay gives the same durations as live. `snitch_logic` uses the wall clock for its timers and quiet hours, so replay bags at normal speed (`--rate 1.0`).

## 10. Setup and build

### 10.1 Dev machine (do this first, while parts ship)

1. Install Ubuntu 24.04, or WSL2 with Ubuntu 24.04 on Windows.
2. Install ROS2 Jazzy (`ros-jazzy-desktop`) following the official docs.
3. Work through the ROS2 beginner tutorials and the TurtleBot3 Gazebo simulation.
4. Clone this repo and confirm it builds:
   ```bash
   cd KitchenSnitch
   colcon build --symlink-install
   source install/setup.bash
   ```

### 10.2 Raspberry Pi

1. Flash Ubuntu Server 24.04 (64-bit) with Raspberry Pi Imager. Set Wi-Fi, a username and SSH in the Imager settings.
2. SSH in and install `ros-jazzy-ros-base`, `ros-jazzy-cv-bridge`, `ros-jazzy-image-transport`, `python3-opencv` and `libopencv-dev`.
3. Install the camera driver: `ros-jazzy-camera-ros`.
4. Test the camera: `ros2 run camera_ros camera_node`, then view it from the dev machine with `rqt_image_view` (both machines on the same `ROS_DOMAIN_ID`).
5. Clone the repo, build, and run calibration.
6. Export the Telegram variables in `~/.bashrc` (see 10.3).
7. Launch:
   ```bash
   ros2 launch kitchensnitch_bringup kitchensnitch.launch.py
   ```
8. Optional: add a `systemd` service so it starts on boot.

**Known risk:** Pi 5 camera support on Ubuntu depends on the libcamera version. If `camera_ros` can't see the camera, there are two fallbacks: build Raspberry Pi's libcamera fork from source, or run Raspberry Pi OS and put ROS2 Jazzy inside a Docker container with the camera passed through. Test this on day one, because the rest of the plan depends on it.

### 10.3 Telegram

1. Message `@BotFather` on Telegram, run `/newbot`, and save the token.
2. Add the bot to the family group chat.
3. Send a message in the group, then open `https://api.telegram.org/bot<TOKEN>/getUpdates` to find the `chat.id`.
4. On the Pi:
   ```bash
   export TELEGRAM_BOT_TOKEN=...
   export TELEGRAM_CHAT_ID=...
   ```

## 11. Testing strategy

### 11.1 Record once, replay forever

With the family's OK, record a few sessions of normal kitchen use:
```bash
ros2 bag record /camera/image_raw -o bags/session_01
```
Make sure the recordings cover: a proper refill, a no-refill return, someone washing hands, dishes piling up, dishes being cleared, and evening lighting.

Then every detector change gets tested by replaying:
```bash
ros2 launch kitchensnitch_bringup replay.launch.py bag:=bags/session_01
```

Bags never get committed (they're gitignored) and get deleted once the system is tuned.

### 11.2 Logic unit tests

`snitch_logic` is pure Python with no camera, so it's tested with `pytest` by feeding it scripted event sequences and checking which alerts come out. For example: TAKEN, NEAR_SINK, faucet 22 s, RETURNED should produce no alert. TAKEN, RETURNED should produce PITCHER_NOT_REFILLED.

### 11.3 Manual event injection

Any rule can be tested live without a camera:
```bash
ros2 topic pub --once /events/pitcher kitchensnitch_interfaces/msg/PitcherEvent "{event: 0}"
```

### 11.4 Acceptance criteria

| Scenario | Expected |
|---|---|
| Pitcher out, refilled at sink for 25 s, returned | No alert |
| Pitcher out, returned with no tap run | PITCHER_NOT_REFILLED |
| Pitcher on the counter, someone washes hands for 30 s, pitcher returned | PITCHER_NOT_REFILLED |
| Pitcher out for 16 min | PITCHER_LEFT_OUT |
| Dishes in sink for 31 min | DISHES_IN_SINK |
| Dishes in sink for 20 min, then cleared | No alert |
| Same violation twice within 30 min | One alert only |
| Violation at midnight | Logged, no message |

Target: at least 9 of 10 correct on each scenario across the recorded bags before going live.

## 12. Milestones

| # | Milestone | Done when |
|---|---|---|
| 0 | ROS2 basics | TurtleBot3 runs in Gazebo on the dev machine, plus one custom pub/sub node |
| 1 | Pi bring-up | Camera frames visible in `rqt_image_view` over the network |
| 2 | Workspace and interfaces | All packages build, custom messages show up in `ros2 interface show` |
| 3 | Recordings | 3 or more bags covering the scenarios in 11.1 |
| 4 | pitcher_tracker | Correct TAKEN and RETURNED events on every bag |
| 5 | faucet_watcher (C++) | Tap durations within ±2 s of the real values |
| 6 | sink_checker | Correct full/empty state on every bag |
| 7 | Logic and alerts | All pytest cases pass, test message arrives in Telegram |
| 8 | Live trial | One week live, before-and-after counts logged |

Each milestone is also one build post for the X account.

## 13. Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Pi 5 camera not working on Ubuntu | Blocks everything | Test on day one, Docker on Raspberry Pi OS as a fallback |
| Lighting changes break the sink check | False dishes alerts | Fixed exposure, hold timers, reference re-capture service |
| Neon tag hidden by a hand | Missed or false RETURNED | Tape on two sides of the pitcher, debounce, 3 s "gone" timer |
| Handwashing counted as a refill | Missed alerts | Require the pitcher in the sink zone for the run |
| Family dislikes being watched | Device gets unplugged | Get consent, no saved video, sink and fridge only in frame |
| Overheating | Throttling, dropped frames | Active cooler, process at 640×360 |

## 14. Privacy

- The camera only frames the sink, faucet and fridge door.
- Frames are processed in memory and dropped.
- Video is only recorded for testing, with consent, and deleted after tuning.
- Logs contain events and times only. No images, no names.
- No cloud services except outgoing Telegram text messages.

## 15. Future work

- Swap color-tag tracking for a small YOLO model running on the AI HAT+.
- Add a load cell under the pitcher so refills are measured, not inferred.
- A simple web dashboard showing the weekly chore stats.
- A Gazebo world of the kitchen to test the logic against simulated events.

# voice_teleop (ROS2 package)

Voice-controlled teleop for tortoisebot. Speak "forward" / "backward" /
"left" / "right" / "stop"; this publishes the matching `geometry_msgs/Twist`
on `/cmd_vel` -- the same topic `teleop_twist_keyboard` uses -- so it drops
straight into your existing bringup as a replacement for Terminal 3.

This is a proper `ament_python` ROS2 package (has `package.xml`, `setup.py`,
`setup.cfg`, `resource/`) -- not loose scripts. All imports inside it are
relative (`.config`, `.voice.recorder`, etc.) so it works once installed.

```
voice_teleop/                  <- this whole folder is the colcon package
├── package.xml
├── setup.py
├── setup.cfg
├── resource/voice_teleop
├── test/                      (standard ament lint tests)
└── voice_teleop/
    ├── __init__.py
    ├── config.py               <- OpenAI keys/models + motion speeds
    ├── voice_teleop_node.py    <- the ROS2 node, run via `ros2 run`
    └── voice/
        ├── __init__.py
        ├── recorder.py         <- mic capture (sounddevice)
        ├── speech_to_text.py   <- Whisper STT (openai)
        ├── intent_parser.py    <- GPT match -> one of the 5 commands
        └── prompts.py
```

## Install

Drop the whole `voice_teleop/` folder into a colcon workspace's `src/`, e.g.:
```bash
cp -r voice_teleop ~/tortoise_ws/src/
```

Install Python deps (inside whatever environment you're building/running
in -- e.g. inside your Docker container on the Pi5):
```bash
pip3 install --break-system-packages openai sounddevice scipy
```
Audio recording also needs `portaudio` at the system level:
```bash
apt-get install -y portaudio19-dev
```

Build:
```bash
cd ~/tortoise_ws
source /opt/ros/jazzy/setup.bash
colcon build --symlink-install --packages-select voice_teleop
source install/setup.bash
```

## Run

Set your OpenAI API key first (required every new shell -- it doesn't
persist across terminals):
```bash
export OPENAI_API_KEY=sk-...
```

Then:
```bash
ros2 run voice_teleop voice_teleop_node
```

Press Enter, speak one of the five commands, and it executes for
`MOVE_DURATION` seconds (see `config.py`) then auto-stops.

## Cross-machine setup (mic device separate from the robot)

If this node runs on a different machine than the robot (e.g. a laptop or a
second Pi providing the mic, while the robot itself runs on `turtlrbotpi4`),
both machines need the same `ROS_DOMAIN_ID` for DDS to bridge `/cmd_vel`
across the network:
```bash
export ROS_DOMAIN_ID=42   # same value on both machines
```
Verify the robot side can see this node's publisher before testing:
```bash
ros2 topic info /cmd_vel
```
Expect `Subscription count: 1` (that's `differential.py` on the robot).

## Known gotchas already fixed in this version

- **Relative imports** -- the original scripts used top-level imports
  (`from config import ...`), which only work as loose files. Fixed to
  `.config` / `..config` / `.voice.recorder` etc. so it works as an
  installed package.
- **`extra_headers={"Accept-Encoding": "identity"}`** on both OpenAI API
  calls (`speech_to_text.py`, `intent_parser.py`) -- avoids a bug in the
  `openai` package's bundled `httpx2` HTTP client where decompressing a
  Brotli-encoded response raises
  `TypeError: process() takes no keyword arguments`.
- **`voice/__init__.py`** -- needed for `voice/` to import as a subpackage.

## Tuning

- `LINEAR_SPEED` / `ANGULAR_SPEED` / `MOVE_DURATION` in `config.py` control
  how far one voice command moves the robot. This is open-loop (no
  obstacle checking) -- start conservative.
- `RECORD_SECONDS` in `config.py` is how long it listens after you press
  Enter.

## Docker mic passthrough (if running inside a container, e.g. on Pi5)

```bash
sudo docker run -it --rm \
  --net=host \
  --device /dev/snd \
  -e ROS_DOMAIN_ID=42 \
  -v ~/tortoise_ws:/root/tortoise_ws \
  tortoise-sim
```
Verify the mic is visible *inside* the container too:
```bash
apt-get install -y alsa-utils
arecord -l
```

# TortoiseBot Software Stack

Custom ROS 2 software stack for the **RigBetel Tortoise** differential drive robot — mapping, navigation, and control, split across two Raspberry Pis.

## Hardware

- **RigBetel Tortoise** — differential drive robot, hardware already assembled, camera onboard
- **Pi 4 (Ubuntu)** — wired directly to the robot, lives in the lab
- **Pi 5 (Raspberry Pi OS)** — at home, used for simulation/homework before lab sessions

ROS 2's DDS-based communication means the stack doesn't need to live on one board — it's split across both Pis over the same Wi-Fi network.

## Architecture

### Pi 4 — Ubuntu — "Edge" node
Native tier-1 ROS 2 support, no Docker needed. Physically connected to the robot.

- **Hardware bridging** — runs `micro_ros_agent` to bridge the TortoiseBot firmware (motor control, encoders) into ROS 2
- **Sensor drivers**:
  - LiDAR driver (`sllidar_ros2` / `rplidar_ros`) → publishes to `/scan`
  - Camera node (`v4l2_camera`) → publishes to `/image_raw`

### Pi 5 — Docker (Jazzy desktop) — "Brain" node
Handles the heavy compute.

- **State publishing** — `robot_state_publisher` loads the TortoiseBot URDF/xacro (camera, wheel, LiDAR positions relative to robot center)
- **Mapping (SLAM)** — `slam_toolbox` (async mode), subscribes to `/scan` + odometry to build a live 2D map
- **Navigation (Nav2)** — plans paths, avoids obstacles using live LiDAR, sends `cmd_vel` back to the Pi 4 to drive the motors

## Build order (4 core layers)

1. **Base controller** — read wheel odometry, send basic `cmd_vel` to drive/turn
2. **TF2 tree** — `odom` → `base_link` → `laser_link`, configured via URDF
3. **SLAM layer** — tune SLAM Toolbox params until a joystick-driven run produces a clean, consistent map
4. **Autonomy layer** — configure Nav2 costmaps to inflate obstacles so the robot doesn't clip corners or hit walls

## Network configuration

Both Pis need to be on the **same Wi-Fi network** for DDS discovery to work across machines. A couple of things to check when wiring the Edge and Brain nodes together:

- Set the **same `ROS_DOMAIN_ID`** (e.g. `export ROS_DOMAIN_ID=42`) on both Pis so they discover each other but stay isolated from other ROS 2 traffic on the lab network
- Confirm the lab network doesn't block multicast/UDP traffic between devices (some enterprise/lab Wi-Fi setups isolate clients from each other — worth testing with `ros2 topic list` from one Pi while a node runs on the other)
- If using Docker on the Pi 5, `--net=host` (already in the run command below) is what lets ROS 2 nodes inside the container see the Pi 4 on the network

> ⚠️ Not yet confirmed: whether the lab Wi-Fi allows this kind of inter-device discovery. Worth testing early rather than after everything else is wired up.

## Pre-lab simulation (Pi 5, Docker)

Since the Tortoise itself lives in the lab, mapping/nav software gets tested first in simulation on the Pi 5.

### 1. Dockerfile

> ⚠️ **ARM64 note:** `osrf/ros:jazzy-desktop` is AMD64-only and fails on the Pi 5 with `expected "linux/arm64" for current build` / `exec format error`. Use the plain `ros:jazzy` base (ARM-compatible) and install the desktop tools manually instead.

```bash
cat << 'EOF' > Dockerfile
FROM ros:jazzy

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    ros-jazzy-desktop \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    ros-jazzy-xacro \
    ros-jazzy-ros-gz \
    python3-colcon-common-extensions \
    && rm -rf /var/lib/apt/lists/*
EOF
```

### 2. Build

```bash
sudo docker build -t tortoise-sim .
```

Installing the full desktop environment manually can take 10–15 minutes.

### 3. Run (with GUI access for Gazebo/RViz)

```bash
xhost +local:root

sudo docker run -it --rm \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  tortoise-sim
```

> **Note:** this uses `--rm` with no volume mount for the workspace — anything created inside the container is lost when it exits. Add a workspace volume mount before doing real work, e.g. `-v ~/tortoise_ws:/root/tortoise_ws`.
>
> **Performance note:** full 3D Gazebo simulation pushes the Pi 5's CPU/RAM hard — expect low framerate.

### 4. Workspace + repo (inside the container)

```bash
mkdir -p ~/tortoise_ws/src
cd ~/tortoise_ws/src

git clone https://github.com/rigbetellabs/tortoisebot.git
git clone https://github.com/prasunjha8/tortoisewithself.git

cd ~/tortoise_ws
source install/setup.bash 2>/dev/null || source /opt/ros/jazzy/setup.bash
```

`tortoisewithself` is PJ's own repo with the URDF/sim files actually being used: `urdf/tortoisebot_sim.xacro`, `tortoisebot_simple.gazebo`, `tortoisebot_simple.xacro`.

**Sanity-check the xacro parses cleanly before building the full workspace:**

```bash
xacro src/tortoisewithself/urdf/tortoisebot_sim.xacro
```

A large block of XML with no errors means the URDF structure is valid.

**Build**, skipping physical-hardware-only packages not needed for simulation (LiDAR/camera drivers), **with `--symlink-install`** so future edits to launch files take effect without a full rebuild:

```bash
colcon build --symlink-install --packages-skip ydlidar_ros2_driver v4l2_camera
```

> If missing-dependency errors come up for other packages, install them directly (`apt install -y ros-jazzy-camera-info-manager`, `ros-jazzy-image-transport`, etc.) and just re-run `colcon build` — it resumes from where it failed. Or use `rosdep` to install everything a workspace needs at once:
> ```bash
> apt update && rosdep init && rosdep update
> rosdep install --from-paths src --ignore-src -r -y
> ```

### 5. Launch the simulation

```bash
source install/setup.bash
ros2 launch tortoisebot_gazebo ignition_sim.launch.py
```

Spawns the robot into `nav2_test_world.sdf` (bundled with the package, not a custom RigBetel world). Confirmed working: Gazebo renders, robot spawns, all sensor bridges (camera, ydlidar, odom, tf) connect.

If a launch file name is ever wrong, list what's actually available:
```bash
ls src/tortoisebot/tortoisebot_gazebo/launch/
```

### 6. Drive the robot (teleop)

Gazebo occupies the terminal it's running in, so driving the robot needs a second shell injected into the *same* running container:

```bash
# In a new terminal on the Pi 5 desktop:
sudo docker ps                              # find the tortoise-sim container ID
sudo docker exec -it <CONTAINER_ID> bash    # open a second shell in it

# Inside that new shell:
source /opt/ros/jazzy/setup.bash
source ~/tortoise_ws/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Drive with `u i o / j k l / m , .` (standard `teleop_twist_keyboard` keymap).

**Status: workspace built, Gazebo launches, robot spawns and drives. Next up: SLAM.**

## GUI troubleshooting

You're accessing the Pi 5 desktop remotely via **Raspberry Pi Connect** (browser-based screen sharing), not a local monitor.

If Gazebo/RViz windows fail to open from inside the container:

- **`cannot connect to X server` / `qt.qpa.xcb: could not connect to display`** — re-run `xhost +local:root` **on the Pi 5 host itself** (open a fresh terminal from the Pi's desktop, not `docker exec` into the running container). This grant does **not** persist across a Raspberry Pi Connect session reset — if the browser tab reconnects, re-run it before launching Gazebo again. Confirm the command actually took by checking for the output `non-network local connections being added to access control list`.
- **`$DISPLAY` mismatch** — run `echo $DISPLAY` on the host *and* inside the container; they need to match (usually `:0`). If they don't, the container needs restarting with a fresh `-e DISPLAY=$DISPLAY` pulled from the host at that moment.
- **Watch for stray characters when typing `xhost +local:root` or any `grep`/quoted command** — a trailing backtick or unclosed quote leaves bash hanging at a `>` continuation prompt instead of erroring, which looks like nothing happened. Ctrl+C and retype carefully.

### GPU rendering (expected, not a bug)

Gazebo on the Pi 5 logs `MESA-LOADER: failed to retrieve device information` / `glx: failed to create dri3 screen` / `failed to load driver: vc4` — the Pi 5's GPU driver doesn't support hardware-accelerated 3D rendering for Gazebo. It falls back to **software rendering** automatically, which works but runs slow (visible as reduced playback % in the sim window). This is just a Pi 5 hardware limitation, not something to fix.

## Debugging log (chronological)

1. **ARM64/AMD64 mismatch** — see Dockerfile note above (`osrf/ros:jazzy-desktop` → `ros:jazzy` + manual desktop install)
2. **`ign` command not found** — `tortoisebot_gazebo`'s `ignition_sim.launch.py` called the old Ignition-era `ign gazebo` command, which doesn't exist under Jazzy's Gazebo Harmonic. Fixed by editing lines 112 & 118 in that launch file: `cmd=['ign', 'gazebo', ...]` → `cmd=['gz', 'sim', ...]`
3. **Fix didn't take effect** — classic colcon gotcha: `colcon build` copies `src/` into `install/` by default, and `ros2 launch` runs the `install/` copy. Edits to source do nothing until rebuilt. Fixed by rebuilding with `colcon build --packages-select tortoisebot_gazebo --symlink-install`, which symlinks `install/` back to `src/` so future edits apply immediately
4. **Missing dependencies during build** (`camera_info_manager`, `ydlidar_ros2_driver`) — installed directly via `apt`, or skipped with `--packages-skip` since they're physical-hardware-only and not needed for simulation
5. **✅ First successful launch** — Gazebo rendered `nav2_test_world.sdf`, robot spawned (`Entity creation successful`), all sensor bridges connected (camera, ydlidar, odom, tf)
6. **Intermittent X11 crash on a later run** — `qt.qpa.xcb: could not connect to display :0` crashed the Gazebo GUI (Qt fatal abort) despite working minutes earlier. Root cause: `xhost +local:root` grant reset after a Raspberry Pi Connect session change. Fix: re-run `xhost +local:root` on the host before each new launch if the desktop session has reconnected

> **Housekeeping:** failed Gazebo GUI crashes leave large `core.*` dump files in `~/tortoise_ws/` (~150MB each). Clean up periodically: `rm -f ~/tortoise_ws/core.*`

## Status / TODO

- [x] Fixed ARM64/AMD64 Docker image mismatch (switched to `ros:jazzy` base)
- [x] Fixed `ign` → `gz sim` command in `ignition_sim.launch.py`
- [x] Fixed stale `install/` copy by rebuilding with `--symlink-install`
- [x] Workspace built, Gazebo simulation launches, robot spawns and drives via teleop
- [ ] Run SLAM Toolbox against the simulated robot (next step)
- [ ] Add persistent volume mount to the sim Docker run command (currently `--rm`, work is lost on exit)
- [ ] Re-run `xhost +local:root` on host whenever the Raspberry Pi Connect session resets (recurring gotcha, not a one-time fix)
- [ ] Periodically clean `~/tortoise_ws/core.*` crash dumps
- [ ] Tune SLAM Toolbox params against manual joystick/teleop-driven mapping
- [ ] Tune Nav2 costmap inflation
- [ ] Validate `.xacro` (from `tortoisewithself` repo) in simulation before running on real hardware in the lab
- [ ] Test ROS_DOMAIN_ID / multi-machine discovery between the two Pis on the lab network

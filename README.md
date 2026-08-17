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

> Not yet confirmed: whether the lab Wi-Fi allows this kind of inter-device discovery. Worth testing early rather than after everything else is wired up.

## Pre-lab simulation (Pi 5, Docker)

Since the Tortoise itself lives in the lab, mapping/nav software gets tested first in simulation on the Pi 5.

### 1. Dockerfile

> **ARM64 note:** `osrf/ros:jazzy-desktop` is AMD64-only and fails on the Pi 5 with `expected "linux/arm64" for current build` / `exec format error`. Use the plain `ros:jazzy` base (ARM-compatible) and install the desktop tools manually instead.

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

**Build**, skipping physical-hardware-only packages not needed for simulation (LiDAR/camera drivers):

```bash
colcon build --packages-skip ydlidar_ros2_driver v4l2_camera
```

> If missing-dependency errors come up for other packages, install them directly (`apt install -y ros-jazzy-camera-info-manager`, `ros-jazzy-image-transport`, etc.) and just re-run `colcon build` — it resumes from where it failed. Or use `rosdep` to install everything a workspace needs at once:
> ```bash
> apt update && rosdep init && rosdep update
> rosdep install --from-paths src --ignore-src -r -y
> ```

### 5. Launch the simulation

```bash
source install/setup.bash
ros2 launch tortoisebot_gazebo tortoisebot_empty_world.launch.py
```

If the launch file name is wrong, list what's actually available:
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

If Gazebo/RViz windows fail to open from inside the container, it's almost always the X11 forwarding:

- **`cannot connect to X server` / blank window** — re-run `xhost +local:root` on the Pi 5 host (not inside the container) before `docker run`
- **Connecting to the Pi 5 over SSH** — plain SSH won't forward a Wayland/X session by itself; you need either a monitor physically on the Pi 5, or SSH with `-X`/`-Y` (X11 forwarding) into the Pi 5 first, or a VNC session into the Pi 5 desktop
- **`$DISPLAY` is empty inside the container** — check `echo $DISPLAY` on the Pi 5 host first; if that's empty, the host itself has no display session to forward
- **Still nothing** — confirm the Pi 5 is running the **64-bit Raspberry Pi OS desktop image** (Gazebo/RViz need a real desktop environment, not Lite)

>  Not yet confirmed: whether you're driving the Pi 5 with a monitor attached or remotely — worth deciding this before the Docker run, since it changes the `-e DISPLAY` setup.

## Status / TODO

- [x] Fixed ARM64/AMD64 Docker image mismatch (switched to `ros:jazzy` base)
- [x] Workspace built, Gazebo simulation launches, robot spawns and drives via teleop
- [ ] Run SLAM Toolbox against the simulated robot (next step)
- [ ] Add persistent volume mount to the sim Docker run command (currently `--rm`, work is lost on exit)
- [ ] Tune SLAM Toolbox params against manual joystick/teleop-driven mapping
- [ ] Tune Nav2 costmap inflation
- [ ] Validate `.xacro` in simulation before running on real hardware in the lab
- [ ] Confirm how you're accessing the Pi 5 desktop (local monitor, SSH -X, or VNC) so GUI forwarding works
- [ ] Test ROS_DOMAIN_ID / multi-machine discovery between the two Pis on the lab network

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

## Pre-lab simulation (Pi 5, Docker)

Since the Tortoise itself lives in the lab, mapping/nav software gets tested first in simulation on the Pi 5.

### 1. Dockerfile

```bash
cat << 'EOF' > Dockerfile
FROM osrf/ros:jazzy-desktop

RUN apt-get update && apt-get install -y \
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
docker build -t tortoise-sim .
```

### 3. Run (with GUI access for Gazebo/RViz)

```bash
xhost +local:root

docker run -it --rm \
  --net=host \
  -e DISPLAY=$DISPLAY \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  tortoise-sim
```

> **Note:** this uses `--rm` with no volume mount for the workspace — anything created inside the container is lost when it exits. Add a workspace volume mount before doing real work, e.g. `-v ~/tortoise_ws:/root/tortoise_ws`.

### 4. Workspace + repo (inside the container)

```bash
mkdir -p ~/tortoise_ws/src
cd ~/tortoise_ws/src

git clone https://github.com/rigbetellabs/tortoisebot.git

cd ~/tortoise_ws
colcon build
source install/setup.bash
```

Then launch the simulation (exact launch file depends on the repo — typically something like `ros2 launch tortoisebot_description display.launch.py` or `gazebo.launch.py`).

## Status / TODO

- [ ] Confirm exact launch file name in the `tortoisebot` repo
- [ ] Add persistent volume mount to the sim Docker run command
- [ ] Tune SLAM Toolbox params against manual joystick-driven mapping
- [ ] Tune Nav2 costmap inflation
- [ ] Validate `.xacro` in simulation before running on real hardware in the lab

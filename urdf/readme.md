# TortoiseBot Simulation & SLAM Mapping — ROS 2 Jazzy Setup Guide

Personal runbook for simulating the [TortoiseBot](https://github.com/rigbetellabs/tortoisebot) in Gazebo Harmonic on ROS 2 Jazzy, and generating a 2D map of a room using Cartographer SLAM.

> **Environment:** ROS 2 Jazzy + Gazebo Harmonic (the `ros_gz` bridge, *not* the old Gazebo Classic / `gazebo_ros`).

---

## Part 1 — One-Time Workspace Setup

### 1.1 Install core dependencies
```bash
sudo apt update
sudo apt install ros-jazzy-ros-gz ros-jazzy-xacro ros-jazzy-robot-state-publisher -y
```

### 1.2 Create the workspace
```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws/src
```

### 1.3 Clone the TortoiseBot repo
```bash
git clone -b ros2-jazzy https://github.com/rigbetellabs/tortoisebot.git
```
> If the `ros2-jazzy` branch doesn't exist, fall back to `ros2-humble` — it has largely been migrated to modern Gazebo already:
> ```bash
> git clone -b ros2-humble https://github.com/rigbetellabs/tortoisebot.git
> ```

### 1.4 Install rosdep (first-time machine setup only)
```bash
sudo apt update
sudo apt install python3-rosdep -y
sudo rosdep init
```
*(Ignore the DeprecationWarning — it's harmless.)*

### 1.5 Install package dependencies
```bash
cd ~/ros2_ws
rosdep update
rosdep install --from-paths src --ignore-src -r -y
```

### 1.6 Build the workspace
**Source the base ROS 2 install first** — this is required or `colcon build` fails with `ament_cmake` config errors:
```bash
source /opt/ros/jazzy/setup.bash
cd ~/ros2_ws
colcon build
```

If `ydlidar_ros2_driver` fails because `ydlidar_sdk` wasn't ready yet (a build-order race condition), build the SDK first, re-source, then build everything:
```bash
colcon build --packages-select ydlidar_sdk
source install/setup.bash
colcon build
```

### 1.7 Source the built workspace
```bash
source install/setup.bash
```
> Add `source ~/ros2_ws/install/setup.bash` to `~/.bashrc` to avoid repeating this every terminal session.

---

## Part 2 — Launching the Gazebo Simulation

### 2.1 Set environment variables
Needed to avoid Gazebo finding no meshes / crashing on Wayland:
```bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:~/ros2_ws/src/tortoisebot
export QT_QPA_PLATFORM=xcb
```

### 2.2 Install `robot_localization` (required by the launch file)
```bash
sudo apt install ros-jazzy-robot-localization -y
```

### 2.3 Launch
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch tortoisebot_gazebo ignition_sim.launch.py
```
> If the launch file name doesn't match, tab-complete to find the right one:
> ```bash
> ros2 launch tortoisebot_gazebo <TAB><TAB>
> ```

The Gazebo Harmonic GUI should open with the TortoiseBot spawned in the world.

---

## Part 3 — SLAM: Mapping the Room

Keep the Gazebo terminal running throughout this part.

### 3.1 Install Cartographer (if not already present)
```bash
sudo apt update
sudo apt install ros-jazzy-cartographer ros-jazzy-cartographer-ros -y
```

### 3.2 Launch the SLAM node (new terminal)
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 launch tortoisebot_slam cartographer.launch.py use_sim_time:=True
```
> If the launch file name isn't found, tab-complete: `ros2 launch tortoisebot_slam <TAB><TAB>`

Success looks like: `Added trajectory with ID '0'` in the terminal, with no crash.

### 3.3 Open RViz to watch the map build (new terminal)
```bash
source ~/ros2_ws/install/setup.bash
rviz2
```
In RViz:
1. Bottom-left → **Add** → **By topic** tab
2. Find `/map` → select **Map** → OK
3. Add `/scan` → select **LaserScan** → OK (shows LiDAR hits on walls)
4. Under **Global Options**, set **Fixed Frame** to `map`

### 3.4 Drive the robot to scan the room (new terminal)
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```
Keys (terminal must be in focus):
| Key | Action |
|---|---|
| `i` | Move forward |
| `,` | Move backward |
| `j` / `l` | Turn left / right |
| `k` | Stop |

Drive around until walls and obstacles are fully outlined in the RViz map.

### 3.5 Save the map
Once the map looks complete, **before closing anything**, open one more terminal:
```bash
cd ~/ros2_ws
source install/setup.bash
ros2 run nav2_map_server map_saver_cli -f my_room_map
```
> If missing: `sudo apt install ros-jazzy-nav2-map-server -y`, then rerun.

This produces two files in `~/ros2_ws`:
- `my_room_map.pgm` — the actual map image
- `my_room_map.yaml` — metadata (resolution, origin, scale)

Once saved, it's safe to `Ctrl+C` the teleop, SLAM, and Gazebo terminals.

---

## Troubleshooting Log (issues actually hit, and fixes)

| Symptom | Cause | Fix |
|---|---|---|
| `colcon build` fails: `Cannot locate rosdep definition for [ament_cmake]` | Base ROS 2 environment not sourced in that terminal | `source /opt/ros/jazzy/setup.bash` before building |
| `ydlidar_ros2_driver` build fails: `Could not find ... ydlidar_sdk` | `colcon` tried building both packages in parallel; SDK wasn't ready | `colcon build --packages-select ydlidar_sdk` first, then `source install/setup.bash` and rebuild |
| Gazebo opens then closes after a few seconds, no clear reason | Missing resource paths / Wayland-Qt conflict | `export GZ_SIM_RESOURCE_PATH=...` and `export QT_QPA_PLATFORM=xcb` |
| Gazebo crash, log shows `package 'robot_localization' not found` | Missing dependency for the launch file's EKF node | `sudo apt install ros-jazzy-robot-localization -y` |
| `cartographer_node` not found | Cartographer not installed | `sudo apt install ros-jazzy-cartographer ros-jazzy-cartographer-ros -y` |
| `cartographer_node` crashes: `symbol lookup error ... undefined symbol: ...fastcdr...` | Version mismatch between newly installed Cartographer and existing FastCDR/FastRTPS middleware libs | `sudo apt update && sudo apt upgrade -y` to sync all ROS 2 library versions |
| `apt upgrade` aborts early, updates never apply | One package (e.g. `microsoft-edge-stable`) failed to download and killed the whole upgrade | `sudo apt update && sudo apt upgrade --fix-missing -y` |
| `rosdep install` fails, rosdep not found | `rosdep` never installed/initialized on this machine | `sudo apt install python3-rosdep -y && sudo rosdep init`, then retry `rosdep update` + `rosdep install ...` |

---

## Quick Reference — Full Sequence (once everything is installed)

Terminal 1 — Gazebo:
```bash
source ~/ros2_ws/install/setup.bash
export GZ_SIM_RESOURCE_PATH=$GZ_SIM_RESOURCE_PATH:~/ros2_ws/src/tortoisebot
export QT_QPA_PLATFORM=xcb
ros2 launch tortoisebot_gazebo ignition_sim.launch.py
```

Terminal 2 — SLAM:
```bash
source ~/ros2_ws/install/setup.bash
ros2 launch tortoisebot_slam cartographer.launch.py use_sim_time:=True
```

Terminal 3 — RViz:
```bash
source ~/ros2_ws/install/setup.bash
rviz2
```

Terminal 4 — Drive:
```bash
source ~/ros2_ws/install/setup.bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Terminal 5 — Save map (after driving around the room):
```bash
source ~/ros2_ws/install/setup.bash
cd ~/ros2_ws
ros2 run nav2_map_server map_saver_cli -f my_room_map
```

---

## Not Yet Covered
- Autonomous navigation with Nav2 (using the saved map)
- Fixing missing textures/meshes in Gazebo Harmonic
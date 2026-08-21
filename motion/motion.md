# TortoiseBot — Physical Robot Mapping & Teleoperation Setup

This setup uses **three terminals**:

1. **Terminal 1 — Engine:** Starts the physical robot hardware and sensors.
2. **Terminal 2 — Bridge:** Publishes the required LiDAR TF transform for mapping.
3. **Terminal 3 — Steering Wheel:** Runs keyboard teleoperation.

---

## Terminal 1 — Engine (Hardware & Sensors)

This terminal starts the physical robot, including the motor hardware and sensors.

### 1. SSH into the Raspberry Pi

```bash
ssh turtlrbotpi4@<ROBOT_IP_ADDRESS>
```

Replace `<ROBOT_IP_ADDRESS>` with the actual IP address of the robot's Raspberry Pi.

### 2. Unlock Motor Hardware Access

```bash
sudo chmod 777 /dev/mem /dev/gpiomem
```

Run this in case the device permissions were reset after restarting or reconnecting to the Pi.

### 3. Source ROS 2 Jazzy

```bash
source /opt/ros/jazzy/setup.bash
```

### 4. Source the TortoiseBot Workspace

```bash
source ~/ros2_ws/install/setup.bash
```

### 5. Launch the Physical Robot

```bash
ros2 launch tortoisebot_bringup autobringup.launch.py use_sim_time:=False
```

`use_sim_time:=False` ensures that ROS 2 uses the physical robot's real clock rather than simulation time.

> **Important:** Keep this terminal running. Wait a few seconds for the launch output to stabilize (and for the LiDAR-related warnings/messages to appear) before starting Terminal 2.

---

## Terminal 2 — Bridge (LiDAR TF Fix)

This terminal publishes a static TF transform so that Cartographer can correctly locate the LiDAR frame.

### 1. Open a New Terminal and SSH into the Pi

```bash
ssh turtlrbotpi4@<ROBOT_IP_ADDRESS>
```

### 2. Source ROS 2 Jazzy

```bash
source /opt/ros/jazzy/setup.bash
```

### 3. Publish the Static Transform

```bash
ros2 run tf2_ros static_transform_publisher \
  --x 0 \
  --y 0 \
  --z 0 \
  --roll 0 \
  --pitch 0 \
  --yaw 0 \
  --frame-id laser_frame \
  --child-frame-id lidar
```

This creates the transform:

```text
laser_frame
    │
    └── lidar
```

with zero translation and zero rotation between the two frames.

> **Important:** Keep this terminal running while using the robot.

---

## Terminal 3 — Steering Wheel (Keyboard Control)

This terminal is used to manually drive the robot using the keyboard.

### 1. Open Another Terminal and SSH into the Pi

```bash
ssh turtlrbotpi4@<ROBOT_IP_ADDRESS>
```

### 2. Source ROS 2 Jazzy

```bash
source /opt/ros/jazzy/setup.bash
```

### 3. Start Keyboard Teleoperation

```bash
ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

Keep this terminal active while driving the robot (keyboard input is captured here).

---

## Final Terminal Layout

```text
┌─────────────────────────────────────────────┐
│ Terminal 1 — ENGINE                         │
│                                             │
│ tortoisebot_bringup                         │
│ Motors + Sensors + LiDAR                    │
│                                             │
│ KEEP RUNNING                                │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Terminal 2 — BRIDGE                         │
│                                             │
│ laser_frame ──────► lidar                   │
│ Static TF Publisher                         │
│                                             │
│ KEEP RUNNING                                │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│ Terminal 3 — STEERING WHEEL                 │
│                                             │
│ teleop_twist_keyboard                       │
│                                             │
│ KEEP ACTIVE + USE KEYBOARD                  │
└─────────────────────────────────────────────┘
```

## Quick Command Reference

### Terminal 1

```bash
ssh turtlrbotpi4@<ROBOT_IP_ADDRESS>

sudo chmod 777 /dev/mem /dev/gpiomem

source /opt/ros/jazzy/setup.bash
source ~/ros2_ws/install/setup.bash

ros2 launch tortoisebot_bringup autobringup.launch.py use_sim_time:=False
```

### Terminal 2

```bash
ssh turtlrbotpi4@<ROBOT_IP_ADDRESS>

source /opt/ros/jazzy/setup.bash

ros2 run tf2_ros static_transform_publisher \
  --x 0 --y 0 --z 0 \
  --roll 0 --pitch 0 --yaw 0 \
  --frame-id laser_frame \
  --child-frame-id lidar
```

### Terminal 3

```bash
ssh turtlrbotpi4@<ROBOT_IP_ADDRESS>

source /opt/ros/jazzy/setup.bash

ros2 run teleop_twist_keyboard teleop_twist_keyboard
```

---

## Startup Order

```text
Terminal 1
    ↓
Start robot hardware and sensors
    ↓
Wait for startup to stabilize
    ↓
Terminal 2
    ↓
Start LiDAR TF bridge
    ↓
Terminal 3
    ↓
Start keyboard teleoperation
    ↓
Drive the robot
```

**Required order:**

```text
Engine → Bridge → Steering Wheel
```


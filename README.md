# ROS 2 Jazzy + Nav2 on Raspberry Pi OS (Docker)

## Prerequisites
- Docker installed on Pi OS (Ubuntu base recommended)

## Steps

### 1. Create the Dockerfile
```bash
cat << 'EOF' > Dockerfile
FROM ros:jazzy-ros-core
RUN apt-get update && apt-get install -y \
    ros-jazzy-navigation2 \
    ros-jazzy-nav2-bringup \
    && rm -rf /var/lib/apt/lists/*
EOF
```

### 2. Build the image
```bash
docker build -t my-ros-jazzy-nav2 .
```

### 3. Run the container
```bash
docker run -it --rm my-ros-jazzy-nav2
```

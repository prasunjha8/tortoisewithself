#!/usr/bin/env python3
"""
voice_teleop_node.py
ROS2 node that drives tortoisebot by voice: record -> Whisper STT -> GPT
intent match against a fixed set of movement words -> publish the
corresponding geometry_msgs/Twist on /cmd_vel -- the same topic
teleop_twist_keyboard publishes to, so it drops straight into your existing
bringup (Terminal 1: autobringup.launch.py, Terminal 2: static transform
publisher, this node replaces Terminal 3).

Loop: press Enter, speak one of forward / backward / left / right / stop,
robot executes it for MOVE_DURATION seconds then auto-stops. Ctrl+C to quit.

Requires: OPENAI_API_KEY set in the environment, a working microphone visible
to this process, and openai/sounddevice/scipy installed. Run with the ROS2
environment sourced.
"""
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

from .config import LINEAR_SPEED, ANGULAR_SPEED, MOVE_DURATION
from .voice.recorder import record_audio
from .voice.speech_to_text import transcribe
from .voice.intent_parser import extract_target

KNOWN_TARGETS = ["forward", "backward", "left", "right", "stop"]

# (linear.x, angular.z) per command; duration comes from config.MOVE_DURATION
COMMAND_TWIST = {
    "forward":  (LINEAR_SPEED, 0.0),
    "backward": (-LINEAR_SPEED, 0.0),
    "left":     (0.0, ANGULAR_SPEED),
    "right":    (0.0, -ANGULAR_SPEED),
    "stop":     (0.0, 0.0),
}


class VoiceTeleop(Node):
    def __init__(self):
        super().__init__("voice_teleop")
        self.pub = self.create_publisher(Twist, "cmd_vel", 10)

    def send_twist(self, linear_x, angular_z, duration):
        msg = Twist()
        msg.linear.x = linear_x
        msg.angular.z = angular_z
        end_time = time.time() + duration
        # Republish for the whole duration -- differential.py acts on the
        # latest message only, there's no built-in "hold for N seconds".
        while time.time() < end_time:
            self.pub.publish(msg)
            time.sleep(0.1)
        self.stop()

    def stop(self):
        self.pub.publish(Twist())  # all-zero Twist


def main():
    rclpy.init()
    node = VoiceTeleop()
    print("Voice teleop ready. Commands: forward / backward / left / right / stop")
    print("Press Enter, then speak. Ctrl+C to quit.\n")
    try:
        while rclpy.ok():
            input("Press Enter to record...")
            audio, fs = record_audio()
            transcript = transcribe(audio, fs)
            print(f'Heard: "{transcript}"')
            target = extract_target(transcript, KNOWN_TARGETS)
            if target is None:
                print("No matching command recognized, try again.\n")
                continue
            print(f"Executing: {target}\n")
            if target == "stop":
                node.stop()
            else:
                linear_x, angular_z = COMMAND_TWIST[target]
                node.send_twist(linear_x, angular_z, MOVE_DURATION)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()

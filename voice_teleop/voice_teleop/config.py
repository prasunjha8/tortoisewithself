"""
config.py
Central config for the voice pipeline + voice_teleop_node.py.
"""
import os

# --- OpenAI ---
# Set this via `export OPENAI_API_KEY=sk-...` before running, rather than
# hardcoding it here.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
STT_MODEL = "whisper-1"
INTENT_MODEL = "gpt-4o-mini"

# --- Audio recording ---
RECORD_SECONDS = 3
SAMPLE_RATE = 16000

# --- Robot motion (tortoisebot tuning) ---
LINEAR_SPEED = 0.15     # m/sec for forward/backward
ANGULAR_SPEED = 0.6     # rad/sec for left/right turn-in-place
MOVE_DURATION = 1.5     # seconds each command runs before auto-stopping

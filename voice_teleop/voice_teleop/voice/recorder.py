"""
voice/recorder.py
Microphone recording via sounddevice. Records a fixed-duration mono clip
and hands it back as a (numpy array, sample_rate) pair for
speech_to_text.transcribe().
"""
import sounddevice as sd

from ..config import RECORD_SECONDS, SAMPLE_RATE


def record_audio(duration=RECORD_SECONDS, fs=SAMPLE_RATE):
    """Blocks for `duration` seconds while recording from the default input
    device."""
    print(f"Recording for {duration}s... speak now.")
    audio = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype="float32")
    sd.wait()
    return audio, fs

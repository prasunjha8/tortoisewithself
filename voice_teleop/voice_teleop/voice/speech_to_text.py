"""
voice/speech_to_text.py
Whisper transcription via the OpenAI API. Writes the recorded audio to a
temp WAV file (what the API expects) and always cleans it up afterward,
even if the API call raises.
"""
import os
import tempfile

from scipy.io.wavfile import write as wav_write
from openai import OpenAI

from ..config import OPENAI_API_KEY, STT_MODEL

_client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe(audio, fs):
    """audio, fs: as returned by recorder.record_audio(). Returns the
    transcript text, stripped of leading/trailing whitespace."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        wav_write(tmp.name, fs, audio)
        path = tmp.name
    try:
        with open(path, "rb") as f:
            # extra_headers disables response compression -- avoids a bug in
            # the openai package's bundled httpx2 client where decompressing
            # a Brotli-encoded response raises
            # "TypeError: process() takes no keyword arguments".
            result = _client.audio.transcriptions.create(
                model=STT_MODEL,
                file=f,
                extra_headers={"Accept-Encoding": "identity"},
            )
        return result.text.strip()
    finally:
        os.unlink(path)

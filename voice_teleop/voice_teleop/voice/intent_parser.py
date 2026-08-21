"""
voice/intent_parser.py
Turns a raw transcript into one of the known target values, using a
temperature-0 chat completion constrained to strict JSON output so it's
either a verbatim match or explicitly null -- never a paraphrase we'd then
have to fuzzy-match ourselves.
"""
import json

from openai import OpenAI

from ..config import OPENAI_API_KEY, INTENT_MODEL
from .prompts import intent_system_prompt

_client = OpenAI(api_key=OPENAI_API_KEY)


def extract_target(transcript, known_targets):
    """known_targets: list of valid values to match against. Returns the
    matched value verbatim, or None if the model didn't confidently match
    one."""
    system_prompt = intent_system_prompt(known_targets)
    resp = _client.chat.completions.create(
        model=INTENT_MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        # extra_headers disables response compression -- avoids a bug in the
        # openai package's bundled httpx2 client where decompressing a
        # Brotli-encoded response raises
        # "TypeError: process() takes no keyword arguments".
        extra_headers={"Accept-Encoding": "identity"},
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": transcript},
        ],
    )
    try:
        return json.loads(resp.choices[0].message.content).get("target")
    except json.JSONDecodeError:
        return None

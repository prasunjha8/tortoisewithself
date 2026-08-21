"""
voice/prompts.py
LLM prompt templates for the voice pipeline, kept separate from
intent_parser.py so prompt wording can be tuned/tested without touching any
API-calling code.
"""


def intent_system_prompt(known_targets):
    """System prompt for intent_parser.extract_target(): forces the model
    to choose one verbatim value from the known list, or null, and to
    answer in strict JSON so it's trivially parseable."""
    return (
        "Extract which movement command a robot voice command refers to. "
        f"Choose exactly one value, verbatim, from this list: "
        f"{known_targets}. If nothing matches, return null. "
        'Respond with STRICT JSON only: {"target": "<name or null>"}'
    )
